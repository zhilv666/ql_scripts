"""
author: zhilv
邮箱: zhilv666@qq.com
网站地址: https://xn--66tw07h.com/
我的邀请链接: https://快车.com?c=VVNLMV
功能: 签到
环境变量: KC_COOKIES=[{"cookie": "cookie1", "name": "name1"}, {"cookie": "cookie2", "name": "name2"}]
"""

from notify import send
import requests
import json
import base64
import os


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


def b64Encode(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def b64Decode(text: str) -> str:
    return base64.b64decode(text.encode()).decode()


def sign(cookie: str, l: L):
    response = requests.post(
        "https://wj-kc.com/api/user/sign_use",
        json={"data": b64Encode("{}")},
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "accept-language": "zh-CN,zh;q=0.9,en-CN;q=0.8,en;q=0.7",
            "cache-control": "no-cache",
            "origin": "https://wj-kc.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://wj-kc.com/",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "Cookie": f"{cookie}",
        },
    )

    try:
        data = json.loads(b64Decode(response.json().get("data", None)))
        if data and data.get("code", -1) == 0:
            l.info(f"签到成功: [{data}]")
            l.info("快车代理签到", f"签到成功: [{data}]")
        elif data:
            l.info(f"签到失败: [{data}]")
            l.info("快车代理签到", f"签到失败: [{data}]")
        else:
            l.info(f"签到失败: [{response.json()}]")
            l.info("快车代理签到", f"签到失败: [{response.json()}]")
    except Exception as e:
        l.info(f"读取结果出错: {e}")


def main():
    env_name = "KC_COOKIES"
    LOGS = []

    raw = os.getenv(env_name)
    if not raw:
        print(f"⛔️未获取到ck变量：请检查变量 {env_name} 是否填写")
        exit(0)

    items: list[dict] = json.loads(raw)
    for item in items:
        l = L(item.get("name", ""))
        sign(item.get("cookie", ""), l)
        LOGS.append(l.log)
    send("快车机场", "\n".join(LOGS))


if __name__ == "__main__":
    main()
