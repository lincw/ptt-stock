"""
Sanitize a PTT article CSV: keep only year, date, title, url columns. Remove all others (author, content, comments).
"""
import csv
import logging
from pathlib import Path
import sys

def sanitize_csv(file_path):
    file = Path(file_path)
    if not file.exists():
        logging.error(f"File not found: {file_path}")
        return
    temp_file = file.with_suffix('.sanitized.csv')
    keep_fields = ['year', 'date', 'title', 'url']
    try:
        with open(file, 'r', encoding='utf-8') as fin, open(temp_file, 'w', encoding='utf-8', newline='') as fout:
            # Skip meta/comment lines
            while True:
                pos = fin.tell()
                line = fin.readline()
                if not line:
                    break
                if not line.startswith('#'):
                    fin.seek(pos)
                    break
            reader = csv.DictReader(fin)
            writer = csv.DictWriter(fout, fieldnames=keep_fields, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in reader:
                sanitized = {k: row[k] for k in keep_fields}
                writer.writerow(sanitized)
        file.unlink()
        temp_file.rename(file)
        logging.info(f"Sanitized file (columns removed): {file_path}")
    except Exception as e:
        logging.error(f"Failed to sanitize {file_path}: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sanitize a PTT article CSV: keep only year, date, title, url columns.")
    parser.add_argument("file_path", type=str, help="Path to the file to sanitize.")
    args = parser.parse_args()
    sanitize_csv(args.file_path)
