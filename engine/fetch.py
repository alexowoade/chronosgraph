import urllib.parse
from typing import List
import requests
from bs4 import BeautifulSoup

def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ChronosGraph-ROCm/2.0"})
    return session

def keyless_search(session: requests.Session, query: str, max_results: int = 4) -> List[str]:
    urls = []
    try:
        r = session.post("https://html.duckduckgo.com/html/", data={"q": query}, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("a.result__a"):
                href = a.get("href", "")
                if "uddg=" in href:
                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if "uddg" in qs:
                        href = qs["uddg"][0]
                if href.startswith("http") and href not in urls:
                    urls.append(href)
                if len(urls) >= max_results:
                    break
    except Exception:
        pass
    return urls
