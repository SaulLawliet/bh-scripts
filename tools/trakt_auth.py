"""
Trakt PKCE 授权脚本

用于快速完成 Trakt 官方 PKCE 授权，获取 access_token 与 refresh_token。

使用说明:
1. 在 https://trakt.tv/oauth/applications 确认应用的 Redirect URI 填写为: https://localhost
2. 运行命令: python tools/trakt_auth.py
"""

import base64
import hashlib
import json
import os
import sys
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import load_dotenv

REDIRECT_URI = "https://localhost"


def main():
    print("=" * 60)
    print("🎬 Trakt PKCE 授权向导 (无需 Client Secret)")
    print(f"📌 提示: 请确保 Trakt 后台应用 Redirect URI 填写为: {REDIRECT_URI}")
    print("=" * 60)

    # 尝试从 .env 读取已有 CLIENT_ID，若无则手动输入
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    client_id = os.getenv("TRAKT_CLIENT_ID") or input("请输入 Trakt Client ID: ").strip()

    if not client_id:
        print("❌ Client ID 不能为空！")
        sys.exit(1)

    # 1. 生成 PKCE 密钥对
    verifier_bytes = os.urandom(32)
    code_verifier = base64.urlsafe_b64encode(verifier_bytes).decode().rstrip("=")
    challenge_hash = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_hash).decode().rstrip("=")

    # 2. 构造授权 URL
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"https://trakt.tv/oauth/authorize?{urllib.parse.urlencode(params)}"

    print("\n👉 1. 请在浏览器打开以下授权链接:")
    print(auth_url)
    print("\n👉 2. 页面中点击 'Authorize' 授权")
    print(f"👉 3. 页面将跳转到以 {REDIRECT_URI}/?code= 开头的地址 (提示无法访问属正常现象)")
    print("👉 4. 复制浏览器地址栏的完整网址或 code 字符串，粘贴在下方:")

    try:
        webbrowser.open(auth_url)
    except Exception as err:  # noqa: BLE001
        print(f"未能自动打开浏览器: {err}")

    redirected_input = input("\n请输入跳转后的网址或 code: ").strip()
    if not redirected_input:
        print("❌ 输入为空，取消授权")
        sys.exit(1)

    code = redirected_input
    if "code=" in redirected_input:
        parsed = urllib.parse.urlparse(redirected_input)
        queries = urllib.parse.parse_qs(parsed.query)
        code = queries.get("code", [redirected_input])[0]

    # 3. 换取 Token
    print("\n⏳ 正在换取 Access Token 与 Refresh Token...")
    session = requests.Session()

    try:
        resp = session.post(
            "https://api.trakt.tv/oauth/token",
            headers={"Content-Type": "application/json"},
            json={
                "code": code,
                "client_id": client_id,
                "code_verifier": code_verifier,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
    except requests.RequestException as err:
        print(f"❌ 换取 Token 请求失败: {err}")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"❌ 换取 Token 失败 (HTTP {resp.status_code}): {resp.text}")
        sys.exit(1)

    token_data = resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 7776000)

    print("\n🎉 授权成功！")
    print("-" * 60)
    print(f"TRAKT_CLIENT_ID={client_id}")
    print(f"TRAKT_ACCESS_TOKEN={access_token}")
    print(f"TRAKT_REFRESH_TOKEN={refresh_token}")
    print(f"Token 有效期约: {expires_in // 86400} 天")
    print("-" * 60)

    panel_data = {
        "client_id": client_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "progress_list": {},
    }
    print("\n📋 白虎面板 JSON 格式 (可填入环境变量 TRAKT 值中):")
    print(json.dumps(panel_data, ensure_ascii=False, indent=2))
    print("-" * 60)


if __name__ == "__main__":
    main()
