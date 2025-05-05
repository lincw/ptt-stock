import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import time
import csv
import argparse
import os
import re

PTT_URL = "https://www.ptt.cc"
BOARD = "/bbs/stock/index.html"
HEADERS = {'User-Agent': 'Mozilla/5.0'}


def get_target_dates(target_date=None):
    if target_date:
        # Accept MM-DD format, convert to various possible date formats
        try:
            dt = datetime.strptime(target_date, '%m-%d')
            # 各種可能的日期格式
            formats = []
            
            # 添加所有可能的格式
            formats.append(f"{dt.month:02d}/{dt.day:02d}")  # MM/DD - 05/02
            formats.append(f"{dt.month}/{dt.day}")  # M/D - 5/2
            formats.append(f"{dt.month}/{dt.day:02d}")  # M/DD - 5/02
            formats.append(f"{dt.month:02d}/{dt.day}")  # MM/D - 05/2
            
            year = dt.year if dt.year > 1900 else datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).year
        except Exception:
            pad = target_date.replace('-', '/')
            parts = pad.split('/')
            m, d = int(parts[0]), int(parts[1]) if len(parts) == 2 else (0, 0)
            
            formats = []
            formats.append(f"{m:02d}/{d:02d}")  # MM/DD - 05/02
            formats.append(f"{m}/{d}")  # M/D - 5/2
            formats.append(f"{m}/{d:02d}")  # M/DD - 5/02
            formats.append(f"{m:02d}/{d}")  # MM/D - 05/2
            
            year = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).year
        
        # 去除重複的格式
        formats = list(set(formats))
        return formats, year
    else:
        now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
        pad = now.strftime('%m/%d')
        space_pad = f"{now.month}/{now.day}"
        year = now.year
        return pad, space_pad, year


def fetch_page(url):
    resp = requests.get(url, headers=HEADERS, cookies={'over18': '1'})
    resp.raise_for_status()
    return resp.text


def parse_articles(html, today_tuple):
    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    date_formats = today_tuple
    found_dates = set()
    date_entry_map = {}
    
    for entry in soup.select('div.r-ent'):
        date = entry.select_one('div.date').text.strip()
        found_dates.add(date)
        
        # 保存每個日期對應的標題，用於調試
        title_tag = entry.select_one('div.title a')
        title_text = title_tag.text.strip() if title_tag else "(無標題或已刪除)"
        if date not in date_entry_map:
            date_entry_map[date] = []
        date_entry_map[date].append(title_text)
        
        # 檢查日期是否匹配 (使用精確比較)
        is_match = False
        for format in date_formats:
            if date == format:
                is_match = True
                break
        
        if not is_match:
            continue
            
        if not title_tag:
            continue
            
        title = title_tag.text.strip()
        url = PTT_URL + title_tag['href']
        author = entry.select_one('div.author').text.strip()
        articles.append({'title': title, 'url': url, 'author': author, 'date': date})
    
    return articles, found_dates, date_entry_map


def find_prev_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    btn = soup.select_one('div.btn-group-paging a:contains("上頁")')
    if btn:
        return PTT_URL + btn['href']
    return None


def fetch_today_articles(max_pages=10, sleep_sec=1, today_tuple=None):
    url = PTT_URL + BOARD
    if today_tuple is None:
        today_tuple = get_target_dates()[0]
    all_articles = []
    pages_checked = 0
    all_found_dates = set()
    all_date_entry_map = {}
    
    while url and pages_checked < max_pages:
        html = fetch_page(url)
        articles, found_dates, date_entry_map = parse_articles(html, today_tuple)
        # 合併日期-條目映射
        for date, entries in date_entry_map.items():
            if date not in all_date_entry_map:
                all_date_entry_map[date] = []
            all_date_entry_map[date].extend(entries)
            
        all_found_dates.update(found_dates)
        all_articles.extend(articles)  # 使用 extend 的同時也去掉了 if articles 判斷，因為即使空列表也可以合併
            
        url = find_prev_page(html)
        pages_checked += 1
        time.sleep(sleep_sec)
    
    return all_articles, all_found_dates, all_date_entry_map


