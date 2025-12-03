"""Data Converter - Measurements, Height/Weight, and Field Normalization"""

import re
from typing import Dict, Optional, Tuple

from py_common.util import guess_nationality

JP_MEASUREMENTS_PATTERN = re.compile(r'([A-Za-z]+?)(\d+)-(\d+)-(\d+)')
BWH_MEASUREMENTS_PATTERN = re.compile(r'B(\d+)\s*W(\d+)\s*H(\d+)', re.IGNORECASE)
CM_REMOVAL_PATTERN = re.compile(r'\s*cm\s*')

HEIGHT_PATTERNS = [
    re.compile(r'(\d+(?:\.\d+)?)\s*(?:cm|centimeters?)', re.IGNORECASE),
    re.compile(r'height:?(\d+(?:\.\d+)?)\s*(?:cm|centimeters?)', re.IGNORECASE),
    re.compile(r"(\d+)\'\s*(\d+(?:\.\d+)?)\"?", re.IGNORECASE),
]

WEIGHT_PATTERNS = [
    re.compile(r'(\d+(?:\.\d+)?)\s*(?:kg|kilograms?)', re.IGNORECASE),
    re.compile(r'(\d+(?:\.\d+)?)\s*(?:lbs?|pounds?)', re.IGNORECASE),
]


def convert_jp_to_us_measurements(measurements: str) -> str:
    if not measurements:
        return measurements
    cleaned = CM_REMOVAL_PATTERN.sub('', measurements).strip()
    match = JP_MEASUREMENTS_PATTERN.match(cleaned)
    if match:
        try:
            return measurements
        except Exception:
            pass
    bwh_match = BWH_MEASUREMENTS_PATTERN.match(cleaned)
    if bwh_match:
        try:
            return measurements
        except Exception:
            pass
    return measurements


CM_TO_INCH = 2.54

JP_TO_US_CUP_MAP = {}


def _convert_jp_cup_to_us(jp_cup: str, bust_cm: int) -> Optional[str]:
    if not jp_cup or not bust_cm:
        return None
    return JP_TO_US_CUP_MAP.get(jp_cup.upper())


def _estimate_cup_from_bwh(bust_cm: int, waist_cm: int) -> str:
    underbust_cm = waist_cm + 20
    cup_difference = bust_cm - underbust_cm
    if cup_difference < 10:
        return 'A'
    elif cup_difference < 13:
        return 'B'
    elif cup_difference < 16:
        return 'C'
    elif cup_difference < 19:
        return 'D'
    elif cup_difference < 22:
        return 'DD'
    elif cup_difference < 25:
        return 'DDD'
    elif cup_difference < 28:
        return 'G'
    elif cup_difference < 31:
        return 'H'
    elif cup_difference < 34:
        return 'I'
    else:
        return 'J'


