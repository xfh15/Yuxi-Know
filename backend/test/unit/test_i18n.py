from __future__ import annotations

from yuxi.i18n import DEFAULT_LOCALE, resolve_locale, translate_payload, translate_text


def test_resolve_locale_prefers_explicit_header():
    assert resolve_locale("ja-JP", "en-US,en;q=0.9") == "ja-JP"


def test_resolve_locale_falls_back_to_accept_language():
    assert resolve_locale(None, "en-US,en;q=0.9,zh-CN;q=0.8") == "en-US"


def test_resolve_locale_uses_default_when_unsupported():
    assert resolve_locale(None, "fr-FR,fr;q=0.9") == DEFAULT_LOCALE


def test_translate_text_formats_placeholders():
    translated = translate_text("en-US", "登录被锁定，请等待 {remaining_time} 秒后再试", remaining_time=12)
    assert translated == "Login is locked. Please wait 12 seconds and try again."


def test_translate_payload_translates_message_fields_recursively():
    payload = {"success": True, "message": "用户已删除", "detail": {"message": "服务正常运行"}}
    translated = translate_payload("ja-JP", payload)
    assert translated["message"] == "ユーザーを削除しました"
    assert translated["detail"]["message"] == "サービスは正常に稼働しています"
