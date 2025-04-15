# PTT Stock Sentiment Analyzer (xAI)

A Python project to analyze sentiment on the PTT Stock board using xAI, summarize market trends, and manage article data securely.

## Features
- **Scrape** articles from the PTT Stock board and save as CSV
- **Analyze** sentiment using xAI (or simulate if xAI is unavailable)
- **Summarize** discussions, market outlook, and key details into markdown reports
- **Sanitize** article data after analysis to keep only metadata (title, date, url)
- **Command-line** interface with flexible options

## Directory Structure
```
ptt-stock-ai/
├── analysis/                    # Output markdown reports
├── ptt_sentiment_analyzer.py    # Main sentiment analysis script
├── ptt_stock_scraper.py         # Scrapes articles from PTT Stock board
├── sanitize_full_article.py     # Sanitizes CSV files (removes content, keeps metadata)
├── xai_stock_sentiment_prompt.txt # Prompt template for xAI
├── requirements.txt             # Python dependencies (if present)
└── ...
```

## Setup
1. **Clone the repository**
2. **Install dependencies** (recommended: Python 3.8+)
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up environment variables**
   - Place your `.env` file in your home directory with `XAI_API_KEY` if using xAI API.

## Usage
### 1. Scrape Articles
```bash
python ptt_stock_scraper.py --date 04-14 --max-pages 20
```
- Saves articles to `ptt_stock_articles_*.csv`

### 2. Sentiment Analysis
```bash
python ptt_sentiment_analyzer.py --csv <article_file.csv> [--output <output.md>] [--sanitize-csv]
```
- `--csv`: Path to the CSV file (default: latest)
- `--output`: Output markdown file (default: in `analysis/`)
- `--sanitize-csv`: After analysis, remove article content/comments and keep only title, date, url

### 3. Sanitize Article CSV (standalone)
```bash
python sanitize_full_article.py <article_file.csv>
```

## Example Workflow
1. Scrape: `python ptt_stock_scraper.py --date 04-14`
2. Analyze: `python ptt_sentiment_analyzer.py --sanitize-csv`
3. Review markdown in `analysis/`
4. The CSV will be sanitized, keeping only metadata for privacy.

## Notes
- If you do not have xAI API access, the analyzer will simulate a response.
- All logs are printed to the console for transparency.

## Credits
- Developed by Chung-Wen Lin
- For questions or collaboration, please contact: [lincw1111@gmail.com](mailto:lincw1111@gmail.com)

---
MIT License
