"""
name: "B站动态"
cron: "0 1 10-23 * * *"

Q: Cookie 1-2天就过期了
A: https://github.com/DIYgod/RSSHub/issues/12207#issuecomment-1636718921
   用隐身模式登陆获取 Cookie 后关闭浏览器, 即可有很长的有效期
"""

from common import TaskContext, build_requests_session

NAME = "B站动态"
ENV_KEY = "BILIBILI_DYNAMIC"
MOCK_CONFIG = '{"cookie": "__BILIBILI_COOKIE__", "last_ts": 0}'


def main():
    ctx = TaskContext(ENV_KEY, NAME, MOCK_CONFIG)

    session = build_requests_session(randomUA=False)
    session.headers.update({"cookie": ctx.data.get("cookie")})

    resp = session.get("https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all?type=video&platform=web&page=1")
    if resp.status_code != 200:
        print(f"请求失败, 状态码: {resp.status_code}")
        return

    data = resp.json().get("data", {})
    if not data:
        ctx.notify("Cookie已过期, 请更换Cookie")
        return

    last_ts = int(ctx.data.get("last_ts", 0))
    content = ""
    for index, item in enumerate(data.get("items", [])):
        module_author = item.get("modules", {}).get("module_author", {})
        author = module_author.get("name")
        ts = int(module_author.get("pub_ts", 0))

        archive = item.get("modules", {}).get("module_dynamic", {}).get("major", {}).get("archive", {})
        title = archive.get("title")
        url = archive.get("jump_url")

        if index == 0:
            ctx.data.update({"last_ts": ts})

        if ts <= last_ts:
            print(f"已通知过的时间戳, {title}, ts: {ts}")
            continue

        content += f"\n{author}: {title} (https:{url})"

    if content:
        ctx.notify_and_save(f"{NAME}\n{content}")
    else:
        print("无新动态, 不通知")


if __name__ == "__main__":
    main()
