"""抓取公开网站并发布为当前线程可搜索的文件资料集。"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urljoin, urlsplit, urlunsplit
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field
from yuxi.utils import logger

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PAGE_SOURCES = 30
MAX_PDF_SOURCES = 20
# 旧调用方仍可能读取该名称；新的选择逻辑不再让 PDF 消耗网页来源额度。
MAX_SOURCES = MAX_PAGE_SOURCES
# 网页和 PDF 使用独立的资料集容量；MAX_DATASET_BYTES 保留为网页容量的兼容名称。
MAX_DATASET_BYTES = 50 * 1024 * 1024
MAX_PAGE_DATASET_BYTES = MAX_DATASET_BYTES
MAX_PDF_DATASET_BYTES = 50 * 1024 * 1024
MAX_TOTAL_DATASET_BYTES = MAX_PAGE_DATASET_BYTES + MAX_PDF_DATASET_BYTES
CRAWL_OPTIONS = {
    "max_depth": 2,
    "max_breadth": 20,
    "limit": MAX_PAGE_SOURCES + MAX_PDF_SOURCES,
    "extract_depth": "advanced",
    "format": "markdown",
    "allow_external": False,
}
DEFAULT_LANGUAGE = "ja"
SUPPORTED_LANGUAGES = {"ja", "zh", "en"}
ProgressCallback = Callable[[int, str], Awaitable[None]]

_PROGRESS_MESSAGES = {
    "ja": {
        "checking": "公開サイトへの接続を確認中...",
        "crawling": "TavilyでサイトのページとPDFを収集中...",
        "collecting": "収集したページとPDFを整理中...",
        "prioritizing": "ページの優先度を判定し、重要な資料を選別中...",
        "sources": "検索用のソースファイルを作成中...",
        "synthesis": "サイト概要とQ&Aを日本語で生成中...",
        "publishing": "資料を現在のスレッドへ公開中...",
        "done": "サイト資料を現在のスレッドへ公開しました",
        "unchanged": "サイト内容に変更がないため、PDF解析とQ&A生成をスキップしました",
        "failed": "サイト資料の取得に失敗しました",
    },
    "zh": {
        "checking": "正在确认网站可访问性...",
        "crawling": "正在使用 Tavily 收集网页和 PDF...",
        "collecting": "正在整理已收集的网页和 PDF...",
        "prioritizing": "正在判断页面优先级并筛选重要资料...",
        "sources": "正在生成可检索的来源文件...",
        "synthesis": "正在用中文生成网站概览和问答...",
        "publishing": "正在将资料发布到当前线程...",
        "done": "网站资料已发布到当前线程",
        "unchanged": "网站内容未变化，已跳过 PDF 解析和问答生成",
        "failed": "网站资料抓取失败",
    },
    "en": {
        "checking": "Checking that the public site is reachable...",
        "crawling": "Collecting site pages and PDFs with Tavily...",
        "collecting": "Organizing the collected pages and PDFs...",
        "prioritizing": "Ranking pages by priority and selecting important materials...",
        "sources": "Creating searchable source files...",
        "synthesis": "Generating the site overview and Q&A in English...",
        "publishing": "Publishing the dataset to the current thread...",
        "done": "Website materials were published to the current thread",
        "unchanged": "The site has not changed; skipped PDF parsing and Q&A generation",
        "failed": "Website material collection failed",
    },
}
_MAX_REDIRECTS = 5
_MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)")
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
# 新闻/动态类路径通常大量重复且时效性强，默认降低优先级。
_LOW_PRIORITY_PATH_RE = re.compile(
    r"(?:/news(?:/|$)|/press(?:/|$)|/media(?:/|$)|/blog(?:/|$)|/topics(?:/|$)|"
    r"/archive(?:/|$)|/article(?:/|$)|/update(?:/|$)|"
    r"/20\d{2}/\d{1,2}/|ニュース|報道|/release(?:/|$))",
    re.IGNORECASE,
)
_HIGH_PRIORITY_PATH_RE = re.compile(
    r"(?:/about(?:/|$)|/company(?:/|$)|/service(?:/|$)|/product(?:/|$)|/faq(?:/|$)|"
    r"/contact(?:/|$)|/guide(?:/|$)|/policy(?:/|$)|/recruit(?:/|$)|/career(?:/|$)|"
    r"/outline(?:/|$)|/overview(?:/|$)|会社|概要|サービス|製品|採用)",
    re.IGNORECASE,
)
PageRankFn = Callable[[dict[str, str], str, int], Awaitable[list[str]]]

@dataclass
class SourceRecord:
    """记录一个网页或 PDF 来源的处理结果。"""

    source_url: str
    content_type: Literal["html", "pdf"]
    status: Literal["ready", "skipped", "failed"]
    content_hash: str | None = None
    markdown_path: str | None = None
    original_path: str | None = None
    error: str | None = None


@dataclass
class CrawlResult:
    """返回网站资料集发布状态和面向工具展示的最小摘要。"""

    status: Literal["created", "updated", "unchanged", "failed"]
    final_host: str | None
    ready: int
    skipped: int
    failed: int
    paths: list[str]
    message: str
    pages: int = 0
    pdfs: int = 0
    qa_count: int = 0


class QaItem(BaseModel):
    """一组可由网站来源验证的问答。"""

    question: str
    answer: str
    source_urls: list[str] = Field(min_length=1)


class WebsiteSynthesis(BaseModel):
    """一次模型调用生成的网站概览和固定数量问答。"""

    overview: str
    qa: list[QaItem] = Field(min_length=15, max_length=15)


class PagePriorityRanking(BaseModel):
    """按业务价值从高到低排列的页面 URL 列表。"""

    high_priority_urls: list[str] = Field(min_length=1)


def normalize_language(language: str | None) -> str:
    """将语言提示归一化为日语、中文或英语代码，未知值默认使用日语。"""

    value = str(language or "").strip().lower()
    aliases = {
        "japanese": "ja",
        "日语": "ja",
        "日本語": "ja",
        "chinese": "zh",
        "中文": "zh",
        "english": "en",
        "英语": "en",
    }
    normalized = aliases.get(value, value)
    return normalized if normalized in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


async def _report_progress(
    callback: ProgressCallback | None,
    language: str,
    percent: int,
    key: str,
    *,
    elapsed_seconds: int | None = None,
    detail: str | None = None,
) -> None:
    if callback is None:
        return
    message = _PROGRESS_MESSAGES[language][key]
    if elapsed_seconds is not None:
        suffix = (
            f"（経過時間：約 {elapsed_seconds} 秒）"
            if language == "ja"
            else f" (elapsed: about {elapsed_seconds}s)"
        )
        if language == "zh":
            suffix = f"（已用时约 {elapsed_seconds} 秒）"
        message += suffix
    if detail:
        message += f": {detail}"
    try:
        await callback(percent, message)
    except Exception as exc:  # 进度展示失败不能影响资料抓取
        logger.debug(f"网站抓取进度通知失败: {exc}")


async def _await_with_progress_heartbeat(
    awaitable: Awaitable[Any],
    callback: ProgressCallback | None,
    language: str,
    *,
    percent: int,
    key: str,
    interval_seconds: int = 10,
) -> Any:
    """等待长时间的抓取调用，并定期刷新仍在工作的进度文案。"""

    if callback is None:
        return await awaitable

    task = asyncio.ensure_future(awaitable)
    elapsed_seconds = 0
    while not task.done():
        done, _ = await asyncio.wait({task}, timeout=interval_seconds)
        if done:
            break
        elapsed_seconds += interval_seconds
        await _report_progress(
            callback,
            language,
            percent,
            key,
            elapsed_seconds=elapsed_seconds,
        )
    return await task


async def crawl_website(
    url: str,
    *,
    thread_id: str,
    uid: str,
    language: str = DEFAULT_LANGUAGE,
    progress_callback: ProgressCallback | None = None,
    tavily_client: Any | None = None,
    http_client: httpx.AsyncClient | None = None,
    parse_document_fn: Callable[[str], Awaitable[str]] | None = None,
    synthesis_fn: Callable[[list[tuple[str, str]]], Awaitable[WebsiteSynthesis]] | None = None,
    page_rank_fn: PageRankFn | None = None,
) -> CrawlResult:
    """抓取网站内容，并以原子替换方式发布到指定线程。"""

    language = normalize_language(language)
    stage_dir: Path | None = None
    owns_http_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=120.0))

    try:
        await _report_progress(progress_callback, language, 2, "checking")
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if tavily_client is None and not api_key:
            raise ValueError("TAVILY_API_KEY が設定されていません")

        final_url = await resolve_public_final_url(url, client)
        final_host = _url_host(final_url)
        _ensure_thread_dirs(thread_id, uid)

        website_root = _sandbox_outputs_dir(thread_id) / "website"
        website_root.mkdir(parents=True, exist_ok=True)
        output_dir = website_root / _safe_host(final_host)
        stage_dir = website_root / f".{_safe_host(final_host)}.tmp-{uuid4().hex}"
        stage_dir.mkdir()

        if tavily_client is None:
            from tavily import AsyncTavilyClient

            tavily_client = AsyncTavilyClient(api_key=api_key)
        await _report_progress(progress_callback, language, 10, "crawling")
        crawl_response = await _await_with_progress_heartbeat(
            tavily_client.crawl(
                final_url,
                select_domains=[final_host],
                **CRAWL_OPTIONS,
            ),
            progress_callback,
            language,
            percent=10,
            key="crawling",
        )

        await _report_progress(progress_callback, language, 35, "collecting")
        sources, page_contents, pdf_bytes = await _collect_sources(
            final_url=final_url,
            final_host=final_host,
            crawl_response=crawl_response,
            client=client,
            progress_callback=progress_callback,
            language=language,
            page_rank_fn=page_rank_fn,
        )
        ready_for_fingerprint = [source for source in sources if source.status == "ready"]
        if not ready_for_fingerprint:
            raise ValueError("公開可能な有効なソースが取得できませんでした")

        fingerprint = _content_fingerprint(ready_for_fingerprint)
        old_manifest = _read_manifest(output_dir / "manifest.json")
        if (
            old_manifest
            and old_manifest.get("fingerprint") == fingerprint
            and _published_dataset_is_complete(output_dir, old_manifest)
        ):
            await _report_progress(progress_callback, language, 100, "unchanged")
            return _result(
                "unchanged",
                final_host,
                sources,
                _published_paths(output_dir),
                _PROGRESS_MESSAGES[language]["unchanged"],
                qa_count=_count_qa_items(output_dir / "qa.md"),
            )

        parse_document_fn = parse_document_fn or _parse_document
        await _report_progress(progress_callback, language, 55, "sources")
        searchable_sources = await _write_source_files(
            stage_dir,
            sources,
            page_contents,
            pdf_bytes,
            parse_document_fn,
        )
        if not searchable_sources:
            raise ValueError("すべてのソースが書き込みまたは解析段階で失敗しました")

        synthesis: WebsiteSynthesis | None = None
        qa_ready = False
        qa_error: str | None = None
        try:
            await _report_progress(progress_callback, language, 70, "synthesis")
            if synthesis_fn is None:
                synthesis = await _generate_synthesis(searchable_sources, language=language)
            else:
                synthesis = await synthesis_fn(searchable_sources)
            synthesis, filtered_items = _sanitize_synthesis_sources(
                synthesis,
                {item[0] for item in searchable_sources},
            )
            _write_qa(stage_dir / "qa.md", synthesis, language=language)
            qa_ready = True
            if filtered_items:
                logger.info(f"网站 QA 已过滤 {filtered_items} 个无法验证来源的问答")
        except Exception as exc:  # QA 是允许独立失败的派生步骤
            qa_error = str(exc)
            logger.warning(f"网站 QA 生成失败: {exc}")

        await _report_progress(progress_callback, language, 90, "publishing")
        _write_index(
            stage_dir / "index.md",
            root_url=url,
            final_host=final_host,
            sources=sources,
            overview=synthesis.overview if synthesis else None,
            qa_error=qa_error,
            language=language,
        )
        manifest = {
            "root_url": url,
            "final_url": final_url,
            "final_host": final_host,
            "language": language,
            "generated_at": datetime.now(UTC).isoformat(),
            "crawl_options": CRAWL_OPTIONS,
            "quotas": {
                "max_page_sources": MAX_PAGE_SOURCES,
                "max_pdf_sources": MAX_PDF_SOURCES,
                "max_pdf_bytes": MAX_PDF_DATASET_BYTES,
            },
            "fingerprint": fingerprint,
            "sources": [asdict(source) for source in sources],
            "qa": {
                "status": "ready" if qa_ready else "failed",
                "error": qa_error,
                "count": len(synthesis.qa) if synthesis and qa_ready else 0,
            },
        }
        (stage_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if _directory_size(stage_dir) > MAX_TOTAL_DATASET_BYTES:
            raise ValueError("サイト資料集が 100 MiB 制限を超えました")

        status: Literal["created", "updated"] = "updated" if output_dir.exists() else "created"
        _publish_atomically(stage_dir, output_dir)
        stage_dir = None
        await _report_progress(progress_callback, language, 100, "done")
        return _result(
            status,
            final_host,
            sources,
            _published_paths(output_dir),
            _PROGRESS_MESSAGES[language]["done"],
            qa_count=len(synthesis.qa) if synthesis and qa_ready else 0,
        )
    except Exception as exc:
        logger.warning(f"网站抓取失败: {exc}")
        await _report_progress(progress_callback, language, 100, "failed", detail=str(exc))
        return CrawlResult(
            status="failed",
            final_host=locals().get("final_host"),
            ready=0,
            skipped=0,
            failed=1,
            paths=[],
            message=str(exc),
        )
    finally:
        if stage_dir is not None:
            shutil.rmtree(stage_dir, ignore_errors=True)
        if owns_http_client:
            await client.aclose()


async def resolve_public_final_url(url: str, client: httpx.AsyncClient) -> str:
    """逐跳校验入口 URL 和公开目标地址，返回最终规范化 URL。"""

    current = normalize_url(url)
    for _ in range(_MAX_REDIRECTS + 1):
        await validate_public_url(current)
        async with client.stream("GET", current, follow_redirects=False) as response:
            if response.status_code not in {301, 302, 303, 307, 308}:
                response.raise_for_status()
                return normalize_url(str(response.url))
            location = response.headers.get("location")
        if not location:
            raise ValueError("サイトのリダイレクトに Location がありません")
        current = normalize_url(urljoin(current, location))
    raise ValueError("サイトのリダイレクト回数が上限を超えました")


async def validate_public_url(url: str) -> None:
    """校验 URL 仅使用 HTTP/HTTPS 且主机只解析到公网 IP。"""

    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("公開ホストを持つ HTTP/HTTPS URL のみ対応しています")
    if parsed.username or parsed.password:
        raise ValueError("URL にユーザー認証情報を含められません")

    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise ValueError(f"サイトホストを解決できません: {parsed.hostname}") from exc
    ips = {item[4][0].split("%", 1)[0] for item in addresses}
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError("URL の宛先が公開ネットワークアドレスではありません")


def normalize_url(url: str) -> str:
    """规范化来源 URL，移除片段并统一主机、协议和默认端口。"""

    value = str(url or "").strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("HTTP/HTTPS URL のみ対応しています")
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower().rstrip(".")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("URL のポートが無効です") from exc
    netloc = f"[{host}]" if ":" in host else host
    if port and port != (443 if scheme == "https" else 80):
        netloc = f"{netloc}:{port}"
    return urlunsplit((scheme, netloc, parsed.path or "/", parsed.query, ""))


async def _collect_sources(
    *,
    final_url: str,
    final_host: str,
    crawl_response: dict[str, Any],
    client: httpx.AsyncClient,
    progress_callback: ProgressCallback | None = None,
    language: str = DEFAULT_LANGUAGE,
    page_rank_fn: PageRankFn | None = None,
) -> tuple[list[SourceRecord], dict[str, str], dict[str, bytes]]:
    """过滤 Tavily 结果并下载同主机 PDF，网页和 PDF 使用独立额度。"""

    results = crawl_response.get("results") if isinstance(crawl_response, dict) else None
    if not isinstance(results, list):
        raise ValueError("Tavily Crawl の戻り値形式が無効です")

    pages: dict[str, str] = {}
    pdf_urls: set[str] = set()
    records: list[SourceRecord] = []
    for item in results:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        try:
            source_url = normalize_url(urljoin(final_url, str(item["url"])))
        except ValueError as exc:
            records.append(SourceRecord(str(item.get("url")), "html", "skipped", error=str(exc)))
            continue
        if _url_host(source_url) != final_host:
            records.append(SourceRecord(source_url, "html", "skipped", error="ホスト外のソース"))
            continue
        if _is_pdf_url(source_url):
            pdf_urls.add(source_url)
            continue

        markdown = item.get("raw_content") or item.get("content") or ""
        normalized_markdown = _normalize_markdown(str(markdown))
        if not normalized_markdown:
            records.append(SourceRecord(source_url, "html", "failed", error="ページ本文が空です"))
            continue
        pages.setdefault(source_url, normalized_markdown)
        for link in _extract_links(normalized_markdown, source_url):
            if _is_pdf_url(link) and _url_host(link) == final_host:
                pdf_urls.add(link)

    if len(pages) > MAX_PAGE_SOURCES:
        await _report_progress(progress_callback, language, 42, "prioritizing")
    selected_pages = await _select_priority_pages(
        pages,
        entry_url=final_url,
        limit=MAX_PAGE_SOURCES,
        rank_fn=page_rank_fn,
    )
    selected_pdfs = sorted(pdf_urls)[:MAX_PDF_SOURCES]
    for source_url in sorted(set(pages) - set(selected_pages)):
        records.append(
            SourceRecord(
                source_url,
                "html",
                "skipped",
                error="優先度が低い、またはWebページソース上限（30件）を超過",
            )
        )
    for source_url in sorted(pdf_urls)[MAX_PDF_SOURCES:]:
        records.append(SourceRecord(source_url, "pdf", "skipped", error="PDFソース上限（20件）を超過"))

    page_contents: dict[str, str] = {}
    admitted_page_bytes = 0
    for source_url in selected_pages:
        content = pages[source_url]
        content_bytes = content.encode("utf-8")
        if admitted_page_bytes + len(content_bytes) > MAX_PAGE_DATASET_BYTES:
            records.append(SourceRecord(source_url, "html", "skipped", error="Webページ資料集の 50 MiB 制限に達しました"))
            continue
        admitted_page_bytes += len(content_bytes)
        page_contents[source_url] = content
        records.append(
            SourceRecord(
                source_url,
                "html",
                "ready",
                content_hash=hashlib.sha256(content_bytes).hexdigest(),
            )
        )

    downloaded_pdfs: dict[str, bytes] = {}
    admitted_pdf_bytes = 0
    for source_url in selected_pdfs:
        try:
            data, final_pdf_url = await _download_pdf(source_url, final_host, client)
            if final_pdf_url in downloaded_pdfs:
                records.append(SourceRecord(source_url, "pdf", "skipped", error="正規化後の PDF が重複しています"))
                continue
            if admitted_pdf_bytes + len(data) > MAX_PDF_DATASET_BYTES:
                records.append(
                    SourceRecord(final_pdf_url, "pdf", "skipped", error="PDF資料集の 50 MiB 制限に達しました")
                )
                continue
            admitted_pdf_bytes += len(data)
            downloaded_pdfs[final_pdf_url] = data
            records.append(
                SourceRecord(
                    final_pdf_url,
                    "pdf",
                    "ready",
                    content_hash=hashlib.sha256(data).hexdigest(),
                )
            )
        except Exception as exc:
            records.append(SourceRecord(source_url, "pdf", "failed", error=str(exc)))
    return records, page_contents, downloaded_pdfs


async def _download_pdf(url: str, expected_host: str, client: httpx.AsyncClient) -> tuple[bytes, str]:
    """流式下载 PDF，并在每次重定向前重复校验公网和同主机边界。"""

    current = normalize_url(url)
    for _ in range(_MAX_REDIRECTS + 1):
        if _url_host(current) != expected_host:
            raise ValueError("PDF のリダイレクトがサイトホスト境界を越えました")
        await validate_public_url(current)
        async with client.stream("GET", current, follow_redirects=False) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise ValueError("PDF のリダイレクトに Location がありません")
                current = normalize_url(urljoin(current, location))
                continue
            response.raise_for_status()
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_PDF_BYTES:
                    raise ValueError("PDF が 10 MiB 制限を超えました")
            if not content:
                raise ValueError("PDF の内容が空です")
            return bytes(content), normalize_url(str(response.url))
    raise ValueError("PDF のリダイレクト回数が上限を超えました")


_PDF_PARSE_CONCURRENCY = 3
_MIN_PDF_TEXT_CHARS = 80


async def _write_source_files(
    stage_dir: Path,
    sources: list[SourceRecord],
    pages: dict[str, str],
    pdfs: dict[str, bytes],
    parse_document_fn: Callable[[str], Awaitable[str]],
) -> list[tuple[str, str]]:
    """写入来源文件并将 PDF 解析失败收敛为来源级失败。"""

    searchable: list[tuple[str, str]] = []
    pdf_jobs: list[tuple[SourceRecord, Path, Path]] = []

    for source in sources:
        if source.status != "ready":
            continue
        filename = _source_filename(source.source_url)
        if source.content_type == "html":
            relative_path = Path("pages") / f"{filename}.md"
            markdown = _source_markdown(source.source_url, "html", pages[source.source_url])
            target = stage_dir / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(markdown, encoding="utf-8")
            source.markdown_path = relative_path.as_posix()
            searchable.append((source.source_url, markdown))
            continue

        pdf_relative = Path("pdf") / f"{filename}.pdf"
        pdf_target = stage_dir / pdf_relative
        pdf_target.parent.mkdir(parents=True, exist_ok=True)
        pdf_target.write_bytes(pdfs[source.source_url])
        source.original_path = pdf_relative.as_posix()
        markdown_relative = Path("pdf") / f"{filename}.md"
        pdf_jobs.append((source, pdf_target, stage_dir / markdown_relative))

    if pdf_jobs:
        semaphore = asyncio.Semaphore(_PDF_PARSE_CONCURRENCY)

        async def parse_one(
            source: SourceRecord, pdf_target: Path, markdown_target: Path
        ) -> tuple[str, str] | None:
            async with semaphore:
                try:
                    parsed = _normalize_markdown(await parse_document_fn(str(pdf_target)))
                    if not parsed:
                        raise ValueError("PDF の解析結果が空です")
                    markdown = _source_markdown(source.source_url, "pdf", parsed)
                    markdown_target.write_text(markdown, encoding="utf-8")
                    source.markdown_path = Path("pdf").joinpath(markdown_target.name).as_posix()
                    return source.source_url, markdown
                except Exception as exc:
                    pdf_target.unlink(missing_ok=True)
                    source.status = "failed"
                    source.original_path = None
                    source.error = f"PDF の解析に失敗しました: {exc}"
                    return None

        results = await asyncio.gather(
            *(
                parse_one(source, pdf_target, markdown_target)
                for source, pdf_target, markdown_target in pdf_jobs
            )
        )
        searchable.extend(item for item in results if item is not None)

    if _directory_size(stage_dir) > MAX_TOTAL_DATASET_BYTES:
        raise ValueError("ソースファイルと解析結果が 100 MiB 制限を超えました")
    return searchable


async def _parse_document(path: str) -> str:
    """优先抽取 PDF 文本层；文本过少再回退 OCR，避免可检索 PDF 逐页 OCR 拖慢抓取。"""

    try:
        from yuxi.knowledge.parser.unified import pdfreader

        text = await asyncio.to_thread(pdfreader, path)
        normalized = _normalize_markdown(text or "")
        if len(normalized) >= _MIN_PDF_TEXT_CHARS:
            return normalized
        logger.info(f"PDF 文本层过短（{len(normalized)} 字），回退 OCR: {path}")
    except Exception as exc:
        logger.debug(f"PDF 文本抽取失败，回退 OCR: {path}: {exc}")

    from yuxi.services.ocr_service import parse_document

    return await parse_document(path)


async def _select_priority_pages(
    pages: dict[str, str],
    *,
    entry_url: str,
    limit: int = MAX_PAGE_SOURCES,
    rank_fn: PageRankFn | None = None,
) -> list[str]:
    """按业务价值选出高优先级页面；数量未超限时仍做启发式排序。"""

    if not pages:
        return []
    if len(pages) <= limit:
        return _heuristic_rank_pages(pages, entry_url)[:limit]

    try:
        if rank_fn is not None:
            ranked = await rank_fn(pages, entry_url, limit)
        else:
            ranked = await _rank_pages_with_model(pages, entry_url, limit)
    except Exception as exc:
        logger.warning(f"页面优先级模型排序失败，回退启发式: {exc}")
        ranked = _heuristic_rank_pages(pages, entry_url)

    return _normalize_ranked_urls(ranked, pages, entry_url, limit)


async def _rank_pages_with_model(pages: dict[str, str], entry_url: str, limit: int) -> list[str]:
    """用模型从候选页中选出高优先级 URL，新闻/动态类默认降权。"""

    from yuxi.agents import load_chat_model, resolve_chat_model_spec

    lines: list[str] = []
    for url in _heuristic_rank_pages(pages, entry_url):
        snippet = re.sub(r"\s+", " ", pages[url])[:180].strip()
        lines.append(f"- URL: {url}\n  snippet: {snippet}")
    catalog = "\n".join(lines[:120])
    prompt = f"""あなたはWebサイト資料整理のキュレーターです。
