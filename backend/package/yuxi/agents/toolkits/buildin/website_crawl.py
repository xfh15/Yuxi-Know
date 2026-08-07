"""チャット内蔵ツールを使用して、公開Webサイトを現在のスレッドのファイル領域に整理する。"""

from __future__ import annotations

import json
import re
from typing import Annotated

from langchain_core.messages import ToolMessage
from langgraph.config import get_stream_writer
from langgraph.prebuilt.tool_node import ToolRuntime
from langgraph.types import Command
from pydantic import Field

from yuxi.agents.toolkits.registry import tool
from yuxi.services.website_crawl_service import CrawlResult
from yuxi.services.website_crawl_service import crawl_website as crawl_website_service
from yuxi.utils.paths import VIRTUAL_PATH_OUTPUTS


CRAWL_WEBSITE_DESCRIPTION = """公開Webサイトを現在の会話スレッドのファイル領域に収集・整理します。

ユーザーがWebサイトの「収集・整理・学習」を明示的に依頼した場合のみ使用し、メッセージにURLが含まれているだけの場合は使用しないでください。
Tavily Crawlで同一ホストのWebページを収集し、同一ホストのPDFをダウンロードし、完了後に簡潔な統計情報と
資料ファイルのパスを返します。
本ツールの実行中は他のツールを並行して呼び出さないでください。ツール完了後はこのターンを終了し、生成されたファイルを再度読み込んだり、検索・検証したりしないでください。
Webサイトに関する質問に回答する際は、まず該当するqa.mdのみを読み取ってください。回答がない場合に限り、index.mdから関連するソースファイルを正確に読み取り、
記載された原URLを引用してください。
この機能にはTAVILY_API_KEYの設定が必要です。固定制限は最大深度2、最大幅20、
Webページ最大30件、PDF最大20件、1 PDFあたり10 MiB、PDF合計50 MiBです。
"""


@tool(
    category="buildin",
    tags=["Webサイト", "ファイル"],
    display_name="Webサイト資料を収集",
    config_guide="TAVILY_API_KEYの設定が必要です。公開HTTP/HTTPS Webサイトのみを処理します。",
    description=CRAWL_WEBSITE_DESCRIPTION,
    return_direct=True,
)
async def crawl_website(
    url: Annotated[str, Field(description="収集・整理する公開HTTP/HTTPS Webサイトの入口URL")],
    runtime: ToolRuntime,
) -> Command:
    """Webサイトを収集し、現在のスレッドで表示できるインデックス、Q&A、ソース一覧を登録する。"""

    tool_call_id = runtime.tool_call_id or ""
    thread_id = _runtime_value(runtime, "file_thread_id") or _runtime_value(runtime, "thread_id")
    uid = _runtime_value(runtime, "uid")
    if not thread_id or not uid:
        return _tool_command(
            tool_call_id,
            CrawlResult("failed", None, 0, 0, 1, [], "実行時コンテキストにthread_idまたはuidがありません"),
        )

    language = _preferred_language(runtime)
    progress_writer = _get_progress_writer()

    async def report_progress(percent: int, message: str) -> None:
        if progress_writer is not None:
            progress_writer(
                {
                    "type": "yuxi.tool_progress",
                    "tool_name": "crawl_website",
                    "progress": percent,
                    "message": message,
                }
            )

    result = await crawl_website_service(
        url,
        thread_id=thread_id,
        uid=uid,
        language=language,
        progress_callback=report_progress,
    )
    return _tool_command(tool_call_id, result, language=language)


