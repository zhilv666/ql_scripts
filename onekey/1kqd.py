"""
author: zhilv
邮箱: zhilv666@qq.com
网站地址: https://one.idkey.cc/
我的邀请链接: https://one.idkey.cc/?ref=zhilv
功能: 签到
环境变量: ONE_KEY_TOKENS=[{"token": "token1", "name": "name1"}, {"token": "token2", "name": "name2"}]
"""

from notify import send
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


def checkin(token: str, l: L):
    response = requests.post(
        "https://one.idkey.cc/api/user/checkin",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "accept-language": "zh-CN,zh;q=0.9,en-CN;q=0.8,en;q=0.7",
            "authorization": f"Bearer {token}",
            "cache-control": "no-cache",
            "content-length": "0",
            "origin": "https://one.idkey.cc",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://one.idkey.cc/?ref=729999721",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
    )

    try:
        data = response.json()
        if data.get("status", "error") == "success":
            l.info(f'签到成功: 当前积分: {data.get("pixel_points", "")}')
        else:
            l.info(f"签到失败: {data}")
    except Exception as e:
        l.info(f"出现错误: {e} {response.text}")


def main():
    env_name = "ONE_KEY_TOKENS"
    LOGS = []

    raw = os.getenv(env_name)
    if not raw:
        print(f"⛔️未获取到ck变量：请检查变量 {env_name} 是否填写")
        exit(0)

    items: list[dict] = json.loads(raw)
    for item in items:
        l = L(item.get("name", ""))
        checkin(item.get("token", ""), l)
        LOGS.append(l.log)
    send("one key 签到", "\n".join(LOGS))


if __name__ == "__main__":
    main()
