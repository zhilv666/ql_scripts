"""
author: zhilv
email: zhilv666@qq.com
功能: New API 通用签到

环境变量:
  NEW_API_TOKENS 或 NEW_API_XV_TOKENS
  值示例:
  [
    {
      "token": "xxx",
      "website": "https://example.com",
      "user": "1234",
      "name": "example"
    }
  ]

可选环境变量:
  NEW_API_PROXY=http://127.0.0.1:9000
  NEW_API_TIMEOUT=20
  NEW_API_DELAY=1
  NEW_API_VERIFY_SSL=false
"""

from __future__ import annotations

import json
import os
import time
import warnings
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests
from requests import Response, Session
from requests.exceptions import RequestException
from urllib3.exceptions import InsecureRequestWarning

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_: Any, **__: Any) -> bool:
        return False

try:
    from notify import wecom_bot
except ImportError:
    wecom_bot = None


load_dotenv()

TOKEN_ENV_NAMES = ("NEW_API_TOKENS", "NEW_API_XV_TOKENS")
DEFAULT_TIMEOUT = 20
DEFAULT_DELAY = 1.0
QUOTA_PER_USD = 500000


@dataclass
class Account:
    token: str
    website: str
    user: str
    name: str = "unknown"

    @property
    def base_url(self) -> str:
        return self.website.rstrip("/")


@dataclass
class CheckinResult:
    name: str
    success: bool
    message: str
    quota: int = 0
    remaining_quota: int | None = None
    remaining_message: str = ""
    status_code: int | None = None

    @property
    def usd(self) -> float:
        return self.quota / QUOTA_PER_USD

    @property
    def remaining_usd(self) -> float | None:
        if self.remaining_quota is None:
            return None
        return self.remaining_quota / QUOTA_PER_USD


@dataclass
class QuotaResult:
    success: bool
    quota: int = 0
    message: str = ""
    status_code: int | None = None

    @property
    def usd(self) -> float:
        return self.quota / QUOTA_PER_USD


class Logger:
    def __init__(self, name: str) -> None:
        self.name = name or "unknown"
        self.logs: list[str] = []

    def info(self, *args: Any) -> None:
        message = " ".join(str(arg) for arg in args)
        text = f"【{self.name}】{message}"
        print(text)
        self.logs.append(text)

    @property
    def log(self) -> str:
        return "\n".join(self.logs)


def getenv_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def getenv_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        print(f"[WARN] 环境变量 {name}={value!r} 不是有效数字，已使用默认值 {default}")
        return default


def get_token_env() -> tuple[str | None, str | None]:
    for env_name in TOKEN_ENV_NAMES:
        raw = os.getenv(env_name)
        if raw and raw.strip():
            return env_name, raw.strip()
    return None, None


def normalize_account(item: dict[str, Any], index: int) -> Account:
    token = str(item.get("token") or "").strip()
    website = str(item.get("website") or item.get("url") or "").strip()
    user = str(item.get("user") or item.get("user_id") or "").strip()
    name = str(item.get("name") or item.get("remark") or f"account-{index}").strip()

    missing = []
    if not token:
        missing.append("token")
    if not website:
        missing.append("website")
    if not user:
        missing.append("user")
    if missing:
        raise ValueError(f"第 {index} 个账号缺少字段: {', '.join(missing)}")

    parsed = urlparse(website)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"第 {index} 个账号 website 不合法: {website}")

    return Account(token=token, website=website, user=user, name=name)


def load_accounts() -> list[Account]:
    env_name, raw = get_token_env()
    if not raw:
        names = " 或 ".join(TOKEN_ENV_NAMES)
        raise RuntimeError(f"未获取到账号变量，请填写环境变量 {names}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"环境变量 {env_name} 不是合法 JSON: {exc}") from exc

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise RuntimeError(f"环境变量 {env_name} 必须是 JSON 数组或对象")

    accounts: list[Account] = []
    errors: list[str] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 个账号不是 JSON 对象")
            continue
        try:
            accounts.append(normalize_account(item, index))
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        raise RuntimeError("\n".join(errors))
    if not accounts:
        raise RuntimeError(f"环境变量 {env_name} 中没有可用账号")

    print(f"已从 {env_name} 加载 {len(accounts)} 个账号")
    return accounts


def build_session() -> Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/145.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        }
    )
    return session


def build_proxies() -> dict[str, str] | None:
    proxy = os.getenv("NEW_API_PROXY", "").strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def build_account_headers(account: Account) -> dict[str, str]:
    return {
        "Origin": account.base_url,
        "Referer": f"{account.base_url}/console/personal",
        "New-API-User": account.user,
        "Authorization": f"Bearer {account.token}",
    }


def parse_response(response: Response, account: Account) -> CheckinResult:
    try:
        data = response.json()
    except ValueError:
        text = response.text.strip()
        if len(text) > 300:
            text = f"{text[:300]}..."
        return CheckinResult(
            name=account.name,
            success=False,
            message=f"JSON 解析失败: {text or '空响应'}",
            status_code=response.status_code,
        )

    success = bool(data.get("success", False))
    message = str(data.get("message") or data.get("msg") or "unknown")
    quota = data.get("data", {}).get("quota_awarded", 0)

    try:
        quota = int(quota or 0)
    except (TypeError, ValueError):
        quota = 0

    return CheckinResult(
        name=account.name,
        success=success,
        message=message,
        quota=quota,
        status_code=response.status_code,
    )


