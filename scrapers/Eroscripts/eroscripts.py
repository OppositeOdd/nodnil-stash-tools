#!/usr/bin/env python3

import sys
import os
import json
import re
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

"""
Eroscripts Forum JSON Parser
----------------------------
This script processes JSON data from eroscripts.com forum posts to extract metadata
about animation content. It focuses on identifying animators/studios and relevant
content details from forum posts.
"""

def clean_animator_name(name: str) -> str:
    """Sanitizes animator names by removing HTML, extra spaces, and brackets."""
    name = re.sub(r'<[^>]+>', '', name)
    name = name.strip('[]() \t\n\r')
    return name

def validate_animator(name: str, original_poster: str) -> bool:
    """
    Validates potential animator names by checking:
    - Not empty or too short
    - Not same as the original poster
    - Not a URL
    """
    if not name or len(name) < 2:
        return False
    if name.lower() == original_poster.lower():
        return False
    if re.match(r'https?://', name):
        return False
    return True

def format_title_for_stash(title: str, animator: Optional[str] = None) -> str:
    """
    Format title according to Stash preferences:
    1. Remove brackets/parentheses and their contents: (), [], {}, "", ''
    2. Replace + and & with "and"
    3. Remove special characters like @, #
    4. Add animator name in brackets at the beginning if provided
    
    Example:
        "[SeventyFive] Belle + Ellen Joe (Suggested)" -> "[SeventyFive] Belle and Ellen Joe"
    """
    # Step 1: Remove brackets/parentheses and everything inside them
    # Match (), [], {}, "", '' and their contents
    title = re.sub(r'\([^)]*\)', '', title)  # Remove (...)
    title = re.sub(r'\[[^\]]*\]', '', title)  # Remove [...]
    title = re.sub(r'\{[^}]*\}', '', title)  # Remove {...}
    title = re.sub(r'"[^"]*"', '', title)    # Remove "..."
    title = re.sub(r"'[^']*'", '', title)    # Remove '...'
    
    # Step 2: Replace + and & with "and"
    title = re.sub(r'\s*\+\s*', ' and ', title)
    title = re.sub(r'\s*&\s*', ' and ', title)
    
    # Step 3: Remove other special characters but keep alphanumeric, spaces, and hyphens
    title = re.sub(r'[@#]', '', title)
    
    # Clean up extra whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Step 4: Add animator name in brackets at the beginning if provided
    if animator:
        # Remove any existing animator prefix if it's already there
        title = title.strip()
        # Add the animator in brackets
        title = f"[{animator}] {title}"
    
    return title

def extract_animator_from_description(description: str) -> Optional[str]:
    """
    Primary animator extraction method (highest priority).
    Searches for explicit animator credits in post descriptions using common patterns.
    """
    patterns = [
        r'Animator[:\s]+([^\."\n\]]+)',
        r'Animation (?:made )?by[:\s]+([^\."\n\]]+)',
        r'Created by[:\s]+([^\."\n\]]+)',
        r'Made by[:\s]+([^\."\n\]]+)',
        r'Animator[:\s]+\[(.*?)\]',
        r'Animation by[:\s]+\[(.*?)\]',
        r'Created by[:\s]+\[(.*?)\]',
        r'Made by[:\s]+\[(.*?)\]',
        r'Support the creator[:\s]+([^\."\n\]]+)',
        r'Support the creator[:\s]+\[(.*?)\]'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, description, re.IGNORECASE)
        for match in matches:
            return match.group(1).strip()
    return None

def extract_animator_from_title(title: str) -> Optional[str]:
    """
    Secondary animator extraction method.
    Looks for names in brackets/parentheses at the start or end of titles.
    """
    start_match = re.match(r'[\[\(](.*?)[\]\)]', title)
    if start_match:
        return start_match.group(1).strip()
    
    end_match = re.search(r'[\[\(](.*?)[\]\)]$', title)
    if end_match:
        return end_match.group(1).strip()
    
    return None

def extract_animator_from_links(links: List[str]) -> Optional[str]:
    """
    Tertiary animator extraction method.
    Extracts usernames from common support platform URLs.
    """
    support_domains = ['patreon.com', 'ko-fi.com', 'buymeacoffee.com']
    for link in links:
        parsed = urlparse(link)
        if parsed.netloc.lower() in support_domains:
            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                return path_parts[0]
    return None

