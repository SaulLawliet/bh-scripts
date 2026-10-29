"""
name: "轻小说文库"
cron: "0 1 0 * * *"
"""

from bs4 import BeautifulSoup

from common import Session, TaskContext

NAME = "轻小说文库"
ENV_KEY = "WENKU8"
MOCK_CONFIG = '{"proxy": false, "novels": [{"id": 1861, "last_chapter": ""}]}'


def main():
    ctx = TaskContext(ENV_KEY, NAME, MOCK_CONFIG)

    session = Session(randomUA=False, proxy=ctx.data.get("proxy", False))
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1",
            "Referer": "https://www.wenku8.net/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        }
    )

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
