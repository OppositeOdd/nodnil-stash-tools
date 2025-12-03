"""API Discovery Module
"""

import re
from functools import lru_cache
from urllib.parse import urlsplit
from typing import Tuple, Optional, Dict, Any

import py_common.log as log
from py_common.deps import ensure_requirements
from py_common.util import dig, is_valid_url

ensure_requirements("requests")
import requests

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
    "wiki.leagueoflegends.com",
    "fireemblemwiki.org",
}

ALLOWED_SUFFIXES = {"fandom.com", "wiki.gg", "miraheze.org", "wikipedia.org"}


def _normalize_host(host: str) -> str:
    return host[4:] if host.lower().startswith("www.") else host


def host_allowed(host: str) -> bool:
    normalized_host = _normalize_host(host.lower())
    return (normalized_host in ALLOWED_HOSTS or
            any(normalized_host.endswith(suf) for suf in ALLOWED_SUFFIXES))


def classify_family(host: str) -> str:
    if host.endswith(".fandom.com"):
        return "fandom"
    if host.endswith(".wiki.gg"):
        return "wiki.gg"
    if host.endswith(".miraheze.org"):
        return "miraheze"
    if host.endswith(".wikipedia.org"):
        return "wikimedia"
    return "other"


@lru_cache(maxsize=256)
def discover_api_base(page_url: str) -> Tuple[Optional[str], Optional[str]]:
    if not page_url:
        return None, None

    parts = urlsplit(page_url)
    scheme = parts.scheme or "https"
    host = _normalize_host(parts.netloc)

    if not host_allowed(host):
        return None, None

    headers = {"User-Agent": "Stash-MediaWiki-Scraper/2.0 (+local use)"}
    params = {"action": "query", "meta": "siteinfo", "format": "json"}

    candidates = []

    # Fallback candidate generation
    candidates.append(f"{scheme}://{host}/api.php")
    candidates.append(f"{scheme}://{host}/w/api.php")

    for api in candidates:
        if not is_valid_url(api):
            continue
        try:
            r = requests.get(api, params=params, headers=headers, timeout=10, allow_redirects=True)
            if r.ok and "application/json" in r.headers.get("content-type", ""):
                j = r.json()
                if dig(j, "query", "general"):
                    return api, classify_family(host)
        except requests.RequestException:
            continue

    return None, None


def extract_page_content(api_base: str, page_title: str) -> Optional[Dict[str, Any]]:
    if not api_base or not page_title:
        return None

    if not is_valid_url(api_base):
        log.warning(f"API endpoint not accessible: {api_base}")
        return None

    headers = {"User-Agent": "Stash-MediaWiki-Scraper/2.0 (+local use)"}
    params = {
        "action": "query", "titles": page_title, "format": "json", "redirects": "1",
        "prop": "info|revisions|pageimages|extracts|categories|pageprops",
        "rvprop": "content", "rvslots": "main", "piprop": "original|thumbnail",
        "exintro": "1", "explaintext": "0"
    }

    try:
        response = requests.get(api_base, params=params, headers=headers, timeout=15)
        if not response.ok:
            return None

        data = response.json()
        pages = dig(data, "query", "pages", default={})
        if not pages:
            return None

        page_id = next(iter(pages))
        if page_id == "-1":
            return None

        page_data = pages[page_id]

        try:
            html_params = {"action": "parse", "page": page_title, "format": "json", "prop": "text", "section": "0", "disabletoc": "1"}
            html_response = requests.get(api_base, params=html_params, headers=headers, timeout=10)
            if html_response.ok:
                html_data = html_response.json()
                parsed_html = dig(html_data, "parse", "text", "*")
                if parsed_html:
                    page_data["html_content"] = parsed_html
        except requests.RequestException:
            pass

        return page_data

    except requests.RequestException as e:
        log.warning(f"Request failed for {api_base}: {e}")
        return None
