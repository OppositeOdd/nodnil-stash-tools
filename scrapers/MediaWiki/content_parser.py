"""Content Parser - Wikitext and HTML Processing """

import re
from typing import Dict

INFOBOX_PATTERNS = [
    re.compile(r'\{\{(?:character\s+infobox|infobox\s+character|character)[^}]*?\|(.*?)\}\}',
               re.IGNORECASE | re.DOTALL),
    re.compile(r'\{\{(?:hero\s+infobox|infobox\s+hero|hero)[^}]*?\|(.*?)\}\}', re.IGNORECASE | re.DOTALL),
    re.compile(r'\{\{(?:infoboxtable|infobox\s+table)[^}]*?\|(.*?)\}\}',
               re.IGNORECASE | re.DOTALL),
    re.compile(r'\{\{(?:infobox|person|actor|actress|performer)[^}]*?\|(.*?)\}\}',
               re.IGNORECASE | re.DOTALL),
    re.compile(r'\{\{[^}]*(?:box|info)[^}]*?\|(.*?)\}\}', re.IGNORECASE | re.DOTALL),
]

CLEANUP_PATTERNS = [
    (re.compile(r'<gallery[^>]*>.*?</gallery>', re.DOTALL | re.MULTILINE), ''),
    (re.compile(r'<ref[^>]*>.*?</ref>', re.DOTALL | re.MULTILINE), ''),
    (re.compile(r'<ref[^>]*/?>', re.DOTALL | re.MULTILINE), ''),
    (re.compile(r'\{\{[Rr]ef[^}]*\}\}', re.DOTALL | re.MULTILINE), ''),
    (re.compile(r'\[\[([^|\]]+)\|([^\]]+)\]\]', re.DOTALL | re.MULTILINE), r'\2'),
    (re.compile(r'\[\[([^\]]+)\]\]', re.DOTALL | re.MULTILINE), r'\1'),
    (re.compile(r'\{\{[^}]*\}\}', re.DOTALL | re.MULTILINE), ''),
    (re.compile(r'<[^>]+>', re.DOTALL | re.MULTILINE), ''),
    (re.compile(r"'{2,}", re.DOTALL | re.MULTILINE), ''),
    (re.compile(r'\{\{[^}]*$', re.DOTALL | re.MULTILINE), ''),
    (re.compile(r'^[^{]*\}\}', re.DOTALL | re.MULTILINE), ''),
    (re.compile(r'\s+', re.DOTALL | re.MULTILINE), ' ')
]

DESCRIPTION_PATTERNS = [
    (re.compile(r'\|[^=\n]*=\s*[^|\n]*', re.MULTILINE), ''),
    (re.compile(r'^=+.*?=+$', re.MULTILINE), ''),
    (re.compile(r'\|+', re.MULTILINE), ''),
    (re.compile(r'\}+', re.MULTILINE), ''),
    (re.compile(r'\{+', re.MULTILINE), ''),
    (re.compile(r'^\s*\)\s*$', re.MULTILINE), ''),
]

PARAGRAPH_FILTER_PATTERNS = [
    re.compile(r'^[|=\[\]{}]+'),
    re.compile(r'^[A-Z][a-z]*\d+\s*=')
]


def parse_infobox_from_wikitext(wikitext: str) -> Dict[str, str]:
    if not wikitext:
        return {}
    infobox_data = {}
    for pattern in INFOBOX_PATTERNS:
        matches = pattern.findall(wikitext)
        for match in matches:
            lines = match.split('\n')
            current_key = None
            current_value = []
            for line in lines:
                line = line.strip()
                if line.startswith('<!--') or not line:
                    continue
                if line.startswith('|') and '=' in line:
                    if current_key and current_value:
                        value = ' '.join(current_value).strip()
                        if value:
                            infobox_data[current_key.lower()] = clean_wiki_markup(value)
                    try:
                        key, value = line.split('=', 1)
                        current_key = key.strip(' |')
                        current_value = [value.strip()]
                    except ValueError:
                        continue
                elif current_key and line and not line.startswith('{{') and not line.startswith('|'):
                    current_value.append(line)
            if current_key and current_value:
                value = ' '.join(current_value).strip()
                if value:
                    infobox_data[current_key.lower()] = clean_wiki_markup(value)
    return infobox_data


