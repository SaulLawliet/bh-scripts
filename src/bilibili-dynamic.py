"""
name: "B站动态"
cron: "0 1 10-23 * * *"

Q: Cookie 1-2天就过期了
A: https://github.com/DIYgod/RSSHub/issues/12207#issuecomment-1636718921
   用隐身模式登陆获取 Cookie 后关闭浏览器, 即可有很长的有效期
"""

from utils import build_requests_session, get_data, notify, notify_and_save

NAME = "B站动态"
ENV_KEY = "BILIBILI_DYNAMIC"
MOCK_CONFIG = '{"cookie": "", "last_ts": 0}'


def main():
    config = get_data(ENV_KEY, MOCK_CONFIG)
    if not config:
        print("未检测到环境变量, 跳过!")
        return

    session = build_requests_session(randomUA=False)
    session.headers.update({"cookie": config.get("cookie")})

    resp = session.get("https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all?type=video&platform=web&page=1")
    if resp.status_code != 200:
        print(f"请求失败, 状态码: {resp.status_code}")
        return

    data = resp.json().get("data", {})
    if not data:
        notify(NAME, "Cookie已过期, 请更换Cookie")
        return

    last_ts = int(config.get("last_ts", 0))
    content = ""
    for index, item in enumerate(data.get("items", [])):
        module_author = item.get("modules", {}).get("module_author", {})
        author = module_author.get("name")
        ts = int(module_author.get("pub_ts", 0))

        archive = item.get("modules", {}).get("module_dynamic", {}).get("major", {}).get("archive", {})
        title = archive.get("title")
        url = archive.get("jump_url")

        if index == 0:
            config.update({"last_ts": ts})

        if ts <= last_ts:
            print(f"已通知过的时间戳, {title}, ts: {ts}")
            continue

        print(f"新动态, {author}: {title}")
        content += f"\n{author}: {title} (https:{url})"

    if content:
        notify_and_save(ENV_KEY, config, NAME, f"{NAME}\n\n{content}")


if __name__ == "__main__":
    main()
