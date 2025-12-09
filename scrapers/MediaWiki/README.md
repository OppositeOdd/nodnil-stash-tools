# MediaWiki Scraper

Comprehensive performer data extraction from MediaWiki-based sites including Fandom, Wikipedia, and other MediaWiki installations.

## Features

### Core Functionality
- **Portable Infobox Support**: Extracts data from modern Fandom infoboxes
- **Legacy Wikitext Parsing**: Supports traditional MediaWiki infoboxes
- **Multiple Site Support**: Fandom, Wikipedia, custom MediaWiki installations
- **Configurable Field Mapping**: Flexible field name matching

### Advanced Features
- **Height/Weight Parsing**: Converts imperial to metric (5'6" → 167 cm)
- **Measurements Conversion**: Grabs raw measurements and standardizes them (i.e 36B-24-35)
- **Birthdate Approximation**: Converts partial dates and approximates them ("1995" → "1995-01-01" / Birthday: May 13th → "2005-05-13" / Age: 21 Birthday: May 13th → "2004-05-13")
- **Universe Tagging**: Automatic franchise/universe tag or disambiguation settings (Configurable)

### Fictional Character Support
- **Raw Data Preservation**: Keep original values (Red eyes, Human race)
- **Standardized Output**: Convert to Stash enums (RED eyes, CAUCASIAN ethnicity)
- **Configurable Processing**: Choose between fictional vs real person modes

## Configuration

Edit `config.json` to customize behavior:

```json
{
  "map_race_to_ethnicity": true,
  "map_universe_to_disambiguation": true, 
  "max_description_length": 2200,
  "extract_categories": false,
  "approximate_birthdate": true,
  "add_universe_to_tags": true,
  "fictional_character_features": true
}
```

### Configuration Options
|--------------Name----------------|Default|------------------Description------------------------| 
| `map_race_to_ethnicity`          | false | Map 'race' field to 'ethnicity' (fantasy wikis)     |
| `map_universe_to_disambiguation` | false | Map 'universe' to 'disambiguation' field            |
| `max_description_length`         | 2200  | Maximum description length before truncation        |
| `extract_categories`             | false | Include wiki categories as tags                     |
| `approximate_birthdate`          | true  | Convert partial ages/birthdays to YYYY-MM-DD        |
| `add_universe_to_tags`           | true  | Add franchise/universe as tags                      |
| `fictional_character_features`   | false | Allow non standard features i.e demon race,pink eyes|               

**Note**: `fictional_character_features` must be `true` for proper race-to-ethnicity mapping.

## Supported Sites

- **Fandom**: *.fandom.com (primary target)
- **Wikipedia**: *.wikipedia.org  
- **Wikimedia**: *.wikimedia.org
- **Wiki.gg**: wiki.gg
- **BG3 Wiki**: bg3.wiki
- **Custom MediaWiki**: Other MediaWiki installations, check the MediaWiki.yaml for full list

## Module Structure

```
MediaWiki/
├── main.py                 # Entry point and orchestration
├── api_discovery.py        # MediaWiki API detection and content extraction
├── content_parser.py       # Wikitext and HTML parsing
├── data_extractor.py       # Field mapping and data extraction  
├── data_converter.py       # Data normalization and conversion
├── performer_processor.py  # Final data processing and formatting
├── image_extractor.py      # Image URL extraction and processing
└── config.json             # Configuration file
```

## Examples

### Fantasy Character (Fictional Mode)
```json
{
  "name": "Lulu",
  "eye_color": "Red",
  "ethnicity": "Human", 
  "hair_color": "Pink",
  "height": 167,
  "tags": [{"name": "Final Fantasy"}]
}
```

### Real Person (Standardized Mode) (Still better to use a reputable database like StashDB for IRL content)
```json
{
  "name": "Example Person",
  "eye_color": "BROWN",
  "ethnicity": "CAUCASIAN",
  "hair_color": "BLACK", 
  "height": 167,
}
```

### Fantasy Species Mapping Examples
When `fictional_character_features` is `false` and `map_race_to_ethnicity` is `true`:

```json
{
  "name": "Elf Character",
  "ethnicity": "CAUCASIAN"  // Mapped from "Elf" race
},
{
  "name": "Orc Character", 
  "ethnicity": "OTHER"      // Mapped from "Orc" race
},
{
  "name": "Android Character",
  "ethnicity": "OTHER"      // Mapped from "Android" species
}
```


## Field Mappings

The scraper maps various infobox field names to standard Stash fields:

- **Name**: full_name, name, title, character_name
- **Physical**: height, weight, measurements, hair_color, eye_color
- **Identity**: gender, ethnicity, nationality, country, race, species
- **Dates**: birthdate, birth_date, age, born
- **Career**: career_start, debut, career_end, retired
- **Other**: aliases, piercings, tattoos

## Troubleshooting

### Common Issues

1. **No data extracted**: Check if the page actually has the data available, it fails in some edge cases still
2. **Missing fields**: Verify field names in the source infobox
3. **Incorrect ethnicity**: Ensure `fictional_character_features` is set correctly
4. **API errors**: Check MediaWiki site accessibility and API availability

## Recent Updates

- Enhanced fictional character support with configurable processing
- Improved height/weight parsing with metric conversion
- Enhanced nationality processing with guess_nationality integration  
- Added universe/franchise tagging system
- Updated configuration system with better documentation
