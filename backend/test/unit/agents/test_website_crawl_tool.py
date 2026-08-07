from types import SimpleNamespace

import pytest
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command

import yuxi.agents.toolkits.buildin.website_crawl as website_tool
from yuxi.agents.context import _default_resource_keys
from yuxi.agents.state import BaseState
from yuxi.agents.toolkits.service import _extract_tool_info, resolve_configured_runtime_tools
from yuxi.services.website_crawl_service import CrawlResult


class _CrawlWebsiteModel(BaseChatModel):
    """首次调用网站抓取工具；工具结束后不应再请求模型。"""

    call_count: int = 0

    @property
    def _llm_type(self) -> str:
        return "crawl-website-direct-return"

    def bind_tools(self, tools, **kwargs):  # noqa: ARG002
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):  # noqa: ARG002
        self.call_count += 1
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call-1",
                                "name": "crawl_website",
                                "args": {"url": "https://example.com"},
                            }
                        ],
                    )
                )
            ]
        )


@pytest.mark.asyncio
async def test_tool_uses_file_thread_scope_and_updates_artifacts(monkeypatch):
    captured = {}

    async def fake_service(url, **kwargs):
        captured.update(url=url, **kwargs)
        return CrawlResult(
            "created",
            "example.com",
            2,
            1,
            0,
            ["website/example.com/index.md", "website/example.com/qa.md", "website/example.com/manifest.json"],
            "ok",
            pages=2,
            pdfs=0,
            qa_count=15,
        )

    monkeypatch.setattr(website_tool, "crawl_website_service", fake_service)
    runtime = SimpleNamespace(
        config={"configurable": {}},
        context=SimpleNamespace(file_thread_id="files-1", thread_id="child-1", uid="user-1"),
        state={},
        tool_call_id="call-1",
    )
    result = await website_tool.crawl_website.coroutine(
        url="https://example.com",
        runtime=runtime,
    )

    assert isinstance(result, Command)
    assert captured["url"] == "https://example.com"
    assert captured["thread_id"] == "files-1"
    assert captured["uid"] == "user-1"
    assert captured["language"] == "ja"
    assert callable(captured["progress_callback"])
    assert result.update["artifacts"][-1].endswith("/website/example.com/manifest.json")

    tool_message = result.update["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    payload = json.loads(tool_message.content)
    assert payload["pages"] == 2
    assert payload["pdfs"] == 0
    assert payload["qa"] == 15
    assert "ページ：2 件" in payload["summary"]
    assert "PDF：0 件" in payload["summary"]
    assert "Q&A：15 件" in payload["summary"]


@pytest.mark.asyncio
async def test_tool_returns_error_message_without_artifacts(monkeypatch):
    async def fake_service(url, **kwargs):
        return CrawlResult("failed", None, 0, 0, 1, [], "bad url")

    monkeypatch.setattr(website_tool, "crawl_website_service", fake_service)
    runtime = SimpleNamespace(
        config={},
        context=SimpleNamespace(thread_id="t1", uid="u1"),
        state={},
        tool_call_id="call-1",
    )
    result = await website_tool.crawl_website.coroutine(url="bad", runtime=runtime)
    assert result.update["artifacts"] == []
    tool_message = result.update["messages"][0]
    payload = json.loads(tool_message.content)
    assert "bad url" in payload["message"]
    assert "サイト資料の収集に失敗しました" in payload["summary"]
    assert "bad url" in payload["summary"]


@pytest.mark.asyncio
async def test_tool_node_injects_runtime_and_tool_call_id(monkeypatch):
    """真实执行器只传业务参数时，工具仍能获得线程作用域和调用 ID。"""

    captured = {}

    async def fake_service(url, **kwargs):
        captured.update(url=url, **kwargs)
        return CrawlResult("created", "example.com", 1, 0, 0, ["website/example.com/index.md"], "ok")

    monkeypatch.setattr(website_tool, "crawl_website_service", fake_service)
    runtime = Runtime()
    config = {"configurable": {"file_thread_id": "files-1", "uid": "user-1"}}
    tool_call = {
        "name": "crawl_website",
        "args": {"url": "https://example.com"},
        "id": "call-1",
        "type": "tool_call",
    }

    result = await ToolNode([website_tool.crawl_website])._afunc([tool_call], config, runtime)

    assert captured["url"] == "https://example.com"
    assert captured["thread_id"] == "files-1"
    assert captured["uid"] == "user-1"
    assert captured["language"] == "ja"
    assert callable(captured["progress_callback"])
    assert result[0].update["messages"][0].tool_call_id == "call-1"


def test_tool_metadata_exposes_only_business_arguments():
    """管理界面读取工具元数据时，不应序列化 ToolRuntime。"""

    metadata = _extract_tool_info(website_tool.crawl_website)

    assert metadata["slug"] == "crawl_website"
    assert metadata["args"] == [
        {
            "name": "url",
            "type": "string",
            "description": "収集・整理する公開HTTP/HTTPS Webサイトの入口URL",
        }
    ]


@pytest.mark.asyncio
async def test_tool_completion_ends_agent_without_second_model_call(monkeypatch):
    """网站资料发布后直接结束本轮，不再触发模型读取和核验文件。"""

    async def fake_service(url, **kwargs):
        return CrawlResult(
            "created",
            "example.com",
            1,
            0,
            0,
            ["website/example.com/index.md"],
            "ok",
            pages=1,
            pdfs=0,
            qa_count=15,
        )

    monkeypatch.setattr(website_tool, "crawl_website_service", fake_service)
    model = _CrawlWebsiteModel()
    agent = create_agent(model=model, tools=[website_tool.crawl_website], state_schema=BaseState)

    result = await agent.ainvoke(
        {"messages": [HumanMessage("整理 https://example.com")]},
        config={"configurable": {"file_thread_id": "files-1", "uid": "user-1"}},
    )

    assert model.call_count == 1
    assert result["artifacts"] == ["/home/gem/user-data/outputs/website/example.com/index.md"]
    tool_message = next(msg for msg in result["messages"] if isinstance(msg, ToolMessage))
    payload = json.loads(tool_message.content)
    # 用户消息是中文，因此总结跟随中文。
    assert "页面：1 个" in payload["summary"]
    assert "Q&A：15 条" in payload["summary"]


@pytest.mark.parametrize(
    ("result", "language", "expected_lines"),
    [
        (
            CrawlResult(
                "created",
                "example.com",
                3,
                1,
                0,
                ["website/example.com/index.md"],
                "ok",
                pages=2,
                pdfs=1,
                qa_count=15,
            ),
            "ja",
            [
                "サイト資料の収集が完了し、現在の会話スレッドへ公開しました。",
                "ページ：2 件",
                "PDF：1 件",
                "Q&A：15 件",
            ],
        ),
        (
            CrawlResult("failed", None, 0, 0, 1, [], "network error"),
            "ja",
            ["サイト資料の収集に失敗しました。", "network error"],
        ),
        (
            CrawlResult(
                "created",
                "example.com",
                3,
                1,
                0,
                ["website/example.com/index.md"],
                "ok",
                pages=2,
                pdfs=1,
                qa_count=15,
            ),
            "zh",
            ["网站资料收集完成，并已发布到当前对话。", "页面：2 个", "PDF：1 个", "Q&A：15 条"],
        ),
        (
            CrawlResult(
                "created",
                "example.com",
                3,
                1,
                0,
                ["website/example.com/index.md"],
                "ok",
                pages=2,
                pdfs=1,
                qa_count=15,
            ),
            "en",
            [
                "Website materials were collected and published to this conversation.",
                "Pages: 2",
                "PDFs: 1",
                "Q&A: 15",
            ],
        ),
    ],
)
def test_build_user_summary_by_language(result, language, expected_lines):
    summary = website_tool._build_user_summary(result, language)
    for line in expected_lines:
        assert line in summary


@pytest.mark.asyncio
async def test_tool_only_enters_runtime_when_explicitly_selected():
    without_tool = await resolve_configured_runtime_tools(SimpleNamespace(tools=[], mcps=[], skills=[]))
    with_tool = await resolve_configured_runtime_tools(SimpleNamespace(tools=["crawl_website"], mcps=[], skills=[]))
    assert "crawl_website" not in {tool.name for tool in without_tool}
    assert "crawl_website" in {tool.name for tool in with_tool}


def test_tool_is_excluded_from_default_tool_selection():
    available = ["ask_user_question", "crawl_website", "present_artifacts"]
    assert _default_resource_keys("tools", available) == ["ask_user_question", "present_artifacts"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("このサイトを整理してください", "ja"),
        ("请整理这个网站", "zh"),
        ("Please organize this website", "en"),
        ("https://example.com", "ja"),
    ],
)
def test_tool_detects_language_from_latest_user_message(query, expected):
    runtime = SimpleNamespace(state={"messages": [HumanMessage(query)]})

    assert website_tool._preferred_language(runtime) == expected