def _tool_command(tool_call_id: str, result: CrawlResult, *, language: str = "ja") -> Command:
    """サービス結果を短いツールメッセージとLangGraphの成果物差分に変換する。"""

    user_summary = _build_user_summary(result, language)
    summary = {
        "status": result.status,
        "host": result.final_host,
        "pages": result.pages,
        "pdfs": result.pdfs,
        "qa": result.qa_count,
        "ready": result.ready,
        "skipped": result.skipped,
        "failed": result.failed,
        "message": result.message,
        "summary": user_summary,
        "language": language,
    }
    artifacts = []
    if result.status != "failed" and result.final_host:
        artifacts = [f"{VIRTUAL_PATH_OUTPUTS}/{path}" for path in result.paths]
        summary["files"] = artifacts
    return Command(
        update={
            "artifacts": artifacts,
            # return_direct 后不会再请求模型，因此把可读总结放进 ToolMessage 供前端直接展示。
            "messages": [
                ToolMessage(
                    content=json.dumps(summary, ensure_ascii=False),
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


def _build_user_summary(result: CrawlResult, language: str) -> str:
    """根据页面 / PDF / QA 统计生成用户可见的简短总结。"""

    host = result.final_host or "-"
    pages = result.pages
    pdfs = result.pdfs
    qa_count = result.qa_count
    skipped = result.skipped
    failed = result.failed
    message = (result.message or "").strip()

    if language == "zh":
        if result.status == "failed":
            reason = f"\n原因：{message}" if message else ""
            return f"网站资料收集失败。{reason}".strip()
        status_line = {
            "created": "网站资料收集完成，并已发布到当前对话。",
            "updated": "网站资料已更新，并重新发布到当前对话。",
            "unchanged": "网站内容未变化，沿用当前对话中的已有资料。",
        }.get(result.status, "网站资料处理完成。")
        return (
            f"{status_line}\n"
            f"\n"
            f"- 主机：{host}\n"
            f"- 页面：{pages} 个\n"
            f"- PDF：{pdfs} 个\n"
            f"- Q&A：{qa_count} 条\n"
            f"- 跳过：{skipped} 项\n"
            f"- 失败：{failed} 项"
        )

    if language == "en":
        if result.status == "failed":
            reason = f"\nReason: {message}" if message else ""
            return f"Website material collection failed.{reason}".strip()
        status_line = {
            "created": "Website materials were collected and published to this conversation.",
            "updated": "Website materials were updated and republished to this conversation.",
            "unchanged": "The site has not changed; existing materials in this conversation were kept.",
        }.get(result.status, "Website material processing finished.")
        return (
            f"{status_line}\n"
            f"\n"
            f"- Host: {host}\n"
            f"- Pages: {pages}\n"
            f"- PDFs: {pdfs}\n"
            f"- Q&A: {qa_count}\n"
            f"- Skipped: {skipped}\n"
            f"- Failed: {failed}"
        )

    # 默认日语
    if result.status == "failed":
        reason = f"\n理由：{message}" if message else ""
        return f"サイト資料の収集に失敗しました。{reason}".strip()
    status_line = {
        "created": "サイト資料の収集が完了し、現在の会話スレッドへ公開しました。",
        "updated": "サイト資料を更新し、現在の会話スレッドへ再公開しました。",
        "unchanged": "サイト内容に変更がないため、現在の会話スレッドの既存資料をそのまま利用します。",
    }.get(result.status, "サイト資料の処理が完了しました。")
    return (
        f"{status_line}\n"
        f"\n"
        f"- ホスト：{host}\n"
        f"- ページ：{pages} 件\n"
        f"- PDF：{pdfs} 件\n"
        f"- Q&A：{qa_count} 件\n"
        f"- スキップ：{skipped} 件\n"
        f"- 失敗：{failed} 件"
    )


def _get_progress_writer():
    """LangGraphのカスタムイベント書き込み関数を取得する。ストリーミング実行環境外では進捗イベントを無効にする。"""

    try:
        return get_stream_writer()
    except (RuntimeError, LookupError):
        return None


def _preferred_language(runtime: ToolRuntime) -> str:
    """現在のユーザーメッセージから資料言語を判定し、判定できない場合は日本語を既定値にする。"""

    messages = _runtime_messages(runtime)
    for message in reversed(messages):
        text = _message_text(message)
        if not text:
            continue
        if re.fullmatch(r"https?://\S+", text.strip(), flags=re.IGNORECASE):
            continue
        if re.search(r"[\u3040-\u30ff]", text):
            return "ja"
        if re.search(r"[\u4e00-\u9fff]", text):
            return "zh"
        if re.search(r"[A-Za-z]", text):
            return "en"
    return "ja"


def _runtime_messages(runtime: ToolRuntime) -> list:
    """実行時状態のメッセージ一覧を読み取り、辞書とPydanticメッセージオブジェクトの両方に対応する。"""

    state = getattr(runtime, "state", None)
    if isinstance(state, dict):
        messages = state.get("messages")
    else:
        messages = getattr(state, "messages", None)
    return messages if isinstance(messages, list) else []


def _message_text(message: object) -> str:
    """言語判定用にメッセージ本文を抽出する。"""

    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item if isinstance(item, str) else str(item.get("text", ""))
            for item in content
            if isinstance(item, str) or isinstance(item, dict)
        )
    return ""


def _runtime_value(runtime: ToolRuntime, key: str) -> str | None:
    """設定、context、stateの順に実行スコープの値を読み取る。"""

    config = getattr(runtime, "config", None)
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    state = getattr(runtime, "state", None)
    for source in (configurable, getattr(runtime, "context", None), state if isinstance(state, dict) else {}):
        value = source.get(key) if isinstance(source, dict) else getattr(source, key, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
