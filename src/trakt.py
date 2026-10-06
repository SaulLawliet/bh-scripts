"""
name: "Trakt"
cron: "0 1 0 * * *"

使用说明:
使用 TRAKT_CLIENT_ID, TRAKT_ACCESS_TOKEN 与 TRAKT_REFRESH_TOKEN 访问接口。
初次授权或 Token 失效无法续期时，请运行: python tools/trakt_auth.py
"""

import requests

from common import Session, TaskContext

NAME = "Trakt"
ENV_KEY = "TRAKT"
MOCK_CONFIG = (
    '{"client_id": "__TRAKT_CLIENT_ID__", "access_token": "__TRAKT_ACCESS_TOKEN__", '
    '"refresh_token": "__TRAKT_REFRESH_TOKEN__", "progress_list": {}}'
)

REDIRECT_URI = "https://localhost"
API_URL = "https://api.trakt.tv/sync/progress/up_next_nitro?page=1&limit=100&intent=continue&sort_how=desc"


def refresh_trakt_token(ctx: TaskContext, session: Session) -> bool:
    """使用 refresh_token 自动刷新 Trakt 访问凭据 (PKCE 免密钥续期)"""
    client_id = ctx.data.get("client_id")
    refresh_token = ctx.data.get("refresh_token")

    if not client_id or not refresh_token:
        print("未配置 client_id 或 refresh_token，无法自动刷新 Token")
        return False

    print("🔄 检测到 Token 过期，正在尝试通过 refresh_token 自动刷新...")
    try:
        resp = session.post(
            "https://api.trakt.tv/oauth/token",
            json={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            token_data = resp.json()
            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")
            if new_access_token:
                ctx.data["access_token"] = new_access_token
                if new_refresh_token:
                    ctx.data["refresh_token"] = new_refresh_token
                ctx.save()

                print("✅ Trakt Token 自动刷新成功并已持久化保存！")
                return True
        else:
            print(f"❌ 刷新 Token 失败, 状态码: {resp.status_code}, 响应: {resp.text}")
    except requests.RequestException as err:
        print(f"❌ 刷新 Token 请求异常: {err}")
    return False


def main():
    ctx = TaskContext(ENV_KEY, NAME, MOCK_CONFIG)

    client_id = ctx.data.get("client_id")
    access_token = ctx.data.get("access_token")

    if not client_id or not access_token:
        print("未检测到 TRAKT_CLIENT_ID 或 TRAKT_ACCESS_TOKEN，请先运行 python tools/trakt_auth.py 授权")
        return

    # 若配置了代理，自动启用
    session = Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "trakt-api-key": client_id,
            "authorization": f"Bearer {access_token}",
        }
    )

    resp = session.get(API_URL)

    # 若遇到 401，尝试使用 refresh_token 自动刷新
    if resp.status_code == 401 and refresh_trakt_token(ctx, session):
        session.headers["authorization"] = f"Bearer {ctx.data.get('access_token')}"
        resp = session.get(API_URL)

    if resp.status_code != 200:
        print(f"请求失败, 状态码: {resp.status_code}, 响应内容: {resp.text}")
        if resp.status_code == 401:
            ctx.notify("Trakt 请求失败, Token 已过期且无法自动续期, 请运行 python tools/trakt_auth.py 重新授权")
        else:
            ctx.notify(f"{NAME}请求失败, 状态码: {resp.status_code}, 请检查配置")
        return

    if ctx.data.get("progress_list") is None:
        ctx.data["progress_list"] = {}

    shows = resp.json()
    current_show_ids = {str(show.get("show_id")) for show in shows if show.get("show_id") is not None}

    # 如果 show 没有出现在进度列表里，那么从 progress_list 里移除
    removed_shows = []
    for show_id in list(ctx.data["progress_list"].keys()):
        if str(show_id) not in current_show_ids:
            show_info = ctx.data["progress_list"].pop(show_id)
            title = show_info.get("title", show_id) if isinstance(show_info, dict) else show_id
            print(f"影集 {title} (ID: {show_id}) 已不在待看列表中, 从 progress_list 移除")
            removed_shows.append(show_id)

    content = ""
    for show in shows:
        show_title = show.get("show", {}).get("title")
        next_episode = show.get("progress", {}).get("next_episode", {})

        if next_episode:
            season_episode = f"S{next_episode.get('season'):02d}E{next_episode.get('number'):02d}"

            title = next_episode.get("title")
            first_aired = next_episode.get("first_aired")

            show_id = str(show.get("show_id"))
            if ctx.data.get("progress_list", {}).get(show_id, {}).get("current") != season_episode:
                content += f"\n\n{show_title}\n{season_episode} - {title}\n{first_aired}"

                ctx.data["progress_list"][show_id] = {
                    "current": season_episode,
                    "title": show_title,
                }
            else:
                print(f"{show_title} {season_episode} 已通知过, 跳过")
    if content:
        ctx.notify_and_save(f"{NAME}{content}")
    elif removed_shows:
        ctx.save()
        print("无新影集, 不通知 (已同步移除已完结或删除的影集)")
    else:
        print("无新影集, 不通知")


if __name__ == "__main__":
    main()