def fetch_article_content(url):
    html = fetch_page(url)
    soup = BeautifulSoup(html, 'html.parser')
    # Main content: in div#main-content, remove meta and pushes
    main_div = soup.find('div', id='main-content')
    # Remove meta info and pushes
    for tag in main_div.find_all(['div', 'span'], class_=['article-metaline', 'article-metaline-right', 'push']):
        tag.decompose()
    # Remove all script/style
    for tag in main_div(['script', 'style']):
        tag.decompose()
    # Main text
    main_text = main_div.get_text(separator='\n', strip=True)
    # Comments (pushes)
    pushes = soup.find_all('div', class_='push')
    comments = []
    for push in pushes:
        tag = push.find('span', class_='push-tag')
        user = push.find('span', class_='push-userid')
        content = push.find('span', class_='push-content')
        if tag and user and content:
            comments.append(f"{tag.text.strip()} {user.text.strip()} {content.text.strip()}")
    comments_text = '\n'.join(comments)
    return main_text, comments_text


def clean_article_content(raw_content, max_length=2000, url=None):
    import re
    # Split into main and reply (after '--')
    parts = raw_content.split('--\n', 1)
    main = parts[0]
    reply = parts[1] if len(parts) > 1 else ''

    # Deduplicate lines in main
    main_lines = main.splitlines()
    seen_main = set()
    unique_main = []
    for line in main_lines:
        lstripped = line.strip()
        # Remove lines like '網址：...' or '文章網址：...' (with or without colon)
        if re.match(r'^(網址|文章網址)[:：]?\s*https?://', lstripped):
            continue
        # Remove if line is exactly the article URL
        if url and lstripped == url:
            continue
        if lstripped and lstripped not in seen_main:
            unique_main.append(lstripped)
            seen_main.add(lstripped)
    
    # Deduplicate lines in reply, and remove signature lines (e.g., '※ 發信站:')
    reply_lines = reply.splitlines()
    seen_reply = set()
    unique_reply = []
    for line in reply_lines:
        lstripped = line.strip()
        if lstripped.startswith('※ 發信站:') or lstripped.startswith('◆ From:') or lstripped == '':
            continue  # Remove signature and empty lines
        if lstripped and lstripped not in seen_reply:
            unique_reply.append(lstripped)
            seen_reply.add(lstripped)
    
    # Recombine, collapse multiple newlines, remove empty lines
    cleaned = '\n'.join(unique_main)
    if unique_reply:
        cleaned += '\n--\n' + '\n'.join(unique_reply)
    # Collapse multiple consecutive newlines
    cleaned = re.sub(r'(\\n|\n){2,}', '\n', cleaned)
    cleaned = cleaned.strip()
    # Limit to max_length characters
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + '\n...（已截斷）'
    return cleaned


def main():
    parser = argparse.ArgumentParser(description='PTT Stock Board Scraper')
    parser.add_argument('--date', type=str, help='Target date in MM-DD format (e.g., 04-14). Defaults to today (Taiwan time).')
    parser.add_argument('--max-pages', type=int, default=20, help='Maximum number of pages to crawl (default: 20)')
    args = parser.parse_args()

    date_formats, year = get_target_dates(args.date)
    today_tuple = date_formats
    target_date_str = args.date if args.date else datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime('%m-%d')
    out_dir = 'articles'
    os.makedirs(out_dir, exist_ok=True)
    out_filename = os.path.join(out_dir, f"ptt_stock_articles_{target_date_str}.csv")

    articles, found_dates, date_entry_map = fetch_today_articles(today_tuple=today_tuple, max_pages=args.max_pages)
    
    # 只展示會保存的文章
    for art in articles:
        print(f"[{year}/{art['date']}] {art['title']} ({art['author']}) -> {art['url']}")
    # Fetch content for each article
    for art in articles:
        content, comments = fetch_article_content(art['url'])
        art['content'] = clean_article_content(content, url=art['url']).replace('\n', '\\n').replace('\r', '')
        art['comments'] = comments.replace('\n', '\\n').replace('\r', '')
        art['year'] = year
    if articles:
        scan_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
        with open(out_filename, 'w', newline='', encoding='utf-8') as csvfile:
            csvfile.write(f"# scanned_at: {scan_time}\n")
            writer = csv.DictWriter(
                csvfile,
                fieldnames=['year', 'date', 'title', 'author', 'url', 'content', 'comments'],
                quoting=csv.QUOTE_ALL
            )
            writer.writeheader()
            writer.writerows(articles)
        print(f"Saved {len(articles)} articles to {out_filename}")
    else:
        print(f"No articles found to save. (Checked up to {args.max_pages} pages)")


if __name__ == "__main__":
    main()
