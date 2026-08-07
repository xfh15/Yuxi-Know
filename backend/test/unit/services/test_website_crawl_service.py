from __future__ import annotations

import json

import pytest

import yuxi.services.website_crawl_service as service


class FakeTavily:
    def __init__(self, results):
        self.results = results
        self.calls = []

    async def crawl(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return {"results": self.results}


class FakeHttpClient:
    async def aclose(self):
        return None


class FakeStreamResponse:
    def __init__(self, *, url, status_code=200, headers=None, chunks=()):
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}
        self.chunks = chunks

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    async def aiter_bytes(self):
        for chunk in self.chunks:
            yield chunk


class FakeStreamContext:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeDownloadClient:
    def __init__(self, responses):
        self.responses = iter(responses)

    def stream(self, *args, **kwargs):
        return FakeStreamContext(next(self.responses))


def synthesis(url: str) -> service.WebsiteSynthesis:
    return service.WebsiteSynthesis(
        overview="网站概览",
        qa=[
            service.QaItem(question=f"问题 {index}", answer="答案", source_urls=[url])
            for index in range(1, 16)
        ],
    )


@pytest.fixture
def crawl_scope(monkeypatch, tmp_path):
    output_root = tmp_path / "outputs"
    monkeypatch.setattr(
        service,
        "_ensure_thread_dirs",
        lambda thread_id, uid: output_root.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(service, "_sandbox_outputs_dir", lambda thread_id: output_root)

    async def final_url(url, client):
        return service.normalize_url(url)

    monkeypatch.setattr(service, "resolve_public_final_url", final_url)
    return output_root


@pytest.mark.asyncio
async def test_crawl_website_publishes_fixed_files_and_tavily_options(crawl_scope):
    url = "https://example.com/docs"
    tavily = FakeTavily([{"url": url, "raw_content": "# 文档\n\n正文"}])

    async def generate(items):
        assert items[0][0] == url
        return synthesis(url)

    result = await service.crawl_website(
        url,
        thread_id="thread-1",
        uid="user-1",
        tavily_client=tavily,
        http_client=FakeHttpClient(),
        synthesis_fn=generate,
    )

    assert result.status == "created"
    assert result.ready == 1
    assert result.pages == 1
    assert result.pdfs == 0
    assert result.qa_count == 15
    assert result.paths == [
        "website/example.com/index.md",
        "website/example.com/qa.md",
        "website/example.com/manifest.json",
    ]
    assert tavily.calls == [(url, {"select_domains": ["example.com"], **service.CRAWL_OPTIONS})]
    output_dir = crawl_scope / "website" / "example.com"
    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["crawl_options"] == service.CRAWL_OPTIONS
    assert manifest["quotas"] == {
        "max_page_sources": 30,
        "max_pdf_sources": 20,
        "max_pdf_bytes": 50 * 1024 * 1024,
    }
    assert manifest["qa"]["count"] == 15
    page = next((output_dir / "pages").glob("*.md")).read_text()
    assert f"source_url: {url}" in page


@pytest.mark.asyncio
async def test_crawl_website_reports_progress_and_writes_japanese_metadata(crawl_scope):
    url = "https://example.com/"
    tavily = FakeTavily([{"url": url, "raw_content": "本文"}])
    progress = []

    async def report(percent, message):
        progress.append((percent, message))

    async def generate(items):
        return synthesis(url)

    result = await service.crawl_website(
        url,
        thread_id="thread-1",
        uid="user-1",
        tavily_client=tavily,
        http_client=FakeHttpClient(),
        synthesis_fn=generate,
        progress_callback=report,
    )

    assert result.status == "created"
    assert [percent for percent, _ in progress] == [2, 10, 35, 55, 70, 90, 100]
    output_dir = crawl_scope / "website" / "example.com"
    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["language"] == "ja"
    assert (output_dir / "index.md").read_text().startswith("# Webサイト資料インデックス")
    assert (output_dir / "qa.md").read_text().startswith("# Webサイトのよくある質問")


@pytest.mark.asyncio
async def test_unchanged_fingerprint_skips_parser_and_model(crawl_scope, monkeypatch):
    page_url = "https://example.com/"
    pdf_url = "https://example.com/guide.pdf"
    tavily = FakeTavily([{"url": page_url, "raw_content": f"[PDF]({pdf_url})\n正文"}])

    async def download(url, host, client):
        return b"%PDF-stable", pdf_url

    monkeypatch.setattr(service, "_download_pdf", download)
    calls = {"parse": 0, "model": 0}

    async def parse(path):
        calls["parse"] += 1
        return "PDF 正文"

    async def generate(items):
        calls["model"] += 1
        return synthesis(page_url)

    first = await service.crawl_website(
        page_url,
        thread_id="thread-1",
        uid="user-1",
        tavily_client=tavily,
        http_client=FakeHttpClient(),
        parse_document_fn=parse,
        synthesis_fn=generate,
    )
    second = await service.crawl_website(
        page_url,
        thread_id="thread-1",
        uid="user-1",
        tavily_client=tavily,
        http_client=FakeHttpClient(),
        parse_document_fn=parse,
        synthesis_fn=generate,
    )

    assert first.status == "created"
    assert second.status == "unchanged"
    assert calls == {"parse": 1, "model": 1}


@pytest.mark.asyncio
async def test_incomplete_published_dataset_is_rebuilt(crawl_scope):
    url = "https://example.com/"
    tavily = FakeTavily([{"url": url, "raw_content": "正文"}])
    calls = 0

    async def generate(items):
        nonlocal calls
        calls += 1
        return synthesis(url)

    first = await service.crawl_website(
        url,
        thread_id="thread-1",
        uid="user-1",
        tavily_client=tavily,
        http_client=FakeHttpClient(),
        synthesis_fn=generate,
    )
    output_dir = crawl_scope / "website" / "example.com"
    (output_dir / "qa.md").unlink()

    second = await service.crawl_website(
        url,
        thread_id="thread-1",
        uid="user-1",
        tavily_client=tavily,
        http_client=FakeHttpClient(),
        synthesis_fn=generate,
    )

    assert first.status == "created"
    assert second.status == "updated"
    assert calls == 2
    assert (output_dir / "qa.md").is_file()


@pytest.mark.asyncio
async def test_pdf_parse_failure_still_publishes_valid_page(crawl_scope, monkeypatch):
    page_url = "https://example.com/"
    pdf_url = "https://example.com/fail.pdf"
    tavily = FakeTavily([{"url": page_url, "raw_content": f"正文 [PDF]({pdf_url})"}])

    async def download(url, host, client):
        return b"%PDF", pdf_url

    async def parse(path):
        raise RuntimeError("OCR unavailable")

    async def generate(items):
        return synthesis(page_url)

    monkeypatch.setattr(service, "_download_pdf", download)
    result = await service.crawl_website(
        page_url,
        thread_id="thread-1",
        uid="user-1",
        tavily_client=tavily,
        http_client=FakeHttpClient(),
        parse_document_fn=parse,
        synthesis_fn=generate,
    )

    assert result.status == "created"
    assert result.ready == 1
    assert result.failed == 1
    manifest = json.loads((crawl_scope / "website" / "example.com" / "manifest.json").read_text())
    pdf_source = next(item for item in manifest["sources"] if item["content_type"] == "pdf")
    assert pdf_source["status"] == "failed"
    assert "OCR unavailable" in pdf_source["error"]


@pytest.mark.asyncio
async def test_qa_failure_is_recorded_without_rolling_back_core_files(crawl_scope):
    url = "https://example.com/"
    tavily = FakeTavily([{"url": url, "content": "正文"}])

    async def fail_qa(items):
        raise RuntimeError("model unavailable")

    result = await service.crawl_website(
        url,
        thread_id="thread-1",
        uid="user-1",
        tavily_client=tavily,
        http_client=FakeHttpClient(),
        synthesis_fn=fail_qa,
    )

    output_dir = crawl_scope / "website" / "example.com"
    assert result.status == "created"
    assert not (output_dir / "qa.md").exists()
    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["qa"]["status"] == "failed"


@pytest.mark.asyncio
async def test_qa_filters_invalid_source_urls_without_losing_valid_questions(crawl_scope):
    url = "https://example.com/"
    tavily = FakeTavily([{"url": url, "content": "正文"}])

    async def generate(items):
        return service.WebsiteSynthesis(
            overview="网站概览",
            qa=[
                service.QaItem(
                    question="有效问题",
                    answer="有效答案",
                    source_urls=["<https://example.com/>."],
                )
                for _ in range(14)
            ]
            + [
                service.QaItem(
                    question="无效问题",
                    answer="无效答案",
                    source_urls=["https://invalid.example/"],
                )
            ],
        )

    result = await service.crawl_website(
        url,
        thread_id="thread-1",
        uid="user-1",
        tavily_client=tavily,
        http_client=FakeHttpClient(),
        synthesis_fn=generate,
    )

    output_dir = crawl_scope / "website" / "example.com"
    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert result.status == "created"
    assert manifest["qa"]["status"] == "ready"
    qa = (output_dir / "qa.md").read_text()
    assert qa.count("## ") == 14
    assert "https://example.com/" in qa
    assert "无效问题" not in qa


def test_normalize_url_removes_fragment_and_keeps_query_identity():
    assert service.normalize_url("HTTPS://Example.COM:443/a?q=1#part") == "https://example.com/a?q=1"
    assert service.normalize_url("https://example.com/a?q=2") != service.normalize_url("https://example.com/a?q=1")


@pytest.mark.asyncio
async def test_validate_public_url_rejects_private_resolution(monkeypatch):
    monkeypatch.setattr(
        service.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(service.socket.AF_INET, service.socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )

    with pytest.raises(ValueError, match="公開ネットワークアドレスではありません"):
        await service.validate_public_url("http://example.com/")


@pytest.mark.asyncio
async def test_collect_sources_uses_independent_page_and_pdf_quotas(monkeypatch):
    results = [
        {"url": f"https://example.com/page-{index}", "content": f"page {index}"}
        for index in range(35)
    ]
    results.extend(
        {"url": f"https://example.com/guide-{index}.pdf"}
        for index in range(25)
    )

    async def download(url, host, client):
        return b"pdf", url

    async def rank_pages(pages, entry_url, limit):
        return sorted(pages)[:limit]

    monkeypatch.setattr(service, "_download_pdf", download)
    sources, _, pdfs = await service._collect_sources(
        final_url="https://example.com/",
        final_host="example.com",
        crawl_response={"results": results},
        client=FakeHttpClient(),
        page_rank_fn=rank_pages,
    )

    assert len([item for item in sources if item.status == "ready" and item.content_type == "html"]) == 30
    assert len([item for item in sources if item.status == "ready" and item.content_type == "pdf"]) == 20
    assert len(pdfs) == 20
    assert any(item.status == "skipped" and item.content_type == "html" for item in sources)
    assert any(item.status == "skipped" and item.content_type == "pdf" for item in sources)


@pytest.mark.asyncio
async def test_select_priority_pages_prefers_high_value_over_news():
    pages = {
        "https://example.com/news/2024/01/a": "ニュース記事 A",
        "https://example.com/news/2024/01/b": "ニュース記事 B",
        "https://example.com/about": "会社概要",
        "https://example.com/service": "サービス説明",
        "https://example.com/": "トップページ",
    }

    async def rank_pages(candidate_pages, entry_url, limit):
        assert entry_url == "https://example.com/"
        return [
            "https://example.com/",
            "https://example.com/about",
            "https://example.com/service",
        ][:limit]

    selected = await service._select_priority_pages(
        pages,
        entry_url="https://example.com/",
        limit=3,
        rank_fn=rank_pages,
    )

    assert selected == [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/service",
    ]
    assert all("/news/" not in url for url in selected)


def test_heuristic_rank_pages_deprioritizes_news_paths():
    pages = {
        "https://example.com/news/latest": "news",
        "https://example.com/about": "about",
        "https://example.com/": "home",
        "https://example.com/blog/post-1": "blog",
    }
    ranked = service._heuristic_rank_pages(pages, "https://example.com/")
    assert ranked[0] == "https://example.com/"
    assert ranked.index("https://example.com/about") < ranked.index("https://example.com/news/latest")
    assert ranked.index("https://example.com/about") < ranked.index("https://example.com/blog/post-1")


@pytest.mark.asyncio
async def test_missing_tavily_key_fails_explicitly(monkeypatch, tmp_path):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    result = await service.crawl_website(
        "https://example.com/",
        thread_id="thread-1",
        uid="user-1",
        http_client=FakeHttpClient(),
    )
    assert result.status == "failed"
    assert "TAVILY_API_KEY" in result.message


@pytest.mark.asyncio
async def test_download_pdf_enforces_size_limit(monkeypatch):
    async def allow_public(url):
        return None

    monkeypatch.setattr(service, "validate_public_url", allow_public)
    monkeypatch.setattr(service, "MAX_PDF_BYTES", 3)
    client = FakeDownloadClient(
        [FakeStreamResponse(url="https://example.com/a.pdf", chunks=[b"12", b"34"])]
    )

    with pytest.raises(ValueError, match="10 MiB"):
        await service._download_pdf("https://example.com/a.pdf", "example.com", client)


@pytest.mark.asyncio
async def test_download_pdf_rejects_cross_host_redirect(monkeypatch):
    async def allow_public(url):
        return None

    monkeypatch.setattr(service, "validate_public_url", allow_public)
    client = FakeDownloadClient(
        [
            FakeStreamResponse(
                url="https://example.com/a.pdf",
                status_code=302,
                headers={"location": "https://evil.example/a.pdf"},
            )
        ]
    )

    with pytest.raises(ValueError, match="サイトホスト境界を越えました"):
        await service._download_pdf("https://example.com/a.pdf", "example.com", client)


@pytest.mark.asyncio
async def test_collect_sources_skips_item_at_dataset_size_limit(monkeypatch):
    monkeypatch.setattr(service, "MAX_PAGE_DATASET_BYTES", 6)
    sources, pages, _ = await service._collect_sources(
        final_url="https://example.com/",
        final_host="example.com",
        crawl_response={
            "results": [
                {"url": "https://example.com/a", "content": "1234"},
                {"url": "https://example.com/b", "content": "5678"},
            ]
        },
        client=FakeHttpClient(),
    )
    assert len(pages) == 1
    assert any(item.status == "skipped" and "50 MiB" in item.error for item in sources)


@pytest.mark.asyncio
async def test_collect_sources_enforces_pdf_dataset_size_separately(monkeypatch):
    monkeypatch.setattr(service, "MAX_PDF_DATASET_BYTES", 6)

    async def download(url, host, client):
        return b"1234", url

    monkeypatch.setattr(service, "_download_pdf", download)
    sources, pages, pdfs = await service._collect_sources(
        final_url="https://example.com/",
        final_host="example.com",
        crawl_response={
            "results": [
                {"url": "https://example.com/page", "content": "page"},
                {"url": "https://example.com/a.pdf"},
                {"url": "https://example.com/b.pdf"},
            ]
        },
        client=FakeHttpClient(),
    )

    assert len(pages) == 1
    assert len(pdfs) == 1
    assert any(item.status == "skipped" and "PDF資料集" in item.error for item in sources)


def test_atomic_publish_restores_old_directory_when_stage_rename_fails(monkeypatch, tmp_path):
    output_dir = tmp_path / "example.com"
    output_dir.mkdir()
    (output_dir / "old.txt").write_text("old")
    stage_dir = tmp_path / ".example.com.tmp-test"
    stage_dir.mkdir()
    (stage_dir / "new.txt").write_text("new")
    original_rename = service.Path.rename

    def fail_stage_rename(self, target):
        if self == stage_dir:
            raise OSError("publish failed")
        return original_rename(self, target)

    monkeypatch.setattr(service.Path, "rename", fail_stage_rename)
    with pytest.raises(OSError, match="publish failed"):
        service._publish_atomically(stage_dir, output_dir)
    assert (output_dir / "old.txt").read_text() == "old"
