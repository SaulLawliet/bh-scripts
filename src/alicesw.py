"""
name: "爱丽丝书屋"
cron: "0 1 0 * * *"
"""

from bs4 import BeautifulSoup

from common import TaskContext, build_requests_session

NAME = "爱丽丝书屋"
ENV_KEY = "ALICESW"
MOCK_CONFIG = '{"novels": [{"id": 32020, "last_chapter": ""}]}'


def main():
    ctx = TaskContext(ENV_KEY, NAME, MOCK_CONFIG)

    session = build_requests_session()

    for novel in ctx.data.get("novels", []):
        novel_id = novel.get("id")

        resp = session.get(f"https://www.alicesw.com/other/chapters/id/{novel_id}.html")

        if resp.status_code != 200:
            print(f"请求失败, 小说 ID: {novel_id}, 状态码: {resp.status_code}")
            continue

        soup = BeautifulSoup(resp.content, "html.parser")
        h1 = soup.find("h1")
        title = h1.text.strip() if h1 else f"小说_{novel_id}"

        chapter_items = soup.select("ul.mulu_list li, ul.section-list li")
        if not chapter_items:
            print(f"小说 {title} 未解析到章节列表")
            continue

        last_item = chapter_items[-1]
        a_tag = last_item.find("a")
        last_chapter = a_tag.text.strip() if a_tag else last_item.text.strip()
        chapter_href = a_tag.get("href", "") if a_tag else ""
        chapter_url = f"https://www.alicesw.com{chapter_href}" if chapter_href.startswith("/") else chapter_href

        if last_chapter != novel.get("last_chapter"):
            print(f"小说 {title} 有更新, 最新章节: {last_chapter}")
            novel["last_chapter"] = last_chapter
            content = f"{title}\n\n更新啦: {last_chapter}"
            if chapter_url:
                content += f"\n{chapter_url}"
            ctx.notify_and_save(content)
        else:
            print(f"小说 {title} 无更新, 最新章节: {last_chapter}")


if __name__ == "__main__":
    main()
