"""Performer Processor Module

Converts extracted MediaWiki page data into the Stash performer format.
"""

import re
import json
from typing import Dict, List, Optional, Any

import py_common.log as log
from py_common.util import dig

from content_parser import extract_clean_text_from_wikitext, format_description_text
from image_extractor import extract_primary_image, extract_images_from_page_data
from data_extractor import extract_all_fields
from data_converter import approximate_birthdate

YEAR_PATTERN = re.compile(r'\b(19\d{2}|20\d{2})\b')

BOOLEAN_TRUE_VALUES = frozenset({'yes', 'true', '1', 'enhanced'})
BOOLEAN_FALSE_VALUES = frozenset({'no', 'false', '0', 'natural'})
FEMALE_VALUES = frozenset({'female', 'f', 'woman', 'girl'})
MALE_VALUES = frozenset({'male', 'm', 'man', 'boy'})
INVALID_NAME_VALUES = frozenset({'unknown', 'n/a', 'none', ''})


def process_performer_data(page_data: Dict, url: str, config=None) -> Dict[str, Any]:
    if not page_data:
        return {}

    extracted_data = extract_all_fields(page_data, config)
    performer = _build_base_performer_object(extracted_data, url, config)

    description = _generate_description(page_data, extracted_data)
    if description:
        performer['details'] = description

    images = _process_performer_images(page_data)
    if images:
        performer['images'] = images

    tags = extracted_data.get('tags', [])
    if tags:
        performer['tags'] = [{'name': tag} for tag in tags]

    return performer


def _build_base_performer_object(data: Dict[str, Any], url: str, config=None) -> Dict[str, Any]:
    performer = {
        'name': dig(data, 'name', default='Unknown'),
        'url': url
    }

    field_mapping = (
        ('gender', 'gender'), ('birthdate', 'birthdate'), ('measurements', 'measurements'),
        ('height', 'height'), ('weight', 'weight'), ('hair_color', 'hair_color'),
        ('eye_color', 'eye_color'), ('ethnicity', 'ethnicity'), ('country', 'country'),
        ('aliases', 'aliases'), ('career_start', 'career_start_year'), ('career_end', 'career_end_year'),
        ('piercings', 'piercings'), ('tattoos', 'tattoos'), ('fake_boobs', 'fake_tits'),
        ('disambiguation', 'disambiguation'), ('categories', 'categories')
    )

    for data_key, performer_key in field_mapping:
        value = dig(data, data_key)
        if value:
            if data_key == 'fake_boobs':
                value_lower = str(value).lower()
                if value_lower in BOOLEAN_TRUE_VALUES:
                    performer[performer_key] = 'Yes'
                elif value_lower in BOOLEAN_FALSE_VALUES:
                    performer[performer_key] = 'No'
                else:
                    performer[performer_key] = str(value)
            elif data_key in ['career_start', 'career_end']:
                year = _extract_year_from_date(str(value))
                if year:
                    performer[performer_key] = year
            elif data_key == 'birthdate':
                age_info = dig(data, 'age')
                if age_info and str(age_info).isdigit():
                    import re
                    from datetime import datetime
                    month_day_match = re.search(r'(\w+)\s+(\d{1,2})', str(value), re.IGNORECASE)
                    if month_day_match:
                        month_name = month_day_match.group(1)
                        day = int(month_day_match.group(2))
                        month_map = {
                            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
                            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
                            'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'october': 10, 'oct': 10,
                            'november': 11, 'nov': 11, 'december': 12, 'dec': 12
                        }
                        month = month_map.get(month_name.lower())
                        if month and 1 <= day <= 31:
                            current_year = datetime.now().year
                            birth_year = current_year - int(age_info)
                            performer[performer_key] = f"{birth_year:04d}-{month:02d}-{day:02d}"
                        else:
                            formatted_birthdate = approximate_birthdate(str(value), config)
                            performer[performer_key] = formatted_birthdate if formatted_birthdate else str(value)
                    else:
                        formatted_birthdate = approximate_birthdate(f"age {age_info}", config)
                        performer[performer_key] = formatted_birthdate if formatted_birthdate else str(value)
                else:
                    formatted_birthdate = approximate_birthdate(str(value), config)
                    performer[performer_key] = formatted_birthdate if formatted_birthdate else str(value)
            elif data_key == 'gender':
                gender_value = str(value).lower()
                if gender_value in FEMALE_VALUES:
                    performer[performer_key] = 'female'
                elif gender_value in MALE_VALUES:
                    performer[performer_key] = 'male'
                else:
                    performer[performer_key] = str(value)
            else:
                performer[performer_key] = str(value)

    return performer


def _generate_description(page_data: Dict, extracted_data: Dict) -> Optional[str]:
    description_parts = []
    if extracted_data.get('description'):
        description_parts.append(extracted_data['description'])
    elif 'wikitext' in page_data and page_data['wikitext']:
        clean_text = extract_clean_text_from_wikitext(page_data['wikitext'])
        if clean_text:
            formatted_description = format_description_text(clean_text)
            if formatted_description and len(formatted_description) > 50:
                description_parts.append(formatted_description)

    if not description_parts and 'extract' in page_data and page_data['extract']:
        extract_text = page_data['extract'].strip()
        if extract_text and len(extract_text) > 50:
            description_parts.append(extract_text)

    if description_parts and 'url' in page_data:
        page_url = page_data['url']
        if 'fandom.com' in page_url:
            wiki_name = _extract_wiki_name_from_url(page_url)
            if wiki_name:
                description_parts.append(f"\n\nSource: {wiki_name} Wiki")
        else:
            description_parts.append(f"\n\nSource: {page_url}")

    return ''.join(description_parts) if description_parts else None


def _process_performer_images(page_data: Dict) -> List[str]:
    primary_image = extract_primary_image(page_data)
    if primary_image:
        return [primary_image]
    all_images = extract_images_from_page_data(page_data)
    return all_images[:3] if all_images else []


def _extract_year_from_date(date_string: str) -> Optional[str]:
    year_match = YEAR_PATTERN.search(date_string)
    return year_match.group(1) if year_match else None


def _extract_wiki_name_from_url(url: str) -> Optional[str]:
    match = re.search(r'https?://([^.]+)\.fandom\.com', url)
    if match:
        return match.group(1).replace('-', ' ').title()
    return None


def format_performer_for_output(performer_data: Dict[str, Any]) -> str:
    if not performer_data:
        return "{}"
    performer_data.setdefault('name', 'Unknown')
    cleaned_data = {}
    for key, value in performer_data.items():
        if value is not None and value != '' and value != []:
            cleaned_data[key] = value
    try:
        return json.dumps(cleaned_data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as e:
        log.error(f"Error formatting performer data as JSON: {e}")
        return json.dumps({'name': performer_data.get('name', 'Unknown'), 'error': 'Formatting error'})


def validate_required_fields(performer_data: Dict[str, Any]) -> bool:
    if not performer_data.get('name'):
        return False
    name = str(performer_data['name']).strip()
    if not name or name.lower() in INVALID_NAME_VALUES:
        return False
    return True


def merge_performer_data(existing_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    if not existing_data:
        return new_data
    if not new_data:
        return existing_data
    merged = existing_data.copy()
    for key, value in new_data.items():
        if (value is not None and value != '' and value != [] and (key not in merged or not merged[key])):
            merged[key] = value
    return merged