def parse_quota_response(response: Response) -> QuotaResult:
    try:
        data = response.json()
    except ValueError:
        text = response.text.strip()
        if len(text) > 300:
            text = f"{text[:300]}..."
        return QuotaResult(
            success=False,
            message=f"JSON 解析失败: {text or '空响应'}",
            status_code=response.status_code,
        )

    success = bool(data.get("success", False))
    message = str(data.get("message") or data.get("msg") or "unknown")
    payload = data.get("data", {})
    quota = payload.get("quota", 0) if isinstance(payload, dict) else 0

    try:
        quota = int(quota or 0)
    except (TypeError, ValueError):
        quota = 0

    return QuotaResult(
        success=success,
        quota=quota,
        message=message,
        status_code=response.status_code,
    )


def checkin(
    session: Session,
    account: Account,
    *,
    timeout: float,
    proxies: dict[str, str] | None,
    verify_ssl: bool,
) -> CheckinResult:
    url = f"{account.base_url}/api/user/checkin"
    headers = build_account_headers(account)

    try:
        response = session.post(
            url,
            headers=headers,
            timeout=timeout,
            proxies=proxies,
            verify=verify_ssl,
        )
    except RequestException as exc:
        return CheckinResult(account.name, False, f"请求异常: {exc}")

    result = parse_response(response, account)
    if not response.ok:
        result.success = False
        result.message = f"HTTP {response.status_code}: {result.message}"
    return result


def get_remaining_quota(
    session: Session,
    account: Account,
    *,
    timeout: float,
    proxies: dict[str, str] | None,
    verify_ssl: bool,
) -> QuotaResult:
    url = f"{account.base_url}/api/user/self"
    headers = build_account_headers(account)

    try:
        response = session.get(
            url,
            headers=headers,
            timeout=timeout,
            proxies=proxies,
            verify=verify_ssl,
        )
    except RequestException as exc:
        return QuotaResult(False, message=f"请求异常: {exc}")

    result = parse_quota_response(response)
    if not response.ok:
        result.success = False
        result.message = f"HTTP {response.status_code}: {result.message}"
    return result


def format_remaining(result: CheckinResult) -> str:
    if result.remaining_usd is not None:
        return f"剩余总额度 ${result.remaining_usd:.4f}"
    if result.remaining_message:
        return f"剩余额度获取失败: {result.remaining_message}"
    return "剩余额度未知"


def format_result(result: CheckinResult) -> str:
    if result.success:
        return f"✅ 签到成功 | 获得 ${result.usd:.4f} | {format_remaining(result)}"
    return f"❌ 签到失败 | {result.message} | {format_remaining(result)}"


def format_notify_result(result: CheckinResult) -> str:
    if result.success:
        return f"【{result.name}】签到成功 ✅ | 获得 ${result.usd:.4f} | {format_remaining(result)}"
    return f"【{result.name}】签到失败 ❌ | {result.message} | {format_remaining(result)}"


def send_notify(content: str) -> None:
    if not getenv_bool("NEW_API_NOTIFY", True):
        return
    if wecom_bot is None:
        return
    try:
        wecom_bot("New API 签到", content)
    except Exception as exc:
        print(f"[WARN] 通知发送失败: {exc}")


def main() -> None:
    try:
        accounts = load_accounts()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return

    timeout = getenv_float("NEW_API_TIMEOUT", DEFAULT_TIMEOUT)
    delay = getenv_float("NEW_API_DELAY", DEFAULT_DELAY)
    verify_ssl = getenv_bool("NEW_API_VERIFY_SSL", False)
    proxies = build_proxies()

    if not verify_ssl:
        warnings.simplefilter("ignore", InsecureRequestWarning)

    if proxies:
        print(f"已启用代理: {proxies['http']}")
    print(f"SSL 校验: {'开启' if verify_ssl else '关闭'}")

    session = build_session()
    notify_logs: list[str] = []
    results: list[CheckinResult] = []

    for index, account in enumerate(accounts, start=1):
        logger = Logger(account.name)
        logger.info(f"开始签到: {account.base_url}")

        result = checkin(
            session,
            account,
            timeout=timeout,
            proxies=proxies,
            verify_ssl=verify_ssl,
        )
        quota_result = get_remaining_quota(
            session,
            account,
            timeout=timeout,
            proxies=proxies,
            verify_ssl=verify_ssl,
        )
        if quota_result.success:
            result.remaining_quota = quota_result.quota
        else:
            result.remaining_message = quota_result.message

        results.append(result)
        logger.info(format_result(result))
        notify_logs.append(format_notify_result(result))

        if index < len(accounts) and delay > 0:
            time.sleep(delay)

    success_count = sum(1 for result in results if result.success)
    fail_count = len(results) - success_count
    summary = f"New API 签到完成: 成功 {success_count} 个，失败 {fail_count} 个"
    print(summary)

    send_notify("\n".join(notify_logs))


if __name__ == "__main__":
    main()
