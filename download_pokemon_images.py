#!/usr/bin/env python3
"""
Download Pokemon card images from scrydex.com.
Images saved to ~/pokemon_card_images/{set_id}/{card_id}.jpg
Skips existing files. Rate-limited to avoid overloading the server.
"""

import os
import sys
import time
import json
import psycopg2
import requests
from pathlib import Path

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
OUTPUT_DIR = Path.home() / 'pokemon_card_images'
DELAY = 0.3  # seconds between downloads
TIMEOUT = 15


def download_image(url: str, dest: Path) -> bool:
    """Download a single image. Returns True on success."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  FAIL {url}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dbname', default='future_sight')
    parser.add_argument('--user', default=os.environ.get('USER', 'clawdbot1'))
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default='5432')
    parser.add_argument('--set', help='Only download this set (e.g. sv1)')
    parser.add_argument('--limit', type=int, help='Max cards to download (for testing)')
    parser.add_argument('--delay', type=float, default=DELAY, help='Delay between downloads (seconds)')
    args = parser.parse_args()

    conn = psycopg2.connect(host=args.host, port=args.port, dbname=args.dbname, user=args.user)
    c = conn.cursor()

    query = """
        SELECT id, set_id, image_url
        FROM pokemon_cards
        WHERE image_url IS NOT NULL
    """
    params = []
    if args.set:
        query += " AND set_id = %s"
        params.append(args.set)
    query += " ORDER BY set_id, number"
    if args.limit:
        query += f" LIMIT {args.limit}"

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    total = len(rows)
    print(f"Cards to download: {total}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    downloaded = 0
    skipped = 0
    failed = 0
    current_set = None

    for i, (card_id, set_id, image_url) in enumerate(rows):
        dest = OUTPUT_DIR / set_id / f"{card_id}.jpg"

        if dest.exists():
            skipped += 1
            continue

        if set_id != current_set:
            current_set = set_id
            print(f"\n[{set_id}]")

        success = download_image(image_url, dest)
        if success:
            downloaded += 1
            print(f"  {card_id}", end='\r')
        else:
            failed += 1

        if (i + 1) % 50 == 0:
            print(f"\n  Progress: {i+1}/{total} | Downloaded: {downloaded} | Skipped: {skipped} | Failed: {failed}")

        time.sleep(args.delay)

    print(f"\n\n=== Done ===")
    print(f"Total:      {total}")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped:    {skipped} (already existed)")
    print(f"Failed:     {failed}")


if __name__ == '__main__':
    main()
