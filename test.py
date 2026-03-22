import requests
import json

# ====== 配置（填你的）======
APP_ID = "cli_a934e0f7e9f89bef"
APP_SECRET = "78eaee7PwchV64tYYvuFJhid7noHW1Tl"

APP_TOKEN = "Lv7ibXCiValnMOs3SULcZnWLnJf"
TABLE_ID = "tblsZfsj8CsYxaYm"


# ====== 1. 获取 tenant_access_token ======
def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    res = requests.post(url, json=payload)
    data = res.json()

    if data.get("code") != 0:
        print("❌ 获取token失败:", data)
        return None

    return data["tenant_access_token"]


# ====== 2. 写入一条记录 ======
def write_record(token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
       "fields": {
         "采集日期": "2026-03-21",
        "采集方式": "自动采集",
        "来源关键词": "深圳带货主播",
        "原笔记链接": "https://test.com",
        "原笔记标题": "测试标题",
        "原笔记正文": "测试内容"
    }
    }

    res = requests.post(url, headers=headers, json=payload)
    data = res.json()

    print("📌 写入结果：")
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ====== 主流程 ======
if __name__ == "__main__":
    token = get_access_token()
    if token:
        print("✅ token获取成功")
        write_record(token)