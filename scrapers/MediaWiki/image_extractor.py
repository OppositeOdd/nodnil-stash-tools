"""Image Extractor Module"""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from py_common.util import dig

FILE_PATTERNS = [
    re.compile(r'\[\[(?:File|Image):([^|\]]+)(?:\|[^\]]*)?\]\]', re.IGNORECASE),
    re.compile(r'\[\[(?:file|image):([^|\]]+)(?:\|[^\]]*)?\]\]', re.IGNORECASE),
]

URL_PATTERNS = [
    re.compile(r'https?://[^\s\]]+\.(?:jpg|jpeg|png|gif|webp)', re.IGNORECASE),
]

PREFIX_REMOVAL_PATTERN = re.compile(r'^(?:File|Image):', re.IGNORECASE)
SKIP_PATTERNS = frozenset({'thumb', 'icon', 'logo', 'banner', 'button', 'wiki', 'disambiguation', 'stub'})
PRIORITY_PATTERNS = frozenset({'full', 'original', 'large', 'hires', 'hq', 'portrait', 'character'})
LOW_QUALITY_PATTERNS = frozenset({'small', 'tiny', '50px', '100px', 'mini'})
WIKIPEDIA_DOMAINS = ('wikipedia.org', 'wikimedia.org')
COMMONS_IMAGE_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/{}"


def extract_images_from_page_data(page_data: Dict) -> List[str]:
    images: List[str] = []
    if not page_data:
        return images
    main_image_name = dig(page_data, 'image')
    if main_image_name and isinstance(main_image_name, str):
        api_base = dig(page_data, 'api_base', default='')
        main_image = resolve_image_url(main_image_name, str(api_base or ''))
        if main_image:
            images.append(main_image)
    images_list = dig(page_data, 'images')
    if isinstance(images_list, list):
        for image_info in images_list:
            if isinstance(image_info, dict) and 'url' in image_info:
                images.append(image_info['url'])
            elif isinstance(image_info, str):
                resolved_url = resolve_image_url(image_info, page_data.get('api_base', ''))
                if resolved_url:
                    images.append(resolved_url)
    if 'html_content' in page_data:
        html_images = extract_images_from_html(page_data['html_content'])
        images.extend(html_images)
    if 'wikitext' in page_data:
        wikitext_images = extract_images_from_wikitext(page_data['wikitext'], page_data.get('api_base', ''))
        images.extend(wikitext_images)
    unique_images = []
    seen = set()
    for img in images:
        if img not in seen:
            unique_images.append(img)
            seen.add(img)
    return unique_images


def extract_images_from_wikitext(wikitext: str, api_base: str = '') -> List[str]:
    if not wikitext:
        return []
    images = []
    for pattern in FILE_PATTERNS:
        matches = pattern.findall(wikitext)
        for match in matches:
            filename = match.strip()
            if filename:
                resolved_url = resolve_image_url(filename, api_base)
                if resolved_url:
                    images.append(resolved_url)
    for pattern in URL_PATTERNS:
        matches = pattern.findall(wikitext)
        images.extend(matches)
    return images


def extract_images_from_html(html_content: str) -> List[str]:
    if not html_content:
        return []
    images = []
    img_patterns = [
        re.compile(r'<a[^>]*href="([^"']*\.(?:png|jpg|jpeg|gif|webp)[^"']*)"[^>]*class="[^"']*image[^"']*"', re.IGNORECASE),
        re.compile(r'<img[^>]*src="([^"']*\.(?:png|jpg|jpeg|gif|webp)[^"']*)"', re.IGNORECASE),
        re.compile(r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"', re.IGNORECASE),
    ]
    for pattern in img_patterns:
        matches = pattern.findall(html_content)
        for match in matches:
            if match and match.startswith(('http://', 'https://', '//')):
                image_url = match if match.startswith('http') else f'https:{match}'
                images.append(image_url)
    return images


def resolve_image_url(filename: str, api_base: str = '') -> Optional[str]:
    if not filename:
        return None
    if filename.startswith('http'):
        return filename
    filename = filename.strip()
    filename = PREFIX_REMOVAL_PATTERN.sub('', filename)
    if not api_base:
        return None
    return _resolve_image_url_by_domain(filename, api_base)


def _resolve_image_url_by_domain(filename: str, api_base: str) -> Optional[str]:
    if not filename or not api_base:
        return None
    parsed = urlparse(api_base)
    domain = parsed.netloc
    encoded_filename = filename.replace(' ', '_')
    if any(wiki_domain in domain for wiki_domain in WIKIPEDIA_DOMAINS):
        return COMMONS_IMAGE_URL.format(encoded_filename)
    base_url = f"{parsed.scheme}://{domain}"
    return f"{base_url}/wiki/Special:FilePath/{encoded_filename}"


def filter_images_by_quality(images: List[str]) -> List[str]:
    if not images:
        return []
    prioritized = []
    standard = []
    low_quality = []
    for image_url in images:
        url_lower = image_url.lower()
        if any(pattern in url_lower for pattern in SKIP_PATTERNS):
            continue
        if any(pattern in url_lower for pattern in PRIORITY_PATTERNS):
            prioritized.append(image_url)
        elif any(pattern in url_lower for pattern in LOW_QUALITY_PATTERNS):
            low_quality.append(image_url)
        else:
            standard.append(image_url)
    return prioritized + standard + low_quality


def extract_primary_image(page_data: Dict) -> Optional[str]:
    images = extract_images_from_page_data(page_data)
    if not images:
        return None
    performer_name = None
    if 'extracted_data' in page_data:
        performer_name = dig(page_data, 'extracted_data', 'name')
    if not performer_name and 'infobox_data' in page_data:
        infobox = page_data['infobox_data']
        performer_name = (dig(infobox, 'name') or dig(infobox, 'full_name') or dig(infobox, 'character_name') or dig(infobox, 'title'))
    if not performer_name:
        page_title = dig(page_data, 'title', default='')
        if page_title:
            performer_name = page_title.split('|')[0].strip()
            for suffix in [' - ', ' (', ' |']:
                if suffix in performer_name:
                    performer_name = performer_name.split(suffix)[0].strip()
                    break
    if performer_name:
        name_lower = performer_name.lower()
        name_based_images = []
        other_images = []
        for img_url in images:
            img_lower = img_url.lower()
            if name_lower in img_lower or f"img-{name_lower}" in img_lower:
                name_based_images.append(img_url)
            else:
                other_images.append(img_url)
        if name_based_images:
            quality_images = filter_images_by_quality(name_based_images)
            if quality_images:
                return quality_images[0]
            return name_based_images[0]
    quality_images = filter_images_by_quality(images)
    if quality_images:
        return quality_images[0]
    return images[0] if images else None
