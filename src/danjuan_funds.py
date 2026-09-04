"""
name: "雪球基金"
cron: "0 1,11 19,20,21 * * *"
"""

from utils import build_requests_session, get_data, notify_and_save

NAME = "雪球基金"
ENV_KEY = "DANJUAN_FUNDS"
MOCK_CONFIG = '[{"code": "050025", "principal": 10000, "share": 2500, "last_update": "2026-01-01"}]'


def main():
    funds = get_data(ENV_KEY, MOCK_CONFIG)
    if not funds:
        print("未检测到环境变量, 跳过!")
        return

    for fund in funds:
        print(fund)

        session = build_requests_session()
        resp = session.get(f"https://danjuanfunds.com/djapi/fund/nav/history/{fund.get('code')}?page=1&size=3")
        if resp.status_code != 200:
            print(f"基金 {fund.get('code')}, 请求失败, 状态码: {resp.status_code}")
            continue

        items = resp.json().get("data", {}).get("items", [])
        if items:
            # item: {'date': '2026-08-31', 'nav': '5.6000', 'percentage': '-0.28', 'value': '5.6000'}
            last_update = items[0].get("date")
            if last_update == fund.get("last_update"):
                print(f"基金 {fund.get('code')} 无更新, 最新净值日期: {last_update}")
            else:
                print(f"基金 {fund.get('code')} 有更新, 最新净值日期: {last_update}")
                fund["last_update"] = last_update
                content = f"基金: {fund.get('code')}, 本金: {fund.get('principal')}\n"
                for item in items:
                    now = float(item.get("nav")) * fund.get("share")
                    profit = now - fund.get("principal")
                    profit_margin = ((100 * profit) / fund.get("principal")) if fund.get("principal") else 0

                    content += f"\n{item.get('date')}: {now:.2f} ({profit:.2f} / {profit_margin:.2f}%)"

                notify_and_save(ENV_KEY, funds, NAME, content)


if __name__ == "__main__":
    main()
