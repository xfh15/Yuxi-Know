"""为当前线程已发布的网站资料注入文件检索约束。"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse

from yuxi.agents.backends.sandbox.paths import sandbox_outputs_dir
from yuxi.utils.paths import VIRTUAL_PATH_OUTPUTS


class WebsiteFilesMiddleware(AgentMiddleware[Any, Any, Any]):
    """只根据当前线程有效 manifest 提示模型优先检索网站文件。"""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        return handler(self._with_website_prompt(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await handler(self._with_website_prompt(request))

    def _with_website_prompt(self, request: ModelRequest) -> ModelRequest:
        thread_id = _context_value(request.runtime.context, "file_thread_id") or _context_value(
            request.runtime.context, "thread_id"
        )
        if not thread_id:
            return request
        datasets = _published_datasets(thread_id)
        if not datasets:
            return request

        lines = [
            "## 当前线程的网站资料",
            "",
            "网站资料问答请按最小检索路径执行：先只使用一次 `read_file` 读取对应的 `qa.md`。",
            "如果 `qa.md` 已直接回答用户问题，立即基于该文件作答，",
            "不要再调用 `glob`、`grep` 或读取来源文件。",
            "只有 `qa.md` 没有答案时，才读取 `index.md`，再按索引中的路径精准读取相关来源；",
            "禁止先扫描整个目录。",
            "事实应引用 `qa.md`、Markdown 头部或 `manifest.json` 中的原始 URL；",
            "资料中找不到时明确说明，不要用无来源内容补全。",
            "",
        ]
        for host, directory in datasets:
            root = f"{VIRTUAL_PATH_OUTPUTS}/website/{directory}"
            lines.append(f"- 主机 `{host}`：索引 `{root}/index.md`，文件根目录 `{root}/`")
        prompt = "\n".join(lines)
        return request.override(system_message=append_to_system_message(request.system_message, prompt))


def _published_datasets(thread_id: str) -> list[tuple[str, str]]:
    """读取当前线程一级网站目录下结构完整的 manifest。"""

    root = sandbox_outputs_dir(thread_id) / "website"
    try:
        directories = list(root.iterdir())
    except (FileNotFoundError, NotADirectoryError, OSError):
        return []

    datasets: list[tuple[str, str]] = []
    for directory in sorted(directories, key=lambda item: item.name):
        if not directory.is_dir() or directory.name.startswith("."):
            continue
        try:
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            continue
        host = manifest.get("final_host") if isinstance(manifest, dict) else None
        fingerprint = manifest.get("fingerprint") if isinstance(manifest, dict) else None
        if isinstance(host, str) and host.strip() and isinstance(fingerprint, str) and fingerprint.strip():
            datasets.append((host.strip(), directory.name))
    return datasets


def _context_value(context: Any, key: str) -> str | None:
    value = context.get(key) if isinstance(context, dict) else getattr(context, key, None)
    return value.strip() if isinstance(value, str) and value.strip() else None
