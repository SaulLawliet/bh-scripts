import json


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
