import os, sys, json, requests, re
from urllib.parse import urlsplit
from functools import lru_cache

# Exact hosts and suffixes you accept (mirrors your YAML list)
ALLOWED_HOSTS = {
    "bulbapedia.bulbagarden.net",
    "liquipedia.net",
    "nookipedia.com",
    "en.pornopedia.com",
    "pidgi.net",
    "tolkiengateway.net",
    "bg3.wiki",
    "fallout.wiki",
    "ffxiclopedia.fandom.com",
    "kidicaruswiki.org",
}
ALLOWED_SUFFIXES = {
    "fandom.com",
    "wiki.gg",
    "miraheze.org",
    "wikipedia.org",
}

def host_allowed(host: str) -> bool:
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    # exact
    if host in ALLOWED_HOSTS:
        return True
    # suffix families
    return any(host.endswith(suf) for suf in ALLOWED_SUFFIXES)

def classify_family(host: str) -> str:
    if host.endswith(".fandom.com"): return "fandom"
    if host.endswith(".wiki.gg"): return "wiki.gg"
    if host.endswith(".miraheze.org"): return "miraheze"
    if host.endswith(".wikipedia.org"): return "wikimedia"
    if host == "bulbapedia.bulbagarden.net": return "bulbapedia"
    if host == "liquipedia.net": return "liquipedia"
    if host == "nookipedia.com": return "nookipedia"
    if host == "en.pornopedia.com": return "pornopedia"
    if host == "pidgi.net": return "pidgi"
    if host == "tolkiengateway.net": return "tolkiengateway"
    if host == "bg3.wiki": return "bg3"
    if host == "fallout.wiki": return "fallout"
    if host == "ffxiclopedia.fandom.com": return "fandom"
    if host == "kidicaruswiki.org": return "kidicarus"
    return "other"

def _norm_host(host: str) -> str:
    host = host.lower()
    return host[4:] if host.startswith("www.") else host

def _first_path_segment(path: str) -> str | None:
    segs = (path or "/").lstrip("/").split("/", 1)
    return segs[0] if segs and segs[0] else None

@lru_cache(maxsize=256)
def discover_api_base(page_url: str) -> tuple[str | None, str | None]:
    """
    Given an article URL on one of your whitelisted domains, return (api_base, family)
    after verifying via action=query&meta=siteinfo. Otherwise (None, None).
    """
    if not page_url:
        return None, None

    parts = urlsplit(page_url)
    scheme = parts.scheme or "https"
    host = _norm_host(parts.netloc)

    if not host_allowed(host):
        return None, None

    headers = {"User-Agent": "Stash-MediaWiki-Scraper/1.0 (+local use)"}
    params  = {"action": "query", "meta": "siteinfo", "format": "json"}

    candidates: list[str] = []

    # Special-case fandom.com/wiki/<wiki>/... -> <wiki>.fandom.com
    if host in ("fandom.com", "www.fandom.com"):
        seg0 = _first_path_segment(parts.path)
        seg1 = None
        if seg0 and seg0.lower() == 'wiki':
            segs = (parts.path or '/').lstrip('/').split('/')
            if len(segs) >= 2:
                seg1 = re.sub(r'[^A-Za-z0-9\-]+', '', segs[1])
        if seg1:
            api_domain = f"{seg1}.fandom.com"
            candidates.append(f"{scheme}://{api_domain}/api.php")
        # also include generic fandom.com candidates as fallback
        candidates.append(f"{scheme}://{host}/api.php")

    # Special-case wiki.gg/wiki/<wiki>/... -> <wiki>.wiki.gg
    if host in ("wiki.gg", "www.wiki.gg"):
        seg0 = _first_path_segment(parts.path)
        seg1 = None
        if seg0 and seg0.lower() == 'wiki':
            segs = (parts.path or '/').lstrip('/').split('/')
            if len(segs) >= 2:
                seg1 = re.sub(r'[^A-Za-z0-9\-]+', '', segs[1])
        if seg1:
            api_domain = f"{seg1}.wiki.gg"
            candidates.append(f"{scheme}://{api_domain}/api.php")
        candidates.append(f"{scheme}://{host}/api.php")

    # Liquipedia: liquipedia.net/<project>/... → api at /<project>/api.php (try it first)
    if host == "liquipedia.net":
        seg0 = _first_path_segment(parts.path)
        if seg0:  # e.g., dota2, valorant, etc.
            candidates.append(f"{scheme}://{host}/{seg0}/api.php")

    # Wikimedia/Bulbapedia often under /w/api.php
    if host.endswith(".wikipedia.org") or host == "bulbapedia.bulbagarden.net":
        candidates.extend([
            f"{scheme}://{host}/w/api.php",
            f"{scheme}://{host}/api.php",
        ])
    else:
        # Generic MediaWiki candidates
        candidates.extend([
            f"{scheme}://{host}/api.php",
            f"{scheme}://{host}/w/api.php",
        ])

    # Try them in order; accept the first that returns siteinfo JSON
    for api in candidates:
        try:
            r = requests.get(api, params=params, headers=headers, timeout=10, allow_redirects=True)
            if r.ok and "application/json" in r.headers.get("content-type", ""):
                j = r.json()
                if "query" in j and "general" in j["query"]:
                    return api, classify_family(host)
        except requests.RequestException:
            continue

    return None, None
