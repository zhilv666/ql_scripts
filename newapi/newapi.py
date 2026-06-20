"""
author: zhilv
邮箱: zhilv666@qq.com
功能: New API 通用签到 (开了 Tunsite 签不了)
环境变量: NEW_API_XV_TOKENS=[{"cookies": "xxx=xxx;xxx=xxx", "website": "http://xxx.com", "user": "1234", "name": "name1"}, {"cookies": "xxx=xxx;xxx=xxx", "website": "website2", "user": "1235", , "name": "name2"}]
"""

from notify import wecom_bot
import requests
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()


class L:
    def __init__(self, name) -> None:
        self.name = name if name else "unknown"
        self.logs = []

    def info(self, *args):
        text = f"【{self.name}】{args}"
        print(text)
        self.logs.append(text)

    @property
    def log(self):
        return "\n".join(self.logs)


def checkin(cookies: str, user: str, website: str, l: L):
    response = requests.post(
        f"{website}/api/user/checkin",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "origin": website,
            "new-api-user": user,
            "referer": f"{website}/console/personal",
            "Cookie": cookies,
        },
    )
    try:
        response.raise_for_status()

        data = response.json()

        success = data.get("success", False)
        message = data.get("message", "unknown")
        quota = int(data.get("data", {}).get("quota_awarded", 0))

        # new-api 默认:
        # 500000 quota ≈ $1
        usd = quota / 500000

        if success:
            l.info(f"签到成功 ✅️ | " f"约 ${usd:.4f}")
        else:
            l.info(f"签到失败 ❌️ : {message}")

    except ValueError:
        l.info(f"JSON解析失败 ❌️ : {response.text}")

    except Exception as e:
        l.info(f"签到异常 ❌️ : {e}")


def main():
    env_name = "NEW_API_TOKENS"
    LOGS = []

    raw = os.getenv(env_name)
    if not raw:
        print(f"⛔️ 未获取到ck变量：请检查变量 {env_name} 是否填写")
        exit(0)

    items: list[dict] = json.loads(raw)
    for item in items:
        l = L(item.get("name", ""))
        checkin(
            item.get("cookies", ""), item.get("user", ""), item.get("website", ""), l
        )
        LOGS.append(l.log)
        time.sleep(1)
    wecom_bot("NewAPI 签到", "\n".join(LOGS))


if __name__ == "__main__":
    main()