def _band_size(bust_inches: int) -> int:
    size = max(28, min(46, ((bust_inches + 1) // 2) * 2))
    return size


def _clean_raw_value(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r'\[\d+\]', '', value)
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)
    cleaned = re.sub(r'[^\w\s,&-]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if any(delimiter in cleaned for delimiter in [',', '&', ' and ']):
        parts = re.split(r'[,&]|\s+and\s+', cleaned)
        parts = [part.strip() for part in parts if part.strip()]
        cleaned = ' '.join(parts)
    return cleaned


def _extract_age_from_raw_value(age_str: str) -> Optional[str]:
    if not age_str:
        return None
    cleaned = _clean_raw_value(age_str)
    age_patterns = [r'(\d+)\+', r'(\d+)\s*-\s*\d+', r'(\d+)', r'(?:circa|about|around)\s*(\d+)']
    for pattern in age_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            age_num = int(match.group(1))
            if 1 <= age_num <= 10000:
                return str(age_num)
    return None


def _normalize_value(value: str) -> str:
    cleaned = _clean_raw_value(value)
    return cleaned.lower().strip()


def _extract_primary_nationality(country_str: str) -> str:
    if not country_str:
        return country_str
    cleaned = country_str.strip()
    import re
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    separators = ['/', ',', ';', '&', ' and ', ' or ']
    for sep in separators:
        if sep in cleaned:
            cleaned = cleaned.split(sep)[0]
            break
    cleaned = cleaned.strip().strip('"\'')
    return cleaned if cleaned else country_str


def normalize_field_values(data: Dict[str, str], config=None) -> Dict[str, str]:
    normalized = {}
    age_value = data.get('age')
    for key, value in data.items():
        if not value:
            continue
        if key == 'measurements' and value:
            normalized[key] = convert_jp_to_us_measurements(value)
            continue
        if key == 'birthdate' and value:
            if not age_value:
                from data_converter import approximate_birthdate
                approximated_date = approximate_birthdate(value, config)
                if approximated_date:
                    normalized[key] = approximated_date
            continue
        if key == 'age' and value:
            cleaned_age = _extract_age_from_raw_value(value)
            if cleaned_age:
                from data_converter import approximate_birthdate
                age_date = approximate_birthdate(f"age: {cleaned_age}", config)
                if age_date:
                    normalized['birthdate'] = age_date
            continue
        if key == 'height' and value:
            parsed_height = parse_height(value)
            if parsed_height:
                normalized[key] = parsed_height
            continue
        if key == 'weight' and value:
            parsed_weight = parse_weight(value)
            if parsed_weight:
                normalized[key] = parsed_weight
            continue
        if key == 'ethnicity':
            cleaned_value = _clean_raw_value(value)
            value_lower = cleaned_value.lower().strip()
            normalized[key] = cleaned_value.title() if cleaned_value else 'Other'
            continue
        normalized[key] = value
    return normalized


def extract_height_weight_from_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    height = None
    weight = None
    if not text:
        return height, weight
    for pattern in HEIGHT_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                if len(match.groups()) >= 2 and match.group(2) is not None:
                    feet = float(match.group(1))
                    inches = float(match.group(2) or 0)
                    total_inches = feet * 12 + inches
                    height_cm = round((total_inches) * 2.54)
                    height = f"{height_cm} cm"
                else:
                    height_val = float(match.group(1))
                    if height_val > 50:
                        height = f"{int(height_val)} cm"
            except (ValueError, IndexError):
                continue
            break
    for pattern in WEIGHT_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                weight_val = float(match.group(1))
                if 'lbs?' in pattern.pattern or 'pounds?' in pattern.pattern:
                    weight_kg = round(weight_val * 0.453592, 1)
                    weight = f"{weight_kg} kg"
                else:
                    weight = f"{weight_val} kg"
            except (ValueError, IndexError):
                continue
            break
    return height, weight


def parse_height(height_str: str) -> Optional[str]:
    if not height_str:
        return None
    cleaned = height_str.strip()
    for pattern in HEIGHT_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            try:
                if len(match.groups()) >= 2 and match.group(2) is not None:
                    feet = float(match.group(1))
                    inches = float(match.group(2) or 0)
                    total_inches = feet * 12 + inches
                    height_cm = total_inches * 2.54
                else:
                    height_cm = float(match.group(1))
                if 100 <= height_cm <= 250:
                    formatted = round(height_cm, 1)
                    if formatted == int(formatted):
                        return str(int(formatted))
                    else:
                        return f"{formatted:.1f}"
            except (ValueError, IndexError):
                continue
    return None


def parse_weight(weight_str: str) -> Optional[str]:
    if not weight_str:
        return None
    cleaned = weight_str.strip()
    for pattern in WEIGHT_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            try:
                weight_val = float(match.group(1))
                if 'lbs?' in pattern.pattern or 'pounds?' in pattern.pattern:
                    weight_kg = weight_val * 0.453592
                else:
                    weight_kg = weight_val
                if 20 <= weight_kg <= 200:
                    formatted = round(weight_kg, 1)
                    if formatted == int(formatted):
                        return str(int(formatted))
                    else:
                        return f"{formatted:.1f}"
            except (ValueError, IndexError):
                continue
    return None


def approximate_birthdate(birthdate_str: str, config=None) -> Optional[str]:
    import re
    from datetime import datetime
    if config and not getattr(config, 'approximate_birthdate', True):
        return None
    if not birthdate_str:
        return None
    cleaned = re.sub(r'[^\w\s\-/.,]', '', birthdate_str.strip())
    current_year = datetime.now().year
    full_date_patterns = [r'(\d{4})-(\d{1,2})-(\d{1,2})', r'(\d{1,2})/(\d{1,2})/(\d{4})', r'(\w+)\s+(\d{1,2}),?\s+(\d{4})']
    for pattern in full_date_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 3:
                    if re.match(r'\d{4}', groups[0]):
                        year, month, day = groups
                    elif re.match(r'\d{4}', groups[2]):
                        if groups[0].isalpha():
                            month_name, day, year = groups
                            month = _month_name_to_number(month_name)
                        else:
                            month, day, year = groups
                    else:
                        continue
                    year = int(year)
                    day = int(day)
                    if isinstance(month, str) and month.isdigit():
                        month = int(month)
                    if month is None or not isinstance(month, int):
                        continue
                    if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= current_year + 10:
                        return f"{year:04d}-{month:02d}-{day:02d}"
            except (ValueError, TypeError):
                continue
    age_patterns = [r'(?:age|aged?)\s*:?(\d{1,5})', r'(\d{1,5})\s*(?:years?\s*old|yo)', r'born\s*(?:in)?\s*(\d{4})']
    for pattern in age_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            try:
                if 'born' in pattern:
                    birth_year = int(match.group(1))
                else:
                    age = int(match.group(1))
                    if age > 10000:
                        continue
                    birth_year = current_year - age
                if birth_year >= (current_year - 10000) and birth_year <= current_year:
                    return f"{birth_year:04d}-01-01"
            except (ValueError, TypeError):
                continue
    month_day_patterns = [r'(\w+)\s+(\d{1,2})', r'(\d{1,2})/(\d{1,2})(?!/)', r'(\d{1,2})-(\d{1,2})(?!-)']
    for pattern in month_day_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            try:
                groups = match.groups()
                if groups[0].isalpha():
                    month_name, day = groups
                    month = _month_name_to_number(month_name)
                    day = int(day)
                else:
                    month, day = map(int, groups)
                if month is None:
                    continue
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return f"2005-{month:02d}-{day:02d}"
            except (ValueError, TypeError):
                continue
    circa_match = re.search(r'c\.?\s*(\d{4})', cleaned, re.IGNORECASE)
    if circa_match:
        try:
            year = int(circa_match.group(1))
            if 1900 <= year <= current_year + 10:
                return f"{year:04d}-01-01"
        except (ValueError, TypeError):
            pass
    return None


def _month_name_to_number(month_name: str) -> Optional[int]:
    if not month_name:
        return None
    month_map = {'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3, 'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9, 'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12}
    return month_map.get(month_name.lower())