入口URL: {entry_url}

以下の候補ページから、知識ベースとして価値の高いページを最大 {limit} 件選び、
重要度の高い順に high_priority_urls へ並べてください。

優先度の指針:
- 高い: 会社概要、サービス/製品説明、制度・政策・手続き、採用/キャリア、FAQ、料金、ガイド
- 低い: ニュース、プレスリリース、お知らせ一覧、ブログ、日付付きアーカイブ、個別の大量記事
- 入口URLおよび入口に近いハブページは優先する
- 必ず候補に存在する URL のみを返す
- ちょうど最大 {limit} 件まで（候補が少なければその数）

候補:
{catalog}
"""
    model = load_chat_model(resolve_chat_model_spec(None)).with_structured_output(PagePriorityRanking)
    result = await model.ainvoke(prompt)
    return list(result.high_priority_urls)


def _heuristic_rank_pages(pages: dict[str, str], entry_url: str) -> list[str]:
    """无模型时按入口接近度与路径启发式排序页面。"""

    try:
        entry = normalize_url(entry_url)
    except ValueError:
        entry = entry_url

    def score(url: str) -> tuple[int, int, str]:
        path = urlsplit(url).path or "/"
        priority = 50
        if url.rstrip("/") == entry.rstrip("/"):
            priority += 40
        if _HIGH_PRIORITY_PATH_RE.search(path) or _HIGH_PRIORITY_PATH_RE.search(url):
            priority += 25
        if _LOW_PRIORITY_PATH_RE.search(path) or _LOW_PRIORITY_PATH_RE.search(url):
            priority -= 35
        depth = path.strip("/").count("/") if path.strip("/") else 0
        # 分数越高越优先；同分数时路径更浅、URL 更短的靠前。
        return (-priority, depth, url)

    return sorted(pages, key=score)


def _normalize_ranked_urls(
    ranked: list[str],
    pages: dict[str, str],
    entry_url: str,
    limit: int,
) -> list[str]:
    """校正模型输出：仅保留合法候选，不足时用启发式补齐。"""

    known = set(pages)
    selected: list[str] = []
    seen: set[str] = set()
    for raw in ranked:
        try:
            url = normalize_url(raw)
        except ValueError:
            url = str(raw or "").strip()
        if url not in known or url in seen:
            continue
        selected.append(url)
        seen.add(url)
        if len(selected) >= limit:
            return selected

    for url in _heuristic_rank_pages(pages, entry_url):
        if url in seen:
            continue
        selected.append(url)
        seen.add(url)
        if len(selected) >= limit:
            break
    return selected


async def _generate_synthesis(
    sources: list[tuple[str, str]],
    *,
    language: str = DEFAULT_LANGUAGE,
) -> WebsiteSynthesis:
    """使用系统默认模型一次生成指定语言的网站概览和 15 组带来源的问答。"""

    from yuxi.agents import load_chat_model, resolve_chat_model_spec

    source_text = "\n\n".join(f"## 来源：{url}\n{content}" for url, content in sources)
    language = normalize_language(language)
    prompts = {
        "ja": f"""以下のWebサイト資料に基づき、簡潔な日本語の概要と、ちょうど15件のFAQを作成してください。