def extract_animator(title: str, description: str, links: List[str], original_poster: str) -> Optional[str]:
    """
    Orchestrates animator extraction using multiple methods in priority order.
    Returns the first valid animator name found or None if no valid candidates.
    """
    methods = [
        lambda: extract_animator_from_description(description),
        lambda: extract_animator_from_title(title),
        lambda: extract_animator_from_links(links)
    ]
    
    for method in methods:
        candidate = method()
        if candidate:
            clean_name = clean_animator_name(candidate)
            if validate_animator(clean_name, original_poster):
                return clean_name
    
    return None

def parse_eroscripts_json(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main parsing function for Eroscripts forum JSON data.
    Processes forum posts to extract animation metadata, focusing on:
    - Basic post metadata (title, tags)
    - Animation content detection
    - Animator/studio identification
    - Post content and engagement metrics
    """
    result = {
        "title": "",
        "tags": [],
        "description": "",
        "posts": [],
        "details": {},
        "studio": None  # Will hold the animator name
    }
    
    # Basic metadata
    result["title"] = json_data.get("fancy_title", "") or json_data.get("title", "")
    result["tags"] = json_data.get("tags", [])
    result["studio"] = None  # Initialize studio as None
    
    # Define animation-related tags
    ANIMATION_TAGS = {"animation", "cgi", "hentai"}
    
    # Check if any animation-related tags are present (case-insensitive)
    post_tags_lower = {tag.lower() for tag in result["tags"]}
    is_animated = bool(ANIMATION_TAGS & post_tags_lower)  # Check for intersection
    
    # Only process animator/studio if animation-related tag is present
    if is_animated:
        # Get first post content for animator extraction
        posts = json_data.get("post_stream", {}).get("posts", [])
        if posts:
            first_post = posts[0]
            first_post_content = first_post.get("cooked", "")
            original_poster = first_post.get("username", "")
            
            # Extract links from first post
            first_post_links = re.findall(r'href=["\'](.*?)["\']', first_post_content)
            
            # Try to extract animator
            animator = extract_animator(
                result["title"],
                first_post_content,
                first_post_links,
                original_poster
            )
            result["studio"] = animator
    
    # Process posts if available
    posts = json_data.get("post_stream", {}).get("posts", [])
    if posts:
        # First post is typically the main content
        first_post = posts[0]
        result["description"] = first_post.get("cooked", "")  # HTML content
        result["details"].update({
            "created_at": first_post.get("created_at"),
            "updated_at": first_post.get("updated_at"),
            "author": first_post.get("username"),
            "post_number": first_post.get("post_number"),
            "like_count": first_post.get("like_count")
        })

        def extract_links(html: str) -> List[str]:
            # Find all href links in the HTML
            return re.findall(r'href=["\"](.*?)["\"]', html)

        # Store processed versions of all posts, including links
        result["posts"] = [{
            "content": post.get("cooked", ""),
            "author": post.get("username", ""),
            "created_at": post.get("created_at"),
            "post_number": post.get("post_number"),
            "like_count": post.get("like_count", 0),
            "links": extract_links(post.get("cooked", ""))
        } for post in posts]
    
    return result

def save_processed_data(data: Dict[str, Any], output_dir: str = "processed_scripts") -> str:
    """
    Saves processed data to a JSON file, using the post title or timestamp as filename.
    Creates output directory if needed and returns the save path.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    if data.get("title"):
        safe_title = "".join(c for c in data["title"] if c.isalnum() or c in " -_")[:100]
        filename = f"script_{safe_title}.json"
    else:
        from datetime import datetime
        filename = f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    filepath = Path(output_dir) / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return str(filepath)


def to_stash_scene(processed: Dict[str, Any], source_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Map internal processed structure to Stash scene object schema.
    Returns a dict matching the fields Stash expects for a scene fragment.
    """

    import mimetypes
    import tempfile
    import shutil
    from pathlib import Path

    def download_image(url: str) -> str:
        """
        Download image from URL and save to a temp file. No conversion is performed.
        Returns local file path to the image, or empty string on failure.
        """
        try:
            import requests
        except ImportError:
            return ""
        resp = requests.get(url, stream=True, timeout=15)
        if resp.status_code != 200:
            return ""
        content_type = resp.headers.get('content-type', '')
        ext = mimetypes.guess_extension(content_type) or Path(url).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(resp.raw, tmp)
            tmp_path = tmp.name
        return tmp_path

    # Always use top-level 'image_url' if present
    image_url = processed.get('image_url')
    # Fallback: previous logic if image_url not found
    if not image_url:
        # Try thumbnails array (from topic JSON)
        thumbs = processed.get('thumbnails')
        if thumbs and isinstance(thumbs, list):
            for thumb in thumbs:
                url = thumb.get('url')
                if url and url.startswith('http') and '/original/' in url:
                    image_url = url
                    break
        # Fallback: first /original/ image in post content (excluding avatars/banners/emojis)
        if not image_url:
            thumbnail_url = None
            posts = processed.get('posts', [])
            if posts:
                cooked = posts[0].get('content', '')
                img_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', cooked)
                def is_valid_cover(url: str) -> bool:
                    lowered = url.lower()
                    if not '/original/' in lowered:
                        return False
                    exclude_patterns = [
                        '/avatar/', '/user_avatar/', '/letter_avatar/', '/emoji/', '/uploads/default/original/1x/', '/uploads/default/original/2x/'
                    ]
                    return not any(p in lowered for p in exclude_patterns)
                for url in img_urls:
                    if is_valid_cover(url):
                        thumbnail_url = url
                        break
                if not thumbnail_url:
                    for url in img_urls:
                        if '/original/' in url:
                            thumbnail_url = url
                            break
                if not thumbnail_url and img_urls:
                    thumbnail_url = img_urls[0]
                if thumbnail_url and (thumbnail_url.startswith('http://') or thumbnail_url.startswith('https://')):
                    image_url = thumbnail_url

    # Format title with animator name
    raw_title = processed.get('title') or ''
    animator = processed.get('studio')
    formatted_title = format_title_for_stash(raw_title, animator)

    # Title without animator (remove leading [animator] if present)
    title_wo_animator = re.sub(r'^\[[^\]]+\]\s*', '', formatted_title).strip()

    # Get original poster
    original_poster = None
    posts = processed.get('posts', [])
    if posts:
        original_poster = posts[0].get('author')

    # Format description as requested
    details_text = f"{title_wo_animator} created by {animator}. Scripted by {original_poster}"

    scene: Dict[str, Any] = {
        "Title": formatted_title or None,
        "Details": details_text or None,
    }
    # Add cover image as 'Image' if available
    if image_url:
        scene['Image'] = image_url

    # Date: attempt to parse created_at if present
    created = processed.get('details', {}).get('created_at')
    if created:
        try:
            # try to parse ISO-like timestamps
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            scene['Date'] = dt.date().isoformat()
        except Exception:
            # leave Date unset if parse fails
            pass

    # Studio
    if processed.get('studio'):
        scene['Studio'] = {"Name": processed.get('studio')}

    # Tags -> list of {Name: tag} and always include 'Scripted'
    tags = processed.get('tags') or []
    # Ensure 'Scripted' is present (case-insensitive check)
    existing_lower = {t.lower() for t in tags}
    if 'scripted' not in existing_lower:
        tags.append('Scripted')
    scene['Tags'] = [{"Name": t} for t in tags]

    # URL: Stash expects a simple string, not an array
    if source_url:
        scene['URL'] = source_url

    # Remove None values
    scene = {k: v for k, v in scene.items() if v is not None}
    return scene


def fetch_forum_json(url: str, cookies: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Fetch the Eroscripts/Discourse topic JSON for a given topic URL.
    Tries appending '.json' to the URL if needed. Returns parsed JSON dict.
    This function imports `requests` lazily and raises a helpful error if it's
    not installed.
    """
    try:
        import requests
    except Exception as e:
        raise RuntimeError("The 'requests' library is required to fetch URLs. Install with: pip install requests") from e

    # Prefer requesting the .json endpoint for Discourse topics
    fetch_urls = []
    if url.endswith('.json'):
        fetch_urls.append(url)
    else:
        fetch_urls.append(url.rstrip('/') + '.json')
        fetch_urls.append(url)

    debug = os.getenv('ES_DEBUG_FETCH') == '1'
    # Ensure we send sensible defaults similar to the YAML driver
    if headers is None:
        headers = {
            "Accept": "application/json",
            "User-Agent": "stash-scraper/v1",
        }

    for u in fetch_urls:
        try:
            if debug:
                print(f"[fetch_forum_json] attempting: {u}", file=sys.stderr)
            resp = requests.get(u, cookies=cookies or {}, headers=headers or {}, timeout=15)
            if debug:
                print(f"[fetch_forum_json] status: {resp.status_code} for {u}", file=sys.stderr)
            resp.raise_for_status()
            # If response is JSON, parse it
            try:
                return resp.json()
            except ValueError:
                # Not JSON, provide debug info then try next candidate
                if debug:
                    snippet = (resp.text or '')[:1000]
                    print(f"[fetch_forum_json] response not JSON (snippet):\n{snippet}", file=sys.stderr)
                continue
        except Exception as e:
            if debug:
                print(f"[fetch_forum_json] error fetching {u}: {e}", file=sys.stderr)
            # Try next URL
            continue

    raise RuntimeError(f"Failed to fetch forum JSON for url: {url}")

def main():
    """
    Main execution flow with basic Stash script action support.

    Usage (called by Stash):
      python fetch_eroscripts.py <mode>

    Modes supported:
      - scrapeURL / scrape : expects full forum JSON on stdin (or a fragment containing 'post_stream')
      - query (not implemented): placeholder for future search support

    By default the script prints the internal processed structure. To enable saving
    of the processed JSON to disk set environment variable ES_SAVE_OUTPUT=1 or pass
    the --save flag as the second argument.
    """
    try:
        args = sys.argv[1:]
        mode = args[0] if args else None
        # alias 'post' (as used in the user's YAML) to 'scrape'
        if mode == 'post':
            mode = 'scrape'

        save_flag = ('--save' in args) or (os.getenv('ES_SAVE_OUTPUT') == '1')

        json_data = json.load(sys.stdin)

        # If Stash passes a full forum JSON (contains post_stream), process it.
        if 'post_stream' in json_data:
            processed_data = parse_eroscripts_json(json_data)

            if save_flag:
                saved_path = save_processed_data(processed_data)
                print(f"Successfully processed and saved to: {saved_path}", file=sys.stderr)

            # If mode requests a Stash scene fragment, map and output it
            if mode in ('scrapeURL', 'scrape'):
                # Attempt to extract a source URL if present in top-level
                source_url = json_data.get('url') or json_data.get('topic_url')
                stash_scene = to_stash_scene(processed_data, source_url=source_url)
                print(json.dumps(stash_scene, ensure_ascii=False))
            else:
                # Default: output the normalized internal structure
                print(json.dumps(processed_data, ensure_ascii=False))

        else:
            # No post_stream: likely Stash passed just {'url': '...'} for scrapeURL.
            if mode in ('scrapeURL', 'scrape') and 'url' in json_data:
                # Collect cookies from env or CLI args
                cookies: Dict[str, str] = {}
                # ENV: ES_COOKIE__<name>=<value> or ES_COOKIES as JSON
                env_cookies = os.getenv('ES_COOKIES')
                if env_cookies:
                    try:
                        cookies.update(json.loads(env_cookies))
                    except Exception:
                        pass

                # Support individual cookie env vars: ES_COOKIE__name
                for k, v in os.environ.items():
                    if k.startswith('ES_COOKIE__'):
                        cookie_name = k.split('ES_COOKIE__', 1)[1]
                        cookies[cookie_name] = v

                # Also accept CLI flags like --cookie name=value or --cookie=name=value
                for a in args:
                    if a.startswith('--cookie'):
                        # Handle both --cookie=name=value and --cookie name=value
                        if '=' in a:
                            # Format: --cookie=name=value
                            cookie_part = a.split('=', 1)[1]  # Get everything after first =
                            # Now split on first = to separate name from value
                            if '=' in cookie_part:
                                name, val = cookie_part.split('=', 1)
                                cookies[name] = val
                            else:
                                # No = means the value itself, treat as a single cookie
                                cookies[cookie_part] = ''
                        # If no = in the arg itself, it might be the next arg

                # Headers from env (ES_HEADERS as JSON) or none
                headers = None
                env_headers = os.getenv('ES_HEADERS')
                if env_headers:
                    try:
                        headers = json.loads(env_headers)
                    except Exception:
                        headers = None

                # Fetch the forum JSON and continue
                try:
                    forum_json = fetch_forum_json(json_data['url'], cookies=cookies or None, headers=headers)
                    processed_data = parse_eroscripts_json(forum_json)
                    if save_flag:
                        saved_path = save_processed_data(processed_data)
                        print(f"Successfully processed and saved to: {saved_path}", file=sys.stderr)
                    source_url = json_data.get('url')
                    stash_scene = to_stash_scene(processed_data, source_url=source_url)
                    print(json.dumps(stash_scene, ensure_ascii=False))
                except Exception as e:
                    print(f"Error fetching forum JSON: {e}", file=sys.stderr)
                    sys.exit(1)
                return

            # Fallback: try to process whatever was given
            processed_data = parse_eroscripts_json(json_data)
            if save_flag:
                saved_path = save_processed_data(processed_data)
                print(f"Successfully processed and saved to: {saved_path}", file=sys.stderr)
            print(json.dumps(processed_data, ensure_ascii=False))

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing data: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()