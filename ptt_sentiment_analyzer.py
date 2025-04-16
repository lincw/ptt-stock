#!/usr/bin/env python3
"""
PTT Stock Sentiment Analyzer (xAI)
Follows the ArticleAnalyzer structure. Reads a PTT stock CSV, loads the xAI prompt, sends the content to xAI,
and saves the xAI output to a markdown file with the same timestamp as the CSV.
"""
import os
import glob
import csv
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Dict, List
import argparse
import subprocess
import sys

from openai import OpenAI
import httpx

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file in Documents folder
env_path = Path.home() / ".env"
load_dotenv(env_path)

PROMPT_FILE = "xai_stock_sentiment_prompt.txt"
CSV_PATTERN = "ptt_stock_articles_*.csv"
OUTPUT_MD_PATTERN = "ptt_stock_sentiment_{}.md"

class PTTStockSentimentAnalyzer:
    def __init__(self, api_key: str = None):
        """Initialize with xAI API key."""
        self.api_key = api_key or os.getenv('XAI_API_KEY')
        if not self.api_key:
            logger.error("XAI_API_KEY not found in environment variables or .env file.")
        # Set up httpx/OpenAI client if available
        if OpenAI and httpx and self.api_key:
            http_client = httpx.Client(proxies=None, transport=httpx.HTTPTransport(retries=3))
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.x.ai/v1",
                http_client=http_client
            )
        else:
            self.client = None

    def read_prompt(self) -> str:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()

    def read_articles(self, csv_file: Path) -> List[Dict]:
        articles = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            # Skip meta/comment lines
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    break
                if not line.startswith('#'):
                    f.seek(pos)
                    break
            reader = csv.DictReader(f)
            for row in reader:
                articles.append(row)
        return articles

    def prepare_xai_input(self, articles: List[Dict]) -> str:
        texts = []
        for art in articles:
            texts.append(f"【標題】{art['title']}\n【作者】{art['author']}\n【日期】{art['year']}/{art['date']}\n【內文】{art['content']}\n【留言】{art['comments']}\n---")
        return '\n'.join(texts)

    def analyze_article(self, prompt: str, content: str) -> str:
        """Send combined content to xAI API (or simulate if not available)."""
        logger.info(f"Starting xAI analysis. Prompt length: {len(prompt)}. Content length: {len(content)}.")
        if self.client:
            try:
                completion = self.client.chat.completions.create(
                    model="grok-3-beta",
                    messages=[{"role": "user", "content": prompt + "\n\n" + content}]
                )
                logger.info("xAI analysis complete. Response received.")
                logger.debug(f"xAI response preview: {completion.choices[0].message.content[:200]}")
                return completion.choices[0].message.content
            except Exception as e:
                logger.error(f"Error calling xAI API: {str(e)}")
                return f"[xAI API error: {str(e)}]"
        else:
            logger.info("[SIMULATION] Would send prompt and content to xAI here...")
            # Simulate a response
            return "# xAI 回應（這裡是範例）\n- 市場情緒：[多頭]\n- 產業名稱：[半導體, AI]\n- 摘要：多數討論看好美國科技股，部分關注半導體產業。"

    def save_analysis(self, analysis: str, output_file: Path, analyzed_date: str, analysis_time: str):
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# PTT Stock Sentiment Analysis\n")
                f.write(f"- 分析目標日期 (Target Day): {analyzed_date}\n")
                f.write(f"- 分析執行時間 (Analysis Time): {analysis_time}\n\n")
                f.write(analysis)
            logger.info(f"Analysis saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving analysis: {str(e)}")


def find_latest_csv() -> Path:
    files = glob.glob(CSV_PATTERN)
    if not files:
        raise FileNotFoundError("No CSV files found matching pattern.")
    latest = max(files, key=os.path.getmtime)
    return Path(latest)

