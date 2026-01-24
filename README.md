# Bot & Troll Detector - Social Media Analysis

Multi-platform tool for extracting and analyzing social media comments to detect bots, trolls, and coordinated inauthentic behavior using Machine Learning.

## Features

- **Multi-platform scraping**: Facebook + TikTok comment extraction
- **Bot/Troll Detection**: Isolation Forest + DBSCAN anomaly detection
- **Sentiment Analysis**: Pro-candidate vs Anti-candidate classification
- **Temporal Analysis**: Suspicious posting patterns (late night, coordinated timing)
- **Text Analysis**: TF-IDF, n-grams, similarity detection
- **Behavioral Features**: User frequency, duplicate detection, coordinated messaging

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install pandas numpy scikit-learn matplotlib seaborn
pip install TikTokApi playwright
playwright install chromium
```

## Quick Start

### 1. Scrape Comments

```bash
# TikTok
python scripts/tiktok/tk_scraper.py "https://www.tiktok.com/@user/video/ID"

# Facebook
python scripts/facebook/fb_scraper.py
```

### 2. Run Bot/Troll Detection

Open and run the Jupyter notebook:
```bash
jupyter notebook notebooks/botsDetector_2.ipynb
```

The notebook will:
1. Load all scraped data from `data/scrapes_facebook/` and `data/scrapes_tiktok/`
2. Clean and preprocess text
3. Extract temporal features (posting hours, patterns)
4. Classify sentiment (Pro vs Against)
5. Detect anomalies using Isolation Forest + DBSCAN
6. Export results to `data/results/bot_troll_analysis.csv`

## Detection Methodology

### Features Extracted
| Category | Features |
|----------|----------|
| **Text** | Length, word count, emoji count, caps ratio, duplicates |
| **Behavioral** | User comment frequency, similarity between comments |
| **Temporal** | Hour of day, day of week, late night posting |
| **NLP** | TF-IDF vectors, n-grams, cosine similarity |

### Anomaly Detection
- **Isolation Forest**: Detects outliers by isolation in feature space
- **DBSCAN**: Clusters similar behavior, marks outliers as cluster -1
- **Combined Score**: High confidence when both methods agree

### Classification Output
| Score | Classification | Description |
|-------|---------------|-------------|
| 2 | High Suspicion | Detected by both methods |
| 1 | Medium Suspicion | Detected by one method |
| 0 | Normal | No anomalies detected |

## Output Files

```
data/results/
├── bot_troll_analysis.csv    # Full analysis with classifications
└── resultados_bots_detectados.csv
```

### CSV Columns
- `platform`: facebook/tiktok
- `text`: Original comment
- `sentimiento`: a_favor/en_contra/neutro
- `bot_classification`: Normal/Medium Suspicion/High Suspicion
- `bot_score`: 0-2
- `max_similarity`: Highest similarity to other comments
- `is_duplicate`: Boolean flag

## Project Structure

```
trollDetector/
├── scripts/
│   ├── facebook/
│   │   └── fb_scraper.py      # Facebook comment scraper
│   ├── tiktok/
│   │   └── tk_scraper.py      # TikTok comment scraper
│   └── common/                # Shared utilities
│
├── data/
│   ├── scrapes_facebook/      # Raw Facebook JSON files
│   ├── scrapes_tiktok/        # Raw TikTok JSON files
│   └── results/               # Analysis output (CSV)
│
├── notebooks/
│   └── botsDetector_2.ipynb   # Main analysis notebook
│
└── README.md
```

## Scrapers Usage

### Facebook Scraper

```bash
# Requires cookies file for headless mode
python scripts/facebook/fb_scraper.py
```

Note: Opens Playwright browser. If login needed, saves cookies to `scripts/facebook/fb-cookies.json`.

### TikTok Scraper

```bash
python scripts/tiktok/tk_scraper.py "https://www.tiktok.com/@user/video/ID"
```

## Use Cases

- **Political Analysis**: Detect coordinated campaigns, astroturfing
- **Content Moderation**: Identify spam accounts, bot networks
- **Research**: Study inauthentic behavior patterns
- **Marketing**: Analyze engagement authenticity

## Roadmap

- [x] Multi-platform scraping (Facebook + TikTok)
- [x] Isolation Forest + DBSCAN anomaly detection
- [x] Sentiment classification (Pro/Against)
- [x] Temporal pattern analysis
- [ ] Deep learning text classification
- [ ] Real-time monitoring dashboard
- [ ] Network analysis (coordinated accounts)
- [ ] API for integration

## Important Notes

- `scripts/facebook/fb-cookies.json` contains session cookies - protect if repo is public
- Playwright requires browser installation (`playwright install chromium`)
- Unofficial APIs may be blocked - use responsibly and respect TOS

## Legal Disclaimer

This tool is for educational and research purposes only. Respect platform Terms of Service and applicable privacy laws. Do not use for:

- Spam or harassment
- Privacy violations
- Unauthorized mass scraping
- Malicious targeting of individuals

---

Built with Python, scikit-learn, and Playwright
