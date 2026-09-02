import json

DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"


def build_requests_session(randomUA=True, mobileUA=False):
    import requests
    from fake_useragent import UserAgent

    session = requests.Session()
    if randomUA:
        if mobileUA:
            session.headers.update({"User-Agent": UserAgent(platforms=["mobile"]).random})
        else:
            session.headers.update({"User-Agent": UserAgent().random})
    else:
        session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
    return session


def get_data(env_key, mock_config):
    try:
        import baihu  # pyright: ignore[reportMissingImports]

        global ENV

        ENV = baihu.get_env(env_key)
        if ENV:
            return json.loads(ENV.get("value"))
        else:
            return None
    except ImportError:
        print("\n💡[提示]未检测到白虎面板环境, 自动启用本地 Mock 数据...\n")
        return json.loads(mock_config)


def notify_and_save(env_key, data, title, content):
    print(f"\n准备通知:\n---\n{content}\n---")
    try:
        import baihu  # pyright: ignore[reportMissingImports]

        resp = baihu.notify(title, content)
        if resp:
            print(f"通知响应: {resp}")
            if json.loads(resp).get("data", {}).get("success", False):
                baihu.update_env(id=ENV.get("id"), name=env_key, value=json.dumps(data))
                print("通知成功, 已更新数据")
            else:
                print("通知失败, 不更新数据")

    except ImportError:
        print("\n💡[提示]未检测到白虎面板环境, 不通知不更新\n")


def notify(title, content):
    print(f"\n准备通知:\n---\n{content}\n---")
    try:
        import baihu  # pyright: ignore[reportMissingImports]

        resp = baihu.notify(title, content)
        if resp:
            print(f"通知响应: {resp}")
            if json.loads(resp).get("data", {}).get("success", False):
                print("通知成功")
            else:
                print("通知失败")

    except ImportError:
        print("\n💡[提示]未检测到白虎面板环境, 不通知\n")
