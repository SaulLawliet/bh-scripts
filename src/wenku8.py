"""
name: "轻小说文库"
cron: "0 0 0 * * *"
"""

from bs4 import BeautifulSoup

from common import TaskContext, build_requests_session

NAME = "轻小说文库"
ENV_KEY = "WENKU8"
MOCK_CONFIG = '{"novels": [{"id": 1861, "last_chapter": ""}]}'


def main():
    ctx = TaskContext(ENV_KEY, NAME, MOCK_CONFIG)

    session = build_requests_session(mobileUA=True)

    for novel in ctx.data.get("novels"):
        print(novel)
        resp = session.get(f"https://www.wenku8.net/modules/article/reader.php?aid={novel.get('id')}")
        if resp.status_code != 200:
            print(f"请求失败, 状态码: {resp.status_code}")
            continue

        soup = BeautifulSoup(resp.content.decode("gbk"), "html.parser")
        title = soup.select_one("#title").text
        last_chapter = soup.select(".vcss")[-1].text

        if last_chapter != novel.get("last_chapter"):
            print(f"小说 {title} 有更新, 最新章节: {last_chapter}")
            novel["last_chapter"] = last_chapter
            ctx.notify_and_save(f"{title}\n\n更新啦: {last_chapter}")
        else:
            print(f"小说 {title} 无更新, 最新章节: {last_chapter}")


if __name__ == "__main__":
    main()
