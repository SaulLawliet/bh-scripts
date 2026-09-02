"""
name: "Trakt"
cron: "0 0 0 * * *"

用浏览器抓包, 找到下面URL的请求头中的 api_key 和 access_token, 填入环境变量中即可
"""

from utils import build_requests_session, get_data, notify, notify_and_save

NAME = "Trakt"
ENV_KEY = "TRAKT"
MOCK_CONFIG = '{"api_key": "", "access_token": ""}'


def main():
    config = get_data(ENV_KEY, MOCK_CONFIG)
    if not config:
        print("未检测到环境变量, 跳过!")
        return

    session = build_requests_session()
    session.headers.update(
        {
            "trakt-api-version": "2",
            "trakt-api-key": config.get("api_key"),
            "authorization": f"Bearer {config.get('access_token')}",
        }
    )

    resp = session.get(
        "https://apiz.trakt.tv/sync/progress/up_next_nitro?page=1&limit=100&intent=continue&sort_how=desc"
    )
    if resp.status_code != 200:
        print(f"请求失败, 状态码: {resp.status_code}")
        notify(NAME, f"{NAME}请求失败, 状态码: {resp.status_code}, 请检查 api_key 和 access_token 是否正确")
        return

    if config.get("progress_list") is None:
        config["progress_list"] = {}

    content = ""
    for show in resp.json():
        show_title = show.get("show", {}).get("title")
        next_episode = show.get("progress", {}).get("next_episode", {})

        if next_episode:
            season_episode = f"S{next_episode.get('season'):02d}E{next_episode.get('number'):02d}"

            title = next_episode.get("title")
            first_aired = next_episode.get("first_aired")

            show_id = str(show.get("show_id"))
            if config.get("progress_list", {}).get(show_id, {}).get("current") != season_episode:
                content += f"\n\n{show_title}\n{season_episode} - {title}\n{first_aired}"

                config["progress_list"][show_id] = {
                    "current": season_episode,
                    "title": show_title,
                }
            else:
                print(f"{show_title} {season_episode} 已通知过, 跳过")
    if content:
        notify_and_save(ENV_KEY, config, NAME, f"{NAME}{content}")
    else:
        print("无新影集, 不通知")


if __name__ == "__main__":
    main()
