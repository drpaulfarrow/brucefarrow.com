"""Fetch the voidX744 YouTube feed and write it to videos.json.

Run by .github/workflows/update-videos.yml so the page never has to fetch the
feed from the visitor's browser. If the feed can't be fetched or parsed, the
existing videos.json is left untouched so the site keeps the last good list.
"""
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

CHANNEL_ID = 'UCNZva9pv563Hc85ibd7O2UQ'
FEED_URL = f'https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}'
OUT_FILE = 'videos.json'
NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'yt': 'http://www.youtube.com/xml/schemas/2015',
    'media': 'http://search.yahoo.com/mrss/',
}


def fetch(url, attempts=4):
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (brucefarrow.com feed updater)'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception as err:
            print(f'Attempt {i + 1} failed: {err}', file=sys.stderr)
            if i < attempts - 1:
                time.sleep(5 * 2 ** i)
    return None


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    videos = []
    for entry in root.findall('atom:entry', NS):
        video_id = entry.findtext('yt:videoId', default='', namespaces=NS).strip()
        if not video_id:
            continue
        thumb = entry.find('media:group/media:thumbnail', NS)
        videos.append({
            'id': video_id,
            'title': entry.findtext('atom:title', default='', namespaces=NS).strip(),
            'published': entry.findtext('atom:published', default='', namespaces=NS).strip(),
            'thumbnail': thumb.get('url') if thumb is not None else None,
        })
    return videos


def main():
    raw = fetch(FEED_URL)
    if raw is None:
        print('Could not fetch feed; keeping existing videos.json', file=sys.stderr)
        return
    try:
        videos = parse(raw)
    except ET.ParseError as err:
        print(f'Could not parse feed ({err}); keeping existing videos.json', file=sys.stderr)
        return
    if not videos:
        print('Feed had no videos; keeping existing videos.json', file=sys.stderr)
        return
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'videos': videos}, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'Wrote {len(videos)} videos to {OUT_FILE}')


if __name__ == '__main__':
    main()
