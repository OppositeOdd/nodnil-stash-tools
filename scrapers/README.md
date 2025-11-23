# Stash Scrapers

Custom scrapers for [Stash](https://github.com/stashapp/stash) to fetch metadata from various sources.

## 📦 Available Scrapers

### Eroscripts
Scrapes scene metadata from [Eroscripts forum](https://discuss.eroscripts.com/) posts, including:
- Scene titles and descriptions
- Animator/studio detection
- Tags and categories
- Forum post metadata

### Fandom (MediaWiki)
Universal MediaWiki scraper supporting multiple wiki platforms:
- Fandom wikis (`.fandom.com`)
- Wiki.gg sites
- Miraheze wikis
- Wikipedia
- And many other MediaWiki-based sites

## 🚀 Installation

### Prerequisites

1. Install required Stash components:
   - Navigate to **Settings → Metadata Providers → Available Scrapers**
   - Install `py_common` (required for Python scrapers)
   - Install any other scrapers you want (e.g., `Rule34Video`)

2. Install Python Tools:
   - Navigate to **Settings → Plugins → Available Plugins**
   - Install `Python Tools Installer`
   - After reloading plugins, go to **Settings → Tasks**
   - Run `Install Python Tools`

### Installing the Scrapers

1. Locate your Stash scrapers directory:
   - Navigate to **Settings → System → Scrapers Path**
   - Default path: `/path/to/stash/scrapers/community/`

2. Copy the scraper folders:
   - Place `Eroscripts/` and `Fandom/` folders into the `community/` directory

3. Reload scrapers:
   - Navigate to **Settings → Metadata Providers**
   - Click **Reload Scrapers**

## ⚙️ Configuration

Some fields are mapped in non-standard ways by default, you will need to adjust these manually or leave as is.

- Tag [Scripted] is added every time this scraper is used if it exists.
- Director is mapped to original poster, to credit the scripter
- Studio is mapped to animator if they are successfully pulled from the post
- Group is mapped to Universe/Franchise

### Eroscripts Setup

Eroscripts requires authentication cookies to access forum content.

#### Getting Your Cookies

**Option 1: Browser Method (Quick but temporary)**

1. Navigate to https://discuss.eroscripts.com/ and login
2. Press `F12` to open Developer Tools
3. Go to the **Application** tab
4. Click **Cookies** in the sidebar
5. Find and copy the values for:
   - `_forum_session`
   - `_t`

**Option 2: curl Method (Recommended for stability)**

Browser cookies refresh frequently and may expire within hours. For stable cookies, use curl:

```bash
# Install jq for JSON parsing (if not already installed)
sudo apt update && sudo apt install -y jq

# Set your credentials
export EROSCRIPTS_USER='your_username'
export EROSCRIPTS_PASS='your_password'

# Configure variables
CK="eroscripts_cookies.txt"
BASE="https://discuss.eroscripts.com"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# Get CSRF token
curl -s -c "$CK" -b "$CK" -A "$UA" "$BASE/session/csrf.json" | jq -r '.csrf' | tee csrf.txt
CSRF=$(cat csrf.txt)

# Login to get session cookies
curl -s -c "$CK" -b "$CK" -A "$UA" \
  -H "Referer: $BASE/login" \
  -H "Origin: $BASE" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Content-Type: application/json" \
  --data-binary "{\"login\":\"$EROSCRIPTS_USER\",\"password\":\"$EROSCRIPTS_PASS\"}" \
  "$BASE/session" | tee login_resp.json

# View login response
jq . login_resp.json

# Verify login was successful (prints your username)
curl -s -c "$CK" -b "$CK" -A "$UA" "$BASE/session/current.json" | jq -r '.current_user.username'

# Extract cookies from the cookies file
cat "$CK" | grep _forum_session
cat "$CK" | grep _t
```

#### Adding Cookies to the Scraper

1. Open `scrapers/community/Eroscripts/eroscripts.yml`
2. Find the commented cookie lines:
   ```yaml
   # - --cookie=_forum_session=YOUR_SESSION_COOKIE_HERE
   # - --cookie=_t=YOUR_T_COOKIE_HERE
   ```
3. Uncomment and replace with your actual cookie values:
   ```yaml
   - --cookie=_forum_session=YOUR_ACTUAL_COOKIE_VALUE
   - --cookie=_t=YOUR_ACTUAL_COOKIE_VALUE
   ```
4. Save the file
5. Reload scrapers in Stash

### Fandom (MediaWiki) Setup

The Fandom scraper works out of the box with default settings.

**Optional Configuration:**

Some uncommon fields are mapped in non-standard ways by default, these can be changed in config.json

- Disambiguation to the Universe or Frnachise of the character (i.e Zenless Zone Zero)
- Ethnicity to Race (i.e Demon or Human)
- Birthdate is approximated (if it has the year only it inputs January 1st, if it only has DD-MM it defaults to 2005)

A `config.json.example` file is provided for advanced customization:

1. Copy or rename `config.json.example` to `config.json`
2. Adjust settings as needed (explanations provided in the file)
3. Save and reload scrapers

Common settings include:
- Preferred image sizes
- Tag filtering options
- Custom field mappings

## 📖 Usage

### Using Eroscripts Scraper

1. Copy the URL of an Eroscripts forum post
2. In Stash, go to the scene you want to scrape
3. Enter the URL into URL field
4. Press the scrape icon next to the field
5. Modify the pulled data and save

### Using Fandom Scraper

1. Copy the URL of a wiki page (from any supported MediaWiki site)
2. In Stash, go to a performer entry
3. Enter the URL into URL field
4. Press the scrape icon next to the field
5. Modify the pulled data and save

## 🛠️ Troubleshooting

### Eroscripts Issues

**Problem:** Scraper returns no data or errors
- **Solution:** Your cookies may have expired. Refresh them using the curl method for longer-lasting cookies

**Problem:** "Access Denied" errors
- **Solution:** Verify your cookies are correctly formatted in `eroscripts.yml` (no extra spaces or brackets)

### Fandom Issues

**Problem:** Wiki not supported
- **Solution:** Check if the wiki URL matches one of the supported patterns in `fandom.yml`

**Problem:** API errors
- **Solution:** Some wikis have custom API paths. The scraper auto-discovers them, but very unusual setups may fail

## 📋 Requirements

- Python 3.6+
- Stash with Python scraper support
- Required Python packages (auto-installed by Python Tools Installer):
  - `requests`
  - `py_common` (Stash community library)

## 🔗 Additional Resources

- [Stash Documentation](https://docs.stashapp.cc/)
- [Community Scrapers](https://github.com/stashapp/CommunityScrapers)
- [Eroscripts Forum](https://discuss.eroscripts.com/)

## 📝 Notes

- Eroscripts cookies from regular browsers may expire frequently due to VPN usage or cache clearing
- The curl method provides more stable cookies for Eroscripts
- Fandom scraper supports performer and group scraping from various wiki platforms
- Both scrapers respect rate limits and site terms of service
