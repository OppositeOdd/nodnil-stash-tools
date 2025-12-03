"""MediaWiki Scraper - Main Entry Point
"""

import json
import os
import re
import sys
from typing import Dict, Any, Optional
from urllib.parse import unquote, urlparse

import py_common.log as log
from py_common.deps import ensure_requirements
from py_common.util import scraper_args, is_valid_url

ensure_requirements("requests")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_discovery import discover_api_base, extract_page_content, host_allowed
from performer_processor import process_performer_data, format_performer_for_output, validate_required_fields

URL_PATTERNS = (
    re.compile(r'/wiki/(.+)$'),
    re.compile(r'/w/index\.php\?title=(.+)'),
    re.compile(r'/index\.php/(.+)$'),
    re.compile(r'/(.+)$')
)


class ConfigObject:
    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


def _get_scraper_config():
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

    defaults = {
        'map_race_to_ethnicity': False,
        'map_universe_to_disambiguation': False,
        'max_description_length': 2200,
        'extract_categories': False,
        'approximate_birthdate': True,
        'add_universe_to_tags': True
    }

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        config_data = {k: v for k, v in config_data.items() if not k.startswith('_')}
        defaults.update(config_data)
        return ConfigObject(defaults)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        log.debug(f"Config file error, using defaults: {e}")
        return ConfigObject(defaults)


def _extract_page_title_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    for pattern in URL_PATTERNS:
        if match := pattern.search(parsed.path):
            return unquote(match.group(1)).replace('_', ' ')
    return None


def _validate_and_prepare_url(url: str) -> Optional[str]:
    parsed_url = urlparse(url)
    if not host_allowed(parsed_url.netloc):
        log.warning(f"Host not allowed: {parsed_url.netloc}")
        return None
    return unquote(url)


def scrape_performer_by_url(url: str) -> Optional[Dict[str, Any]]:
    try:
        decoded_url = _validate_and_prepare_url(url)
        if not decoded_url:
            return None

        api_base, _ = discover_api_base(decoded_url)
        if not api_base:
            log.error(f"Could not discover API for: {url}")
            return None

        page_title = _extract_page_title_from_url(decoded_url)
        if not page_title:
            log.error(f"Could not extract page title from: {url}")
            return None

        page_data = extract_page_content(api_base, page_title)
        if not page_data:
            log.error(f"Could not extract content from: {url}")
            return None

        page_data['url'] = url
        config = _get_scraper_config()
        performer_data = process_performer_data(page_data, url, config)

        if not validate_required_fields(performer_data):
            log.warning(f"Data validation failed for: {url}")
            return None

        log.info(f"Successfully scraped performer: {performer_data.get('name', 'Unknown')}")
        return performer_data

    except Exception as e:
        log.error(f"Error scraping {url}: {e}")
        return None


def scrape_performer_by_name(name: str, site_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    log.warning("Search by name not supported - use direct page URLs")
    return None


def scrape_performer_url(url: str) -> str:
    result = scrape_performer_by_url(url)
    return format_performer_for_output(result or {})


def scrape_scene_url(url: str) -> str:
    log.warning("Scene scraping not supported")
    return "{}"


def validate_url(url: str) -> bool:
    parsed_url = urlparse(url)
    return host_allowed(parsed_url.netloc) and is_valid_url(url)


def get_supported_hosts() -> list:
    return ['fandom.com', 'wikipedia.org', 'wikimedia.org', 'wiki.gg', 'bg3.wiki']


def main():
    op, args = scraper_args()

    if op == "performer-by-url" and "url" in args:
        result = scrape_performer_by_url(args["url"]) 
    elif op == "performer-by-name" and "name" in args:
        result = scrape_performer_by_name(args["name"]) 
    else:
        log.error(f"Invalid operation: {op}, args: {args}")
        print("{}")
        sys.exit(1)

    output = format_performer_for_output(result) if result else "{}"
    print(output)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
