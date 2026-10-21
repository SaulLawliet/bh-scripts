"""
name: "92号汽油价格"
cron: "0 0 8 * * *"
"""

from common import Session, TaskContext

NAME = "92号汽油价格"
ENV_KEY = "GAS_PRICE"
MOCK_CONFIG = '{"provinces": [{"name": "北京", "last_update": ""}]}'

SWITCH_PROVINCE_URL = "https://cx.sinopecsales.com/yjkqiantai/data/switchProvince"
INIT_MAIN_DATA_URL = "https://cx.sinopecsales.com/yjkqiantai/data/initMainData"

# 中国石化省份ID与名称映射表
PROVINCE_MAP = {
    "11": "北京",
    "12": "天津",
    "13": "河北",
    "14": "山西",
    "15": "内蒙古",
    "21": "辽宁",
    "22": "吉林",
    "23": "黑龙江",
    "31": "上海",
    "32": "江苏",
    "33": "浙江",
    "34": "安徽",
    "35": "福建",
    "36": "江西",
    "37": "山东",
    "41": "河南",
    "42": "湖北",
    "43": "湖南",
    "44": "广东",
    "45": "广西",
    "46": "海南",
    "50": "重庆",
    "51": "四川",
    "52": "贵州",
    "53": "云南",
    "54": "西藏",
    "61": "陕西",
    "62": "甘肃",
    "63": "青海",
    "64": "宁夏",
    "65": "新疆",
}

NAME_TO_PROVINCE_ID = {name: pid for pid, name in PROVINCE_MAP.items()}


def resolve_province_id(name_or_id: str) -> tuple[str | None, str]:
    """通过省份名（如'辽宁'、'辽宁省'）或ID解析出对应的中石化provinceId和规范省份名"""
    raw = str(name_or_id).strip()
    if raw in PROVINCE_MAP:
        return raw, PROVINCE_MAP[raw]

    if raw in NAME_TO_PROVINCE_ID:
        return NAME_TO_PROVINCE_ID[raw], raw

    # 尝试去除常见的行政区后缀
    clean_name = raw
    for suffix in ("壮族自治区", "维吾尔自治区", "回族自治区", "特别行政区", "自治区", "省", "市"):
        if clean_name.endswith(suffix) and len(clean_name) > len(suffix):
            clean_name = clean_name[: -len(suffix)]
            break

    if clean_name in NAME_TO_PROVINCE_ID:
        return NAME_TO_PROVINCE_ID[clean_name], clean_name

    # 模糊包含匹配
    for pid, prov_name in PROVINCE_MAP.items():
        if prov_name in raw or raw in prov_name:
            return pid, prov_name

    return None, raw


def query_province_gas_92(session: Session, province_id: str):
    """查询指定省份的92号/E92号汽油价格信息"""
    resp = session.post(SWITCH_PROVINCE_URL, json={"provinceId": str(province_id)})
    if resp.status_code != 200:
        print(f"切换省份失败 (provinceId: {province_id}), 状态码: {resp.status_code}")
        return None

    resp = session.get(INIT_MAIN_DATA_URL)
    if resp.status_code != 200:
        print(f"获取油价数据失败 (provinceId: {province_id}), 状态码: {resp.status_code}")
        return None

    json_data = resp.json()
    data = json_data.get("data", {})
    to_day = json_data.get("toDay", "")
    province_check = data.get("provinceCheck", {})
    province_name = province_check.get("PROVINCE_NAME") or PROVINCE_MAP.get(str(province_id), f"省份_{province_id}")

    province_data = data.get("provinceData")
    areas = data.get("area", [])

    if province_data:
        target_items = [("", province_check, province_data)]
    elif areas:
        target_items = [
            (
                a.get("areaCheck", {}).get("AREA_NAME", ""),
                a.get("areaCheck", {}),
                a.get("areaData", {}),
            )
            for a in areas
        ]
    else:
        target_items = []

    results = []
    for area_name, check, price_data in target_items:
        fuel_name = "92号"
        if check.get("E92") == "Y":
            fuel_name = "E92号"

        price = price_data.get("GAS_92") or price_data.get("E92")
        status = (
            price_data.get("GAS_92_STATUS")
            if price_data.get("GAS_92_STATUS") is not None
            else price_data.get("E92_STATUS", 0.0)
        )
        start_date = price_data.get("START_DATE", "")

        results.append(
            {
                "province_name": province_name,
                "area_name": area_name,
                "fuel_name": fuel_name,
                "price": price,
                "status": status,
                "start_date": start_date,
                "to_day": to_day,
            }
        )

    return results


def format_status(status: float | None) -> str:
    if status is None or status == 0.0:
        return "持平"
    if status > 0:
        return f"+{status:.2f} ↗"
    return f"{status:.2f} ↘"


def main():
    ctx = TaskContext(ENV_KEY, NAME, MOCK_CONFIG)

    session = Session()
    session.headers.update({"Referer": "https://cx.sinopecsales.com/yjkqiantai/"})

    # 兼容多种配置格式：[{"name": "辽宁", "last_update": ""}] 或 ["辽宁"]
    raw_provinces = ctx.data.get("provinces", [])
    if not isinstance(raw_provinces, list):
        raw_provinces = []

    provinces = []
    for item in raw_provinces:
        if isinstance(item, dict):
            item.setdefault("last_update", "")
            provinces.append(item)
        elif isinstance(item, str):
            provinces.append({"name": item, "last_update": ""})

    # 回写到 ctx.data 中，确保保存时不包含多余字段
    ctx.data["provinces"] = provinces

    if not provinces:
        print("未配置查询省份，退出。")
        return

    notify_contents = []
    has_update = False

    for prov in provinces:
        name_input = prov.get("name", "")
        prov_id, standard_name = resolve_province_id(name_input)

        if not prov_id:
            print(f"\n未匹配到省份: '{name_input}'，请检查名称是否正确")
            continue

        prov["name"] = standard_name
        last_update = prov.get("last_update", "")

        print(f"\n正在查询: {standard_name}...")
        results = query_province_gas_92(session, prov_id)
        if not results:
            print(f"未获取到 {standard_name} 的油价数据")
            continue

        start_date = results[0].get("start_date", "")
        print(f"查询结果: {standard_name} 最新生效时间: {start_date}, 上次记录生效时间: {last_update or '无'}")

        # 检查是否变动（通过生效时间判断）
        is_changed = bool(start_date and start_date != last_update)
        if is_changed:
            has_update = True
            prov["last_update"] = start_date

        for res in results:
            area_text = f" - {res['area_name']}" if res["area_name"] else ""
            status_text = format_status(res["status"])
            item_msg = (
                f"【{res['province_name']}{area_text}】{res['fuel_name']}汽油: {res['price']} 元/升 ({status_text})"
            )
            if res.get("start_date"):
                item_msg += f"\n生效时间: {res['start_date']}"
            print(item_msg)

            if is_changed:
                notify_contents.append(item_msg)

    if has_update and notify_contents:
        summary_text = "\n\n".join(notify_contents)
        ctx.notify_and_save(f"{NAME}更新提醒\n\n{summary_text}")
    else:
        print("\n所有配置省份的油价生效时间均无更新，无需推送通知。")


if __name__ == "__main__":
    main()