def extract_target_date_and_timestamp(filename: Path) -> (str, str):
    # e.g. ptt_stock_articles_04-16.csv or ptt_stock_articles_04-14_20250415-2203.csv
    # If timestamp is not in filename, attempts to read scan time from the CSV meta line.
    base = filename.name
    parts = base.split('_')
    if len(parts) >= 5:
        target_date = parts[3]
        timestamp = parts[4].replace('.csv', '')
    elif len(parts) >= 4:
        # Handles ptt_stock_articles_04-16.csv
        target_date = parts[3].replace('.csv', '')
        # Try to read scan time from meta in the CSV file
        timestamp = ""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                while True:
                    line = f.readline()
                    if not line:
                        break
                    if line.startswith('# scanned_at:'):
                        timestamp = line.strip().split(':', 1)[1].strip().replace(' ', '_').replace(':', '')
                        break
                    if not line.startswith('#'):
                        break
        except Exception:
            timestamp = ""
    else:
        target_date = 'Unknown'
        timestamp = ""
    return target_date, timestamp

def find_previous_md(target_date):
    """Find the previous day's markdown output in analysis/ directory."""
    analysis_dir = Path('analysis')
    try:
        # Parse target_date (e.g., '04-16') to get previous day
        prev_date = datetime.strptime(target_date, '%m-%d') - timedelta(days=1)
        prev_date_str = prev_date.strftime('%m-%d')
        # Find files matching previous day
        candidates = sorted(analysis_dir.glob(f"ptt_stock_sentiment_{prev_date_str}_*.md"), reverse=True)
        if candidates:
            return candidates[0]
    except Exception as e:
        logger.warning(f"Could not determine previous day's file: {e}")
    return None

def main():
    parser = argparse.ArgumentParser(description="PTT Stock Sentiment Analyzer (xAI)")
    parser.add_argument('--csv', type=Path, help="Path to the PTT stock articles CSV (default: latest)")
    parser.add_argument('--output', type=Path, help="Path to the output markdown file (optional)")
    parser.add_argument('--remove-csv', action='store_true', help="Remove the CSV file after analysis.")
    parser.add_argument('--sanitize-csv', action='store_true', help="Sanitize the CSV file after analysis (remove content, keep title/date/url).")
    args = parser.parse_args()

    # Find latest CSV if not specified
    if args.csv:
        csv_file = args.csv
    else:
        csv_file = find_latest_csv()

    target_date, timestamp = extract_target_date_and_timestamp(csv_file)
    out_dir = 'analysis'
    os.makedirs(out_dir, exist_ok=True)
    output_file = args.output if args.output else Path(out_dir) / f"ptt_stock_sentiment_{target_date}_{timestamp}.md"

    # For metadata
    analyzed_date = target_date
    analysis_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    analyzer = PTTStockSentimentAnalyzer()
    prompt = analyzer.read_prompt()

    # Add previous day's summary if available
    prev_md = find_previous_md(target_date)
    prev_summary = ''
    if prev_md and prev_md.exists():
        with open(prev_md, 'r', encoding='utf-8') as f:
            prev_summary = f.read()
        prompt = (f"【前一日分析摘要】\n" + prev_summary + "\n\n" + prompt)
    else:
        logger.info("No previous day's summary found or file missing.")

    articles = analyzer.read_articles(csv_file)
    xai_input = analyzer.prepare_xai_input(articles)
    analysis = analyzer.analyze_article(prompt, xai_input)
    analyzer.save_analysis(analysis, output_file, analyzed_date, analysis_time)

    # Remove the full article file if requested
    if args.remove_csv:
        try:
            subprocess.run([
                sys.executable, str(Path(__file__).parent / 'remove_full_article.py'), str(csv_file)
            ], check=True)
        except Exception as e:
            logger.error(f"Failed to remove CSV file: {e}")

    # Sanitize the article file if requested
    if args.sanitize_csv:
        try:
            subprocess.run([
                sys.executable, str(Path(__file__).parent / 'sanitize_full_article.py'), str(csv_file)
            ], check=True)
        except Exception as e:
            logger.error(f"Failed to sanitize CSV file: {e}")

if __name__ == "__main__":
    main()
