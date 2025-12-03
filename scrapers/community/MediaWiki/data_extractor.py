"""Data Extractor - Field Mapping and Data Processing"""

import re
from typing import Dict, List, Optional, Any

from content_parser import parse_infobox_from_wikitext, clean_wiki_markup, parse_portable_infobox_html
from py_common.util import dig, guess_nationality
from data_converter import normalize_field_values


def _split_compound_alias(alias_text):
    if not alias_text:
        return []
    alias_text = alias_text.strip()
    if not alias_text:
        return []
    for separator in [' / ', ' | ', ' or ', ' aka ', ' also known as ']:
        if separator in alias_text:
            parts = alias_text.split(separator)
            result = []
            for part in parts:
                result.extend(_split_compound_alias(part.strip()))
            return result
    camel_pattern = re.compile(r'([a-z])([A-Z])')
    if camel_pattern.search(alias_text):
        spaced_text = camel_pattern.sub(r'\1 \2', alias_text)
        words = spaced_text.split()
        common_words = {'my', 'is', 'the', 'of', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from'}
        if len(words) >= 3 and any(word.lower() in common_words for word in words):
            return [spaced_text]
    return [alias_text]


def _get_field_mappings(config=None):
    mappings = {
        'name': ['full name', 'full_name', 'name', 'title', 'character_name'],
        'gender': ['gender', 'sex', 'identity'],
        'birthdate': ['birthdate', 'birth_date', 'date of birth', 'born', 'birthday'],
        'age': ['age', 'current_age', 'current age'],
        'measurements': ['measurements', 'body_measurements', 'stats'],
        'height': ['height', 'stature'],
        'weight': ['weight', 'weight kg', 'weight_kg'],
        'hair_color': ['hair_color', 'hair'],
        'eye_color': ['eye_color', 'eyes'],
        'ethnicity': ['ethnicity', 'species', 'race_species', 'creature_type'],
        'country': ['nationality', 'nation', 'country', 'origin'],
        'aliases': ['aliases', 'alias', 'also_known_as', 'aka'],
        'career_start': ['career_start', 'debut', 'first_appearance'],
        'career_end': ['career_end', 'retired', 'last_appearance'],
        'piercings': ['piercings', 'piercing'],
        'tattoos': ['tattoos', 'tattoo'],
        'cup_size': ['cup_size', 'cup', 'bra_size'],
        'fake_boobs': ['fake_boobs', 'breast_implants', 'implants']
    }
    if config:
        if getattr(config, 'map_race_to_ethnicity', False):
            mappings['ethnicity'].extend(['race', 'species_type', 'character_race'])
        if getattr(config, 'map_universe_to_disambiguation', False):
            mappings['disambiguation'] = ['universe', 'continuity']
    return mappings


def extract_performer_data(page_data: Dict, config=None) -> Dict[str, Any]:
    if not page_data or 'infobox_data' not in page_data:
        raise ValueError("No infobox data found in page_data")
    infobox_data = page_data['infobox_data']
    if not infobox_data:
        raise ValueError("Infobox data is empty")
    mapped_data = _map_infobox_fields(infobox_data, config)
    if 'name' not in mapped_data or not mapped_data['name']:
        page_title = dig(page_data, 'title', default='')
        if page_title:
            clean_title = page_title.split('/')[-1].split('(')[0].strip()
            if clean_title:
                mapped_data['name'] = clean_title
    return mapped_data


def _map_infobox_fields(infobox_data: Dict[str, str], config=None) -> Dict[str, Any]:
    mapped_data = {}
    field_mappings = _get_field_mappings(config)
    lowercase_infobox = {k.lower(): v for k, v in infobox_data.items() if v and v.strip()}
    for standard_field, possible_names in field_mappings.items():
        if standard_field == 'aliases':
            alias_values = []
            for field_name in possible_names:
                value = lowercase_infobox.get(field_name.lower())
                if value:
                    cleaned_value = clean_wiki_markup(value.strip())
                    if cleaned_value:
                        split_aliases = _split_compound_alias(cleaned_value)
                        alias_values.extend(split_aliases)
            performer_name = None
            for name_field in ['full name', 'full_name', 'name', 'title', 'character_name']:
                if name_field in lowercase_infobox:
                    performer_name = clean_wiki_markup(lowercase_infobox[name_field].strip())
                    break
            real_name = lowercase_infobox.get('real_name')
            if real_name:
                real_name_clean = clean_wiki_markup(real_name.strip())
                if real_name_clean and real_name_clean != performer_name:
                    alias_values.append(real_name_clean)
            if alias_values:
                unique_aliases = []
                seen = set()
                for alias in alias_values:
                    alias_clean = alias.strip()
                    if (alias_clean not in seen and alias_clean != performer_name and len(alias_clean) > 1):
                        unique_aliases.append(alias_clean)
                        seen.add(alias_clean)
                if unique_aliases:
                    mapped_data[standard_field] = ', '.join(unique_aliases)
        elif standard_field == 'country':
            for field_name in possible_names:
                value = lowercase_infobox.get(field_name.lower())
                if value:
                    cleaned_value = clean_wiki_markup(value.strip())
                    country_name = guess_nationality(cleaned_value)
                    mapped_data[standard_field] = country_name
                    break
        else:
            for field_name in possible_names:
                value = lowercase_infobox.get(field_name.lower())
                if value:
                    mapped_data[standard_field] = clean_wiki_markup(value.strip())
                    break
    return mapped_data


def _get_page_text_content(page_data: Dict) -> str:
    text_parts = [
        dig(page_data, 'extract', default=''),
        dig(page_data, 'wikitext', default='')[:2000]
    ]
    return '\n'.join(filter(None, text_parts))


def extract_categories(page_data: Dict) -> List[str]:
    categories_list = dig(page_data, "categories", default=[])
    if not isinstance(categories_list, list):
        return []
    categories = []
    for cat in categories_list:
        category_name = dig(cat, "title", default=cat if isinstance(cat, str) else "")
        if category_name:
            clean_name = category_name.replace('Category:', '').strip()
            if clean_name:
                categories.append(clean_name)
    return categories


RELEVANT_KEYWORDS = frozenset({'character', 'protagonist', 'antagonist', 'main character', 'supporting character'})
INVALID_VALUES = frozenset({'unknown', 'n/a', 'none', ''})


def extract_tags_from_content(page_data: Dict) -> List[str]:
    categories = extract_categories(page_data)
    tags = []
    for category in categories:
        category_lower = category.lower()
        if any(keyword in category_lower for keyword in RELEVANT_KEYWORDS):
            tag = category.replace('_', ' ').title()
            if tag not in tags:
                tags.append(tag)
    return tags


def validate_performer_data(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {}
    validated = {}
    name = dig(data, 'name')
    if name:
        validated['name'] = str(name).strip()
    optional_fields = ('gender', 'birthdate', 'age', 'measurements', 'height', 'weight', 'hair_color')
    for field in optional_fields:
        value = dig(data, field)
        if value:
            clean_value = str(value).strip()
            if clean_value and clean_value.lower() not in INVALID_VALUES:
                validated[field] = clean_value
    list_fields = ['categories', 'tags', 'images']
    for field in list_fields:
        value = dig(data, field)
        if value and isinstance(value, list) and len(value) > 0:
            validated[field] = value
    special_fields = ['disambiguation', 'description', 'source_url', 'page_title']
    for field in special_fields:
        value = dig(data, field)
        if value:
            validated[field] = value
    return validated


def _extract_franchise_from_page(page_data: Dict) -> Optional[str]:
    from urllib.parse import urlparse
    categories = [cat.get('title', '').replace('Category:', '') for cat in page_data.get('categories', [])]
    franchise_patterns = [r'(Resident Evil)[:\s]', r'(Dead or Alive)\s+\d']
    matches = []
    for pattern_idx, pattern in enumerate(franchise_patterns):
        for category in categories:
            match = re.search(pattern, category, re.IGNORECASE)
            if match:
                franchise = match.group(1).strip()
                franchise = re.sub(r'\s+', ' ', franchise)
                matches.append((pattern_idx, franchise, category))
    if matches:
        matches.sort(key=lambda x: x[0])
        return matches[0][1]
    description = dig(page_data, 'pageprops', 'fandomdescription', default='')
    if description:
        description_patterns = [r'(Resident Evil)[:\s]+[A-Z]', r'(Dead or Alive)\s+\d']
        for pattern in description_patterns:
            match = re.search(pattern, description)
            if match:
                franchise = match.group(1).strip()
                return franchise
    source_url = dig(page_data, 'url')
    if source_url and '.fandom.com' in source_url:
        parsed = urlparse(source_url)
        domain_parts = parsed.netloc.split('.')
        if len(domain_parts) >= 3:
            franchise = domain_parts[0]
            url_mappings = {'residentevil': 'Resident Evil'}
            if franchise in url_mappings:
                return url_mappings[franchise]
            franchise = franchise.replace('-', ' ').replace('_', ' ')
            franchise = ' '.join(word.capitalize() for word in franchise.split())
            return franchise
    return None


def extract_all_fields(page_data: Dict, config=None) -> Dict[str, Any]:
    if 'infobox_data' not in page_data:
        wikitext = dig(page_data, 'revisions', 0, 'slots', 'main', '*', default='')
        infobox_data = parse_infobox_from_wikitext(wikitext) or {}
        html_content = page_data.get('html_content', '')
        if html_content:
            html_infobox_data = parse_portable_infobox_html(html_content)
            if html_infobox_data:
                infobox_data.update(html_infobox_data)
        page_data = page_data.copy()
        page_data['infobox_data'] = infobox_data
    performer_data = extract_performer_data(page_data, config)
    result = dict(performer_data)
    fandom_description = dig(page_data, 'pageprops', 'fandomdescription')
    if fandom_description and not result.get('description'):
        description = clean_wiki_markup(fandom_description)
        max_length = getattr(config, 'max_description_length', 2200) if config else 2200
        if len(description) > max_length:
            description = description[:max_length].rsplit(' ', 1)[0] + '...'
        result['description'] = description
    if config and getattr(config, 'map_universe_to_disambiguation', False):
        if not result.get('disambiguation'):
            franchise = _extract_franchise_from_page(page_data)
            if franchise:
                result['disambiguation'] = franchise
    if config and getattr(config, 'extract_categories', False):
        result['categories'] = extract_categories(page_data)
    result['tags'] = extract_tags_from_content(page_data)
    if config and getattr(config, 'add_universe_to_tags', True):
        universe = _extract_franchise_from_page(page_data)
        if universe and universe not in result['tags']:
            result['tags'].append(universe)
    source_url = dig(page_data, 'url')
    if source_url:
        result['source_url'] = source_url
    page_title = dig(page_data, 'title')
    if page_title:
        result['page_title'] = page_title
    normalized_result = normalize_field_values(result, config)
    validated_result = validate_performer_data(normalized_result)
    for field in ['categories', 'tags', 'source_url', 'page_title', 'description', 'disambiguation']:
        if field in normalized_result:
            validated_result[field] = normalized_result[field]
    return validated_result