資料に存在するFAQと、デモに適した一般的な質問をカバーしてください。各回答は資料で検証可能でなければなりません。
source_urls には、以下に明記された原URLだけを使用し、出典を捏造しないでください。検証できない内容は書かないでください。
overview、question、answer はすべて日本語で書いてください。

{source_text[:250_000]}""",
        "zh": f"""请根据以下网站资料生成简明中文概览和恰好 15 组常见问答。
问答应同时覆盖资料中已有 FAQ 和适合演示的常见问题；每个答案必须可由资料验证，
source_urls 只能使用下方明确出现的原始 URL，不得编造来源。无法验证的内容不要写入。
overview、question 和 answer 都必须使用中文。

{source_text[:250_000]}""",
        "en": f"""Based on the website materials below, create a concise English overview and exactly 15 FAQs.
Cover existing FAQs and demo-suitable common questions. Every answer must be verifiable from the materials.
Use only the original URLs listed below in source_urls; do not invent citations. Omit unverifiable content.
Write overview, question, and answer entirely in English.

{source_text[:250_000]}""",
    }
    prompt = prompts[language]
    model = load_chat_model(resolve_chat_model_spec(None)).with_structured_output(WebsiteSynthesis)
    return await model.ainvoke(prompt)


def _canonical_qa_url(value: str) -> str | None:
    """清理模型输出的引用文本，并返回可比较的规范化 URL。"""

    text = str(value or "").strip().strip("<>\"'")
    text = text.rstrip(".,，。；;：:").strip("<>\"'")
    if not text:
        return None
    try:
        return normalize_url(text)
    except ValueError:
        return None


def _sanitize_synthesis_sources(
    synthesis: WebsiteSynthesis,
    allowed_urls: set[str],
) -> tuple[WebsiteSynthesis, int]:
    """保留可由已发布来源验证的问答，过滤错误或格式化不一致的引用。"""

    allowed_by_canonical = {
        canonical: url
        for url in allowed_urls
        if (canonical := _canonical_qa_url(url)) is not None
    }
    valid_items: list[QaItem] = []
    filtered_items = 0
    for item in synthesis.qa:
        source_urls: list[str] = []
        for raw_url in item.source_urls:
            canonical = _canonical_qa_url(raw_url)
            if canonical is None or canonical not in allowed_by_canonical:
                continue
            source_url = allowed_by_canonical[canonical]
            if source_url not in source_urls:
                source_urls.append(source_url)
        if not source_urls:
            filtered_items += 1
            continue
        valid_items.append(item.model_copy(update={"source_urls": source_urls}))

    if not valid_items:
        raise ValueError("QA に検証可能な出典 URL が含まれていません")
    return synthesis.model_copy(update={"qa": valid_items}), filtered_items


def _validate_synthesis_sources(synthesis: WebsiteSynthesis, allowed_urls: set[str]) -> None:
    """严格校验问答中的每个来源 URL，供需要拒绝异常结果的调用方使用。"""

    allowed_canonical = {
        canonical
        for url in allowed_urls
        if (canonical := _canonical_qa_url(url)) is not None
    }
    for item in synthesis.qa:
        if not item.source_urls or any(
            _canonical_qa_url(url) not in allowed_canonical for url in item.source_urls
        ):
            raise ValueError("QA に欠落または無効な出典 URL が含まれています")


def _write_qa(path: Path, synthesis: WebsiteSynthesis, *, language: str = DEFAULT_LANGUAGE) -> None:
    language = normalize_language(language)
    title = {"ja": "# Webサイトのよくある質問", "zh": "# 网站常见问答", "en": "# Website FAQ"}[language]
    source_label = {"ja": "出典：", "zh": "来源：", "en": "Sources: "}[language]
    lines = [title, "", synthesis.overview.strip(), ""]
    for index, item in enumerate(synthesis.qa, start=1):
        lines.extend(
            [
                f"## {index}. {item.question.strip()}",
                "",
                item.answer.strip(),
                "",
                source_label + "、".join(f"<{url}>" for url in item.source_urls),
                "",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_index(
    path: Path,
    *,
    root_url: str,
    final_host: str,
    sources: list[SourceRecord],
    overview: str | None,
    qa_error: str | None,
    language: str = DEFAULT_LANGUAGE,
) -> None:
    language = normalize_language(language)
    labels = {
        "ja": {
            "title": "# Webサイト資料インデックス",
            "root": "入口 URL",
            "host": "最終ホスト",
            "overview": "Webサイト概要",
            "fallback": "概要の生成に失敗しました。以下のソースファイルを直接検索してください。",
            "sources": "ソース",
            "derived_failure": "派生ファイルの生成に失敗",
            "qa": "Q&A",
        },
        "zh": {
            "title": "# 网站资料索引",
            "root": "入口 URL",
            "host": "最终主机",
            "overview": "网站概览",
            "fallback": "概览生成失败；请直接检索下列来源文件。",
            "sources": "来源",
            "derived_failure": "派生文件失败",
            "qa": "QA",
        },
        "en": {
            "title": "# Website Material Index",
            "root": "Entry URL",
            "host": "Final host",
            "overview": "Website overview",
            "fallback": "Overview generation failed; search the source files below directly.",
            "sources": "Sources",
            "derived_failure": "Derived file failure",
            "qa": "Q&A",
        },
    }[language]
    lines = [
        labels["title"],
        "",
        f"- {labels['root']}：<{root_url}>",
        f"- {labels['host']}：`{final_host}`",
        "",
        f"## {labels['overview']}",
        "",
        overview.strip() if overview else labels["fallback"],
        "",
        f"## {labels['sources']}",
        "",
    ]
    for source in sources:
        local_path = source.markdown_path or source.original_path or "-"
        detail = f"（{source.error}）" if source.error else ""
        source_line = f"- [{source.status}] [{source.source_url}]({source.source_url}) → `{local_path}` {detail}"
        lines.append(source_line.rstrip())
    if qa_error:
        lines.extend(["", f"## {labels['derived_failure']}", "", f"- {labels['qa']}：{qa_error}"])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _publish_atomically(stage_dir: Path, output_dir: Path) -> None:
    """使用同文件系统改名发布，并在异常时恢复旧资料目录。"""

    backup_dir = output_dir.parent / f".{output_dir.name}.bak-{uuid4().hex}"
    had_old = output_dir.exists()
    try:
        if had_old:
            output_dir.rename(backup_dir)
        stage_dir.rename(output_dir)
    except Exception:
        if had_old and backup_dir.exists() and not output_dir.exists():
            backup_dir.rename(output_dir)
        raise
    else:
        if backup_dir.exists():
            shutil.rmtree(backup_dir)


def _content_fingerprint(sources: list[SourceRecord]) -> str:
    payload = "\n".join(
        f"{source.source_url}\0{source.content_type}\0{source.content_hash}"
        for source in sorted(sources, key=lambda item: (item.source_url, item.content_type))
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_manifest(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _published_dataset_is_complete(output_dir: Path, manifest: dict[str, Any]) -> bool:
    """仅在核心派生文件和所有已发布来源文件都存在时复用旧资料集。"""

    if not all((output_dir / name).is_file() for name in ("index.md", "manifest.json", "qa.md")):
        return False
    qa = manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("status") != "ready":
        return False
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        return False
    for source in sources:
        if not isinstance(source, dict) or source.get("status") != "ready":
            continue
        relative_path = source.get("markdown_path") or source.get("original_path")
        if not isinstance(relative_path, str) or not (output_dir / relative_path).is_file():
            return False
    return True


def _published_paths(output_dir: Path) -> list[str]:
    if not output_dir.exists():
        return []
    return [
        f"website/{output_dir.name}/{name}"
        for name in ("index.md", "qa.md", "manifest.json")
        if (output_dir / name).is_file()
    ]


def _count_qa_items(path: Path) -> int:
    """从已发布的 qa.md 统计问答条数（以二级标题为准）。"""

    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return 0
    return sum(1 for line in text.splitlines() if line.startswith("## "))


def _result(
    status: str,
    final_host: str,
    sources: list[SourceRecord],
    paths: list[str],
    message: str,
    *,
    qa_count: int = 0,
) -> CrawlResult:
    ready_sources = [source for source in sources if source.status == "ready"]
    return CrawlResult(
        status=status,  # type: ignore[arg-type]
        final_host=final_host,
        ready=len(ready_sources),
        skipped=sum(source.status == "skipped" for source in sources),
        failed=sum(source.status == "failed" for source in sources),
        paths=paths,
        message=message,
        pages=sum(source.content_type == "html" for source in ready_sources),
        pdfs=sum(source.content_type == "pdf" for source in ready_sources),
        qa_count=qa_count,
    )


def _normalize_markdown(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip()


def _source_markdown(url: str, content_type: str, content: str) -> str:
    return f"---\nsource_url: {url}\ncontent_type: {content_type}\n---\n\n{content.rstrip()}\n"


def _extract_links(markdown: str, base_url: str) -> set[str]:
    links: set[str] = set()
    for raw_link in _MARKDOWN_LINK_RE.findall(markdown):
        try:
            links.add(normalize_url(urljoin(base_url, raw_link.strip("<>"))))
        except ValueError:
            continue
    return links


def _url_host(url: str) -> str:
    hostname = urlsplit(url).hostname
    if not hostname:
        raise ValueError("URL にホストがありません")
    return hostname.lower().rstrip(".")


def _is_pdf_url(url: str) -> bool:
    return urlsplit(url).path.lower().endswith(".pdf")


def _safe_host(host: str) -> str:
    value = _SAFE_FILENAME_RE.sub("_", host).strip("._-")
    if not value:
        raise ValueError("サイトホストを安全なディレクトリ名に変換できません")
    return value


def _source_filename(url: str) -> str:
    parsed = urlsplit(url)
    stem = Path(parsed.path).stem or "index"
    safe_stem = _SAFE_FILENAME_RE.sub("_", stem).strip("._-") or "source"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{safe_stem[:80]}-{digest}"


def _directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _ensure_thread_dirs(thread_id: str, uid: str) -> None:
    """延迟加载 Agent 路径模块，避免服务加载时触发工具注册环。"""

    from yuxi.agents.backends.sandbox.paths import ensure_thread_dirs

    ensure_thread_dirs(thread_id, uid)


def _sandbox_outputs_dir(thread_id: str) -> Path:
    """延迟解析线程输出目录，保持服务模块可独立导入。"""

    from yuxi.agents.backends.sandbox.paths import sandbox_outputs_dir

    return sandbox_outputs_dir(thread_id)
