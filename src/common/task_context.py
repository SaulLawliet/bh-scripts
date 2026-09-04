import json
import os
import sys

from dotenv import load_dotenv


class TaskContext:
    def __init__(self, env_key: str, name: str, mock_config: str):
        self.env_key = env_key
        self.name = name

        self.env = None
        self.data = self._init_data(mock_config)

    def _init_data(self, mock_config: str):
        try:
            import baihu  # pyright: ignore[reportMissingImports]

            self.env = baihu.get_env(self.env_key)
            data = json.loads(self.env.get("value")) if self.env else None
        except ImportError:
            print("\n💡[提示]未检测到白虎面板环境, 自动启用本地 Mock / .env 数据...\n")

            data = json.loads(mock_config) if mock_config else None

            if isinstance(data, dict):
                load_dotenv()
                # 暂时只读第一层的key，后续可能需要支持深层递归
                for key, val in data.items():
                    if isinstance(val, str) and val.startswith("__") and val.endswith("__") and len(val) > 4:
                        data[key] = os.getenv(val[2:-2], "")

        if not data:
            print("未检测到环境变量, 跳过!")
            sys.exit(0)

        return data

    def notify(self, content: str, title: str | None = None):
        print(f"\n准备通知:\n---\n{content}\n---")
        try:
            import baihu  # pyright: ignore[reportMissingImports]

            resp = baihu.notify(title or self.name, content)
            if resp:
                print(f"通知响应: {resp}")
                if json.loads(resp).get("data", {}).get("success", False):
                    print("通知成功")
                    return
            print("通知失败")
        except ImportError:
            print("\n💡[提示]未检测到白虎面板环境, 不通知\n")

    def notify_and_save(self, content: str, title: str | None = None):
        print(f"\n准备通知:\n---\n{content}\n---")
        try:
            import baihu  # pyright: ignore[reportMissingImports]

            resp = baihu.notify(title or self.name, content)
            if resp:
                print(f"通知响应: {resp}")
                if json.loads(resp).get("data", {}).get("success", False):
                    baihu.update_env(
                        id=self.env.get("id"),
                        name=self.env_key,
                        value=json.dumps(self.data, ensure_ascii=False),
                    )
                    print("通知成功, 已更新数据")
                    return
            print("通知失败, 不更新数据")
        except ImportError:
            print("\n💡[提示]未检测到白虎面板环境, 不通知不更新\n")