def clean_wiki_markup(text: str) -> str:
    if not text:
        return ""
    for pattern, replacement in CLEANUP_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


def extract_clean_text_from_wikitext(wikitext: str) -> str:
    if not wikitext:
        return ""
    text = wikitext
    template_pattern = re.compile(r'\{\{[^{}]*\}\}')
    for _ in range(10):
        old_text = text
        text = template_pattern.sub('', text)
        if text == old_text:
            break
    for pattern, replacement in DESCRIPTION_PATTERNS:
        text = pattern.sub(replacement, text)
    text = clean_wiki_markup(text)
    paragraphs = [para.strip() for para in text.split('\n\n') if para.strip()]
    clean_paragraphs = [
        para for para in paragraphs
        if (len(para) > 50 and
            not PARAGRAPH_FILTER_PATTERNS[0].match(para) and
            not PARAGRAPH_FILTER_PATTERNS[1].search(para) and
            ('. ' in para or '! ' in para or '? ' in para))
    ]
    return '\n\n'.join(clean_paragraphs)


def format_description_text(text: str) -> str:
    if not text:
        return ""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    formatted_text = '\n\n'.join(paragraphs[:4])
    if len(formatted_text) <= 2200:
        return formatted_text
    truncated = formatted_text[:2200]
    for i in range(len(truncated) - 1, -1, -1):
        if truncated[i] in '.!?' and (
            i == len(truncated) - 1 or
            truncated[i + 1] in ' \n'
        ):
            return truncated[:i + 1]
    last_space = truncated.rfind(' ')
    return (truncated[:last_space] + "...") if last_space > 0 else truncated + "..."


def parse_portable_infobox_html(html_content: str) -> Dict[str, str]:
    if not html_content:
        return {}
    infobox_data = {}
    pi_data_pattern = re.compile(
        r'<div[^>]*class="[^\"]*pi-data[^\"]*"[^>]*data-source="([^\"]+)"[^>]*>.*?'
        r'<div[^>]*class="[^\"]*pi-data-value[^\"]*"[^>]*>(.*?)</div>',
        re.DOTALL | re.IGNORECASE
    )
    infoboxtable_pattern = re.compile(
        r'<tr[^>]*>\s*<td[^>]*><div[^>]*>([^<]+)</div></td>\s*<td[^>]*>(.*?)</td>\s*</tr>',
        re.DOTALL | re.IGNORECASE
    )
    matches = pi_data_pattern.findall(html_content)
    for field_name, value_html in matches:
        cleaned_value = clean_html_content(value_html)
        if cleaned_value and cleaned_value.strip():
            infobox_data[field_name.lower()] = cleaned_value.strip()
    if not infobox_data and 'infoboxtable' in html_content.lower():
        table_matches = infoboxtable_pattern.findall(html_content)
        for field_name, value_html in table_matches:
            cleaned_field = clean_html_content(field_name)
            cleaned_value = clean_html_content(value_html)
            if cleaned_field and cleaned_value and cleaned_value.strip():
                field_key = cleaned_field.lower().strip().rstrip(':').replace(' ', '_')
                infobox_data[field_key] = cleaned_value.strip()
    title_pattern = re.compile(
        r'<h2[^>]*class="[^\"]*pi-title[^\"]*"[^>]*data-source="([^\"]+)"[^>]*>'
        r'(.*?)</h2>',
        re.DOTALL | re.IGNORECASE
    )
    title_matches = title_pattern.findall(html_content)
    for field_name, title_html in title_matches:
        cleaned_title = clean_html_content(title_html)
        if cleaned_title and cleaned_title.strip():
            infobox_data[field_name.lower()] = cleaned_title.strip()
    return infobox_data


def clean_html_content(html: str) -> str:
    if not html:
        return ""
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'</li>\s*<li[^>]*>', ', ', html, flags=re.IGNORECASE)
    html = re.sub(r'</?[uo]l[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</?li[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', '', html)
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&#160;', ' ')
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&quot;', '"')
    html = html.replace('&#39;', "'")
    html = html.replace('&#91;', '[')
    html = html.replace('&#93;', ']')
    html = re.sub(r'\s+', ' ', html)
    return html.strip()
