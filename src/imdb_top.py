"""
name: "IMDb Top 10"
cron: "0 1 0 * * *"
"""

import json

from bs4 import BeautifulSoup

from common import Session, TaskContext

NAME = "IMDb Top 10"
ENV_KEY = "IMDB_TOP10"
MOCK_CONFIG = '{"last_top10": []}'
URL = "https://www.imdb.com/chart/top/?sort=release_date%2Cdesc&mode=simple&page=1"


def fetch_top10(session: Session) -> list[dict]:
    # 使用社交媒体抓取 UA 可避免被 AWS WAF 拦截 (202 质询)
    headers = {
        "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = session.get(URL, headers=headers)
    if resp.status_code != 200:
        print(f"请求失败, 状态码: {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        print("未在页面中找到 __NEXT_DATA__ 数据标签")
        return []

    try:
        data = json.loads(script.string)
        chart_titles = (
            data.get("props", {}).get("pageProps", {}).get("pageData", {}).get("chartTitles", {}).get("edges", [])
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"解析 __NEXT_DATA__ 失败: {e}")
        return []

    top10 = []
    for edge in chart_titles[:10]:
        node = edge.get("node", {})
        title_id = node.get("id")
        title = node.get("titleText", {}).get("text", "")
        year = node.get("releaseYear", {}).get("year")
        rating = node.get("ratingsSummary", {}).get("aggregateRating")
        rank_top250 = edge.get("currentRank")
        release_date = node.get("releaseDate", {})
        date_str = ""
        if release_date and release_date.get("year"):
            y = release_date.get("year")
            m = release_date.get("month")
            d = release_date.get("day")
            if m and d:
                date_str = f"{y}-{m:02d}-{d:02d}"
            else:
                date_str = str(y)

        top10.append(
            {
                "id": title_id,
                "title": title,
                "year": year,
                "rating": rating,
                "rank_top250": rank_top250,
                "release_date": date_str,
            }
        )

    return top10


def main():
    ctx = TaskContext(ENV_KEY, NAME, MOCK_CONFIG)
    session = Session(randomUA=False)

    current_top10 = fetch_top10(session)
    if not current_top10:
        print("获取 IMDb 前10名数据为空，退出")
        return

    current_titles = [m.get("title", "") for m in current_top10]
    last_top10 = ctx.data.get("last_top10", [])
    if not isinstance(last_top10, list):
        last_top10 = []

    # 首次运行记录初始化数据
    if not last_top10:
        print("首次运行，初始化记录当前 IMDb Top 10 数据：")
        for idx, item in enumerate(current_top10, 1):
            rating_str = f"⭐{item['rating']}" if item.get("rating") else "暂无评分"
            rank_str = f"(Top 250 #{item['rank_top250']})" if item.get("rank_top250") else ""
            print(f"{idx}. {item['title']} ({item.get('year')}) {rating_str} {rank_str}")

        ctx.data["last_top10"] = current_titles
        content = f"{NAME} (最新上映) 初始化成功，当前前10名：\n"
        for idx, item in enumerate(current_top10, 1):
            rating_str = f"⭐{item['rating']}" if item.get("rating") else "暂无评分"
            rank_str = f"(Top 250 #{item['rank_top250']})" if item.get("rank_top250") else ""
            content += f"\n{idx}. {item['title']} ({item.get('year')}) {rating_str} {rank_str}"

        ctx.notify_and_save(content)
        return

    # 判断是否有变动（顺序或内容）
    has_changed = last_top10 != current_titles

    if has_changed:
        print("检测到 IMDb Top 10 发生变动！")
        new_in_top10 = [m for m in current_top10 if m.get("title") not in last_top10]
        out_of_top10 = [title for title in last_top10 if title not in current_titles]

        content = f"{NAME} 榜单变动！\n"
        if new_in_top10:
            content += "\n🎉 新进前10名："
            for m in new_in_top10:
                rating_str = f"⭐{m['rating']}" if m.get("rating") else ""
                rank_str = f"(Top 250 #{m['rank_top250']})" if m.get("rank_top250") else ""
                content += f"\n+ {m['title']} ({m.get('year')}) {rating_str} {rank_str}"

        if out_of_top10:
            content += "\n\n🔻 跌出前10名："
            for title in out_of_top10:
                content += f"\n- {title}"

        content += "\n\n📋 当前最新前10名："
        for idx, m in enumerate(current_top10, 1):
            rating_str = f"⭐{m['rating']}" if m.get("rating") else "暂无评分"
            rank_str = f"#{m['rank_top250']}" if m.get("rank_top250") else ""
            is_new = " [新上榜]" if m.get("title") not in last_top10 else ""
            content += f"\n{idx}. {m['title']} ({m.get('year')}) {rating_str} ({rank_str}){is_new}"

        ctx.data["last_top10"] = current_titles

        ctx.notify_and_save(content)
    else:
        print("IMDb Top 10 无变化，不通知")


if __name__ == "__main__":
    main()
