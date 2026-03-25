"""
author: zhilv
邮箱: zhilv666@qq.com
网站: https://www.xiavier.com/
我的邀请链接: https://www.xiavier.com/register?aff=4rfw
功能: 签到
环境变量: NEW_API_XV_TOKENS=[{"session": "session1", "name": "name1", "user": "1234"}, {"session": "session2", "name": "name2", "user": "1235"}]
"""

from notify import wecom_bot
import requests
import json
import os
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


def checkin(session: str, user: str, l: L):
    response = requests.post(
        "https://www.xiavier.com/api/user/checkin",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "origin": "https://www.xiavier.com",
            "new-api-user": user,
            "referer": "https://www.xiavier.com/console/personal",
            "Cookie": f"session={session}",
        },
    )
    try:
        data = response.json()
        if data.get("success"):
            l.info(
                f'签到成功: ${data.get("data", {}).get("quota_awarded", 0) * 0.000002 }'
            )
        else:
            l.info(f"签到失败: ${data}")
    except Exception as e:
        l.info(f"解析数据失败: {e} {response.text}")


def main():
    env_name = "NEW_API_XV_TOKENS"
    LOGS = []

    raw = os.getenv(env_name)
    if not raw:
        print(f"⛔️未获取到ck变量：请检查变量 {env_name} 是否填写")
        exit(0)

    items: list[dict] = json.loads(raw)
    for item in items:
        l = L(item.get("name", ""))
        checkin(item.get("session", ""), item.get("user", ""), l)
        LOGS.append(l.log)
    wecom_bot("xiavier 签到", "\n".join(LOGS))


if __name__ == "__main__":
    main()
