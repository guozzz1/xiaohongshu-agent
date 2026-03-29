"""
飞书多维表连通性小测试（从 .env 读密钥，勿在代码里写死）。
用法：配置好 .env 后执行  python test.py
"""
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID", "").strip()
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "").strip()
APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "").strip()
TABLE_ID = os.getenv("FEISHU_TABLE_ID", "").strip()


def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    res = requests.post(url, json=payload, timeout=20)
    data = res.json()
    if data.get("code") != 0:
        print("获取 token 失败:", data)
        return None
    return data["tenant_access_token"]


def write_record(token: str) -> None:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "fields": {
            "采集日期": "2099-01-01",
            "采集方式": "test.py 连通性测试",
            "来源关键词": "test",
            "原笔记链接": "https://example.com/test",
            "原笔记标题": "测试标题",
            "原笔记正文": "测试内容",
        }
    }
    res = requests.post(url, headers=headers, json=payload, timeout=30)
    print(json.dumps(res.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if not all([APP_ID, APP_SECRET, APP_TOKEN, TABLE_ID]):
        raise SystemExit("请先在 .env 中配置 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_APP_TOKEN / FEISHU_TABLE_ID")
    t = get_access_token()
    if t:
        print("token 获取成功，尝试写入一条测试记录…")
        write_record(t)
