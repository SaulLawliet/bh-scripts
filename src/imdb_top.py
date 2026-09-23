"""
name: "IMDb Top"
cron: "0 1 0 * * *"
"""

import json

from bs4 import BeautifulSoup

from common import Session, TaskContext

NAME = "IMDb Top"
ENV_KEY = "IMDB_TOP10"
MOCK_CONFIG = '{"cookie": "__IMDB_COOKIE__", "top": 10, "last_unwatched": []}'
URL = "https://www.imdb.com/chart/top/?sort=release_date%2Cdesc&mode=simple&page=1"


def format_movie(item: dict, prefix: str = "", suffix: str = "") -> str:
    rating = f"⭐{item['rating']}" if item.get("rating") else ""
    rank = f"(Top 250 #{item['rank_top250']})" if item.get("rank_top250") else ""
    meta = f"{rating} {rank}".strip()
    year = f" ({item['year']})" if item.get("year") else ""
    indent = "  " if prefix.startswith(("+", "-")) else "   "
    return (
        f"{prefix}{item['title']}{year}\n{indent}{meta}{suffix}".rstrip()
        if meta
        else f"{prefix}{item['title']}{year}{suffix}"
    )


def fetch_watched_titles(session: Session, ctx: TaskContext) -> tuple[set[str], set[str]] | None:
    try:
        resp = session.get("https://www.imdb.com/list/watchhistory/", allow_redirects=False)
        location = resp.headers.get("Location")

        if resp.status_code in (401, 403) or not location or any(k in location.lower() for k in ["signin", "login"]):
            print("Cookie 已失效，需重新登录")
            ctx.notify("IMDb Cookie 已失效，请重新获取并更新 Cookie")
            return None

        target_url = f"https://www.imdb.com{location}" if location.startswith("/") else location
        resp2 = session.get(target_url)
        if resp2.status_code != 200 or "/signin" in resp2.url.lower():
            print(f"获取观影历史失败, 状态码: {resp2.status_code}")
            ctx.notify("IMDb Cookie 已失效，请重新获取并更新 Cookie")
            return None

        soup = BeautifulSoup(resp2.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            print("未在 IMDb 观影历史页面找到数据")
            ctx.notify("未在 IMDb 观影历史页面找到数据，Cookie 可能已失效，请重新获取并更新 Cookie")
            return None

        data = json.loads(script.string)
        edges = (
            data.get("props", {})
            .get("pageProps", {})
            .get("mainColumnData", {})
            .get("advancedTitleSearch", {})
            .get("edges", [])
        )

        watched_ids = {
            e.get("node", {}).get("title", {}).get("id") for e in edges if e.get("node", {}).get("title", {}).get("id")
        }
        watched_titles = {
            e.get("node", {}).get("title", {}).get("titleText", {}).get("text")
            for e in edges
            if e.get("node", {}).get("title", {}).get("titleText", {}).get("text")
        }
        print(f"已获取用户标记为 watched 的电影数量: {len(watched_ids)}")
        return watched_ids, watched_titles
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        print(f"解析观影历史失败: {e}")
        ctx.notify(f"获取 IMDb 观影历史异常: {e}，请检查 Cookie 是否有效")
        return None


def fetch_top_unwatched(
    session: Session, top_limit: int, watched_ids: set[str], watched_titles: set[str]
) -> list[dict]:
    resp = session.get(URL)
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

    unwatched = []
    for edge in chart_titles[:top_limit]:
        node = edge.get("node", {})
        title_id = node.get("id")
        title = node.get("titleText", {}).get("text", "")
        if title_id in watched_ids or title in watched_titles:
            continue

        unwatched.append(
            {
                "title": title,
                "year": node.get("releaseYear", {}).get("year"),
                "rating": node.get("ratingsSummary", {}).get("aggregateRating"),
                "rank_top250": edge.get("currentRank"),
            }
        )

    return unwatched


def main():
    ctx = TaskContext(ENV_KEY, NAME, MOCK_CONFIG)
    session = Session(randomUA=False)
    session.headers.update(
        {
            "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.imdb.com/",
        }
    )

    top_limit = int(ctx.data.get("top", 10))
    cookie = ctx.data.get("cookie", "")
    if cookie == "IMDB_COOKIE":
        import os

        cookie = os.getenv("IMDB_COOKIE", "")

    if not cookie:
        print("未配置 IMDb Cookie，中断运行")
        ctx.notify("未配置 IMDb Cookie，无法排除已看电影，请先配置 Cookie")
        return

    session.headers.update({"cookie": cookie})
    watched_res = fetch_watched_titles(session, ctx)
    if watched_res is None:
        print("由于 Cookie 失效或获取观影历史失败，程序中断")
        return
    watched_ids, watched_titles = watched_res

    current_unwatched = fetch_top_unwatched(session, top_limit, watched_ids, watched_titles)
    current_titles = [m.get("title", "") for m in current_unwatched]
    last_unwatched = ctx.data.get("last_unwatched", [])

    # 首次运行记录初始化数据
    if not last_unwatched and current_titles:
        print(f"首次运行，初始化记录当前 IMDb Top {top_limit} 中的未读电影：")
        lines = [format_movie(item, prefix=f"{i}. ") for i, item in enumerate(current_unwatched, 1)]
        for line in lines:
            print(line)

        ctx.data["last_unwatched"] = current_titles
        content = f"{NAME} (Top {top_limit} 未读电影) 初始化成功，共 {len(current_unwatched)} 部：\n\n" + "\n".join(
            lines
        )
        ctx.notify_and_save(content)
        return

    # 判断是否有变动（顺序或内容）
    if last_unwatched != current_titles:
        print(f"检测到 IMDb Top {top_limit} 未读电影发生变动！")
        new_in_unwatched = [m for m in current_unwatched if m.get("title") not in last_unwatched]
        out_of_unwatched = [title for title in last_unwatched if title not in current_titles]

        content = f"{NAME} (Top {top_limit}) 未读电影发生变动！\n"
        if new_in_unwatched:
            content += "\n🎉 新增未读电影：\n" + "\n".join(format_movie(m, prefix="+ ") for m in new_in_unwatched)

        if out_of_unwatched:
            content += "\n\n🔻 移出未读电影：\n" + "\n".join(f"- {title}" for title in out_of_unwatched)

        if current_unwatched:
            list_lines = [
                format_movie(m, prefix=f"{i}. ", suffix=" [新]" if m.get("title") not in last_unwatched else "")
                for i, m in enumerate(current_unwatched, 1)
            ]
            content += f"\n\n📋 当前 Top {top_limit} 未读电影 ({len(current_unwatched)} 部)：\n" + "\n".join(list_lines)
        else:
            content += f"\n\n📋 当前 Top {top_limit} 中已无未读电影！"

        ctx.data["last_unwatched"] = current_titles
        ctx.notify_and_save(content)
    else:
        print(f"IMDb Top {top_limit} 未读电影无变化，不通知")


if __name__ == "__main__":
    main()
