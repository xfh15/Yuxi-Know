from __future__ import annotations

from typing import Any

from fastapi import Request

DEFAULT_LOCALE = "zh-CN"
SUPPORTED_LOCALES = ("zh-CN", "en-US", "ja-JP")

_LOCALE_ALIASES = {
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-hans": "zh-CN",
    "en": "en-US",
    "en-us": "en-US",
    "ja": "ja-JP",
    "ja-jp": "ja-JP",
}

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "服务正常运行": {
        "en-US": "Service is running",
        "ja-JP": "サービスは正常に稼働しています",
    },
    "登录尝试过于频繁，请稍后再试": {
        "en-US": "Too many login attempts. Please try again later.",
        "ja-JP": "ログイン試行が多すぎます。しばらくしてから再試行してください。",
    },
    "配置重新加载成功": {
        "en-US": "Configuration reloaded successfully",
        "ja-JP": "設定を再読み込みしました",
    },
    "获取信息配置失败": {
        "en-US": "Failed to load info configuration",
        "ja-JP": "Failed to load info configuration",
    },
    "重新加载信息配置失败": {
        "en-US": "Failed to reload info configuration",
        "ja-JP": "Failed to reload info configuration",
    },
    "OCR服务健康检查完成": {
        "en-US": "OCR health check completed",
        "ja-JP": "OCR health check completed",
    },
    "无效的凭证": {
        "en-US": "Invalid credentials",
        "ja-JP": "無効な認証情報です",
    },
    "请登录后再访问": {
        "en-US": "Please log in first",
        "ja-JP": "ログインしてからアクセスしてください",
    },
    "当前用户未绑定部门": {
        "en-US": "The current user is not bound to a department",
        "ja-JP": "現在のユーザーは部門に紐付いていません",
    },
    "需要管理员权限": {
        "en-US": "Administrator permission required",
        "ja-JP": "管理者権限が必要です",
    },
    "需要超级管理员权限": {
        "en-US": "Super administrator permission required",
        "ja-JP": "スーパー管理者権限が必要です",
    },
    "登录标识或密码错误": {
        "en-US": "Incorrect login identifier or password",
        "ja-JP": "ログイン識別子またはパスワードが正しくありません",
    },
    "该账户已注销": {
        "en-US": "This account has been deactivated",
        "ja-JP": "このアカウントは削除されています",
    },
    "登录被锁定，请等待 {remaining_time} 秒后再试": {
        "en-US": "Login is locked. Please wait {remaining_time} seconds and try again.",
        "ja-JP": "ログインはロックされています。{remaining_time}秒後に再試行してください。",
    },
    "由于多次登录失败，账户已被锁定 {remaining_time} 秒": {
        "en-US": "Too many failed login attempts. The account is locked for {remaining_time} seconds.",
        "ja-JP": "ログイン失敗が続いたため、アカウントは{remaining_time}秒ロックされています。",
    },
    "用户名或密码错误": {
        "en-US": "Incorrect username or password",
        "ja-JP": "ユーザー名またはパスワードが正しくありません",
    },
    "系统已经初始化，无法再次创建初始管理员": {
        "en-US": "The system has already been initialized and the initial administrator cannot be created again",
        "ja-JP": "The system has already been initialized and the initial administrator cannot be created again",
    },
    "用户ID只能包含字母、数字和下划线": {
        "en-US": "User ID can only contain letters, numbers, and underscores",
        "ja-JP": "User ID can only contain letters, numbers, and underscores",
    },
    "用户ID长度必须在3-20个字符之间": {
        "en-US": "User ID must be between 3 and 20 characters",
        "ja-JP": "User ID must be between 3 and 20 characters",
    },
    "手机号格式不正确": {
        "en-US": "Invalid phone number format",
        "ja-JP": "Invalid phone number format",
    },
    "用户名不能为空": {
        "en-US": "Username cannot be empty",
        "ja-JP": "Username cannot be empty",
    },
    "用户名长度不能少于2个字符": {
        "en-US": "Username must be at least 2 characters",
        "ja-JP": "Username must be at least 2 characters",
    },
    "用户名长度不能超过20个字符": {
        "en-US": "Username cannot exceed 20 characters",
        "ja-JP": "Username cannot exceed 20 characters",
    },
    "用户名只能包含中文、英文、数字和下划线": {
        "en-US": "Username can only contain Chinese characters, letters, numbers, and underscores",
        "ja-JP": "Username can only contain Chinese characters, letters, numbers, and underscores",
    },
    "用户名已存在": {
        "en-US": "Username already exists",
        "ja-JP": "Username already exists",
    },
    "手机号已存在": {
        "en-US": "Phone number already exists",
        "ja-JP": "Phone number already exists",
    },
    "手机号已被其他用户使用": {
        "en-US": "The phone number is already used by another user",
        "ja-JP": "The phone number is already used by another user",
    },
    "不能创建超级管理员账户": {
        "en-US": "Super administrator accounts cannot be created",
        "ja-JP": "Super administrator accounts cannot be created",
    },
    "管理员只能创建普通用户账户": {
        "en-US": "Administrators can only create regular user accounts",
        "ja-JP": "Administrators can only create regular user accounts",
    },
    "普通管理员不能指定部门": {
        "en-US": "Regular administrators cannot assign departments",
        "ja-JP": "Regular administrators cannot assign departments",
    },
    "用户不存在": {
        "en-US": "User does not exist",
        "ja-JP": "User does not exist",
    },
    "只有超级管理员才能修改超级管理员账户": {
        "en-US": "Only super administrators can modify super administrator accounts",
        "ja-JP": "Only super administrators can modify super administrator accounts",
    },
    "不能降级超级管理员账户": {
        "en-US": "Super administrator accounts cannot be downgraded",
        "ja-JP": "Super administrator accounts cannot be downgraded",
    },
    "不能将管理员降级为普通用户，因为该用户是当前部门的唯一管理员": {
        "en-US": "This administrator cannot be downgraded because the user is the only administrator in the current department",
        "ja-JP": "This administrator cannot be downgraded because the user is the only administrator in the current department",
    },
    "只有超级管理员才能修改用户部门": {
        "en-US": "Only super administrators can change a user's department",
        "ja-JP": "Only super administrators can change a user's department",
    },
    "不能修改该用户的部门，因为该用户是当前部门的唯一管理员": {
        "en-US": "This user's department cannot be changed because the user is the only administrator in the current department",
        "ja-JP": "This user's department cannot be changed because the user is the only administrator in the current department",
    },
    "不能删除超级管理员账户": {
        "en-US": "Super administrator accounts cannot be deleted",
        "ja-JP": "Super administrator accounts cannot be deleted",
    },
    "不能删除部门唯一的管理员": {
        "en-US": "The only administrator in the department cannot be deleted",
        "ja-JP": "The only administrator in the department cannot be deleted",
    },
    "不能删除自己的账户": {
        "en-US": "You cannot delete your own account",
        "ja-JP": "You cannot delete your own account",
    },
    "该用户已经被删除": {
        "en-US": "This user has already been deleted",
        "ja-JP": "This user has already been deleted",
    },
    "用户已删除": {
        "en-US": "User deleted successfully",
        "ja-JP": "ユーザーを削除しました",
    },
    "只能上传图片文件": {
        "en-US": "Only image files can be uploaded",
        "ja-JP": "Only image files can be uploaded",
    },
    "文件大小不能超过5MB": {
        "en-US": "File size cannot exceed 5 MB",
        "ja-JP": "File size cannot exceed 5 MB",
    },
    "头像上传成功": {
        "en-US": "Avatar uploaded successfully",
        "ja-JP": "アバターをアップロードしました",
    },
    "头像上传失败: {error}": {
        "en-US": "Avatar upload failed: {error}",
        "ja-JP": "アバターのアップロードに失敗しました: {error}",
    },
    "不能模拟超级管理员账户": {
        "en-US": "Super administrator accounts cannot be impersonated",
        "ja-JP": "Super administrator accounts cannot be impersonated",
    },
}


