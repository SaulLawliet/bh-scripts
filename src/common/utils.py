import requests
from fake_useragent import UserAgent

DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"


def build_requests_session(randomUA=True, mobileUA=False):
    session = requests.Session()
    if randomUA:
        if mobileUA:
            session.headers.update({"User-Agent": UserAgent(platforms=["mobile"]).random})
        else:
            session.headers.update({"User-Agent": UserAgent().random})
    else:
        session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
    return session
