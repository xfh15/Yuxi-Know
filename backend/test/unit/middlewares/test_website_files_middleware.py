from __future__ import annotations

import json
from types import SimpleNamespace

from langchain_core.messages import SystemMessage

import yuxi.agents.middlewares.website_files as website_files
from yuxi.agents.middlewares.website_files import WebsiteFilesMiddleware


class FakeRequest:
    def __init__(self, context):
        self.runtime = SimpleNamespace(context=context)
        self.system_message = SystemMessage(content="base")

    def override(self, **kwargs):
        request = FakeRequest(self.runtime.context)
        request.system_message = kwargs.get("system_message", self.system_message)
        return request


def write_manifest(root, directory, *, valid=True):
    target = root / "website" / directory
    target.mkdir(parents=True)
    content = {"final_host": directory, "fingerprint": "abc"} if valid else {"final_host": directory}
    (target / "manifest.json").write_text(json.dumps(content))


def test_middleware_injects_only_current_thread_published_manifests(monkeypatch, tmp_path):
    thread_one = tmp_path / "thread-one"
    thread_two = tmp_path / "thread-two"
    write_manifest(thread_one, "example.com")
    write_manifest(thread_two, "other.example")
    monkeypatch.setattr(
        website_files,
        "sandbox_outputs_dir",
        lambda thread_id: thread_one if thread_id == "thread-1" else thread_two,
    )

    request = WebsiteFilesMiddleware()._with_website_prompt(
        FakeRequest(SimpleNamespace(thread_id="thread-1", uid="user-1"))
    )
    prompt = request.system_message.text
    assert "example.com" in prompt
    assert "other.example" not in prompt
    assert "glob" in prompt and "grep" in prompt and "read_file" in prompt
    assert "先只使用一次" in prompt
    assert "不要再调用" in prompt
    assert "禁止先扫描整个目录" in prompt
    assert "原始 URL" in prompt


def test_middleware_ignores_temporary_and_broken_manifests(monkeypatch, tmp_path):
    root = tmp_path / "outputs"
    write_manifest(root, ".example.com.tmp-1")
    write_manifest(root, "broken.example", valid=False)
    corrupt = root / "website" / "corrupt.example"
    corrupt.mkdir(parents=True)
    (corrupt / "manifest.json").write_text("not-json")
    monkeypatch.setattr(website_files, "sandbox_outputs_dir", lambda thread_id: root)

    original = FakeRequest(SimpleNamespace(thread_id="thread-1", uid="user-1"))
    result = WebsiteFilesMiddleware()._with_website_prompt(original)
    assert result is original


def test_middleware_prefers_file_thread_id(monkeypatch, tmp_path):
    file_root = tmp_path / "file-thread"
    write_manifest(file_root, "shared.example")
    monkeypatch.setattr(
        website_files,
        "sandbox_outputs_dir",
        lambda thread_id: file_root if thread_id == "file-thread" else tmp_path / "empty",
    )
    context = SimpleNamespace(file_thread_id="file-thread", thread_id="child-thread", uid="user-1")
    result = WebsiteFilesMiddleware()._with_website_prompt(FakeRequest(context))
    assert "shared.example" in result.system_message.text