def _normalize_locale_token(value: str | None) -> str:
    if not value:
        return DEFAULT_LOCALE

    normalized = value.strip().lower().replace("_", "-")
    if normalized in _LOCALE_ALIASES:
        return _LOCALE_ALIASES[normalized]

    base = normalized.split("-")[0]
    return _LOCALE_ALIASES.get(base, DEFAULT_LOCALE)


def resolve_locale(locale_header: str | None = None, accept_language: str | None = None) -> str:
    if locale_header:
        return _normalize_locale_token(locale_header)

    if accept_language:
        for segment in accept_language.split(","):
            token = segment.split(";")[0].strip()
            if not token:
                continue
            locale = _normalize_locale_token(token)
            if locale in SUPPORTED_LOCALES:
                return locale

    return DEFAULT_LOCALE


def get_request_locale(request: Request | None) -> str:
    if request is None:
        return DEFAULT_LOCALE

    state_locale = getattr(request.state, "locale", None)
    if state_locale:
        return state_locale

    return resolve_locale(
        request.headers.get("X-Yuxi-Locale"),
        request.headers.get("Accept-Language"),
    )


def translate_text(locale: str, text: str, **params: Any) -> str:
    translated = _TRANSLATIONS.get(text, {}).get(locale) or _TRANSLATIONS.get(text, {}).get(DEFAULT_LOCALE) or text
    if params:
        return translated.format(**params)
    return translated


def tr(request_or_locale: Request | str | None, text: str, **params: Any) -> str:
    locale = request_or_locale if isinstance(request_or_locale, str) else get_request_locale(request_or_locale)
    return translate_text(locale, text, **params)


def translate_payload(locale: str, payload: Any, field_name: str | None = None) -> Any:
    if isinstance(payload, dict):
        return {key: translate_payload(locale, value, key) for key, value in payload.items()}

    if isinstance(payload, list):
        return [translate_payload(locale, item, field_name) for item in payload]

    if isinstance(payload, str) and field_name in {"detail", "message", "msg"}:
        return translate_text(locale, payload)

    return payload
