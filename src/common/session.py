import sys

import requests
from fake_useragent import UserAgent

from common.task_context import TaskContext

DEFAULT_TIMEOUT = 15
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"


class Session(requests.Session):
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        randomUA: bool = True,
        mobileUA: bool = False,
        proxy: bool = False,
    ):
        super().__init__()
        self.timeout = timeout

        if randomUA:
            if mobileUA:
                self.headers.update({"User-Agent": UserAgent(platforms=["mobile"]).random})
            else:
                self.headers.update({"User-Agent": UserAgent().random})
        else:
            self.headers.update({"User-Agent": DEFAULT_USER_AGENT})

        if proxy:
            ctx = TaskContext("PROXY", "", '{"http": "__HTTP_PROXY__"}')
            proxy_url = ctx.data.get("http")
            if not proxy_url or len(proxy_url) == 0:
                print("开启了代理, 但是没有配置代理，程序中断。")
                sys.exit(1)
            else:
                self.proxies = {"http": proxy_url, "https": proxy_url}

    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        print(f"[{'Proxy' if 'http' in self.proxies else 'Direct'}] {method.upper()}: {url}")
        return super().request(method, url, *args, **kwargs)
