"""Fetch the voidX744 YouTube feed and write it to videos.json.

Run by .github/workflows/update-videos.yml so the page never has to fetch the
feed from the visitor's browser. If the feed can't be fetched or parsed, the
existing videos.json is left untouched so the site keeps the last good list.

Each video gets a short magazine-style "blurb". Blurbs already in videos.json
are kept; new videos get one written by Claude when ANTHROPIC_API_KEY is set,
and are simply left without one otherwise.
"""
import json
import os
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


BLURB_PROMPT = """You write the captions for a fun gaming and sport magazine page that \
showcases a young YouTuber's short videos (mostly Fortnite clips, Zelda: Tears of \
the Kingdom tutorials and football edits).

Write one magazine-style blurb for the video below: one or two punchy sentences, \
under 30 words, family-friendly, excited but not over the top. Only describe what \
the title, hashtags and description actually suggest; don't invent specific events, \
scores or people. No hashtags, no emoji, no quotation marks. Reply with the blurb only.

Title: {title}
YouTube description: {description}"""


def write_blurb(client, video):
    response = client.beta.messages.create(
        model='claude-opus-5-5',
        max_tokens=2000,
        output_config={'effort': 'low'},
        betas=['server-side-fallback-2026-07-01'],
        fallbacks='default',
        messages=[{'role': 'user', 'content': BLURB_PROMPT.format(
            title=video['title'],
            description=video.get('description') or '(none)',
        )}],
    )
    if response.stop_reason != 'end_turn':
        print(f"No blurb for {video['id']}: stop_reason={response.stop_reason}", file=sys.stderr)
        return None
    text = ''.join(b.text for b in response.content if b.type == 'text').strip()
    return text or None


def add_blurbs(videos):
    """Fill in missing blurbs with Claude; failures just leave a video without one."""
    missing = [v for v in videos if not v.get('blurb')]
    if not missing:
        return
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print(f'{len(missing)} videos have no blurb; set ANTHROPIC_API_KEY to generate them', file=sys.stderr)
        return
    import anthropic
    client = anthropic.Anthropic()
    for video in missing:
        try:
            video['blurb'] = write_blurb(client, video)
        except anthropic.APIError as err:
            print(f"Blurb failed for {video['id']}: {err}", file=sys.stderr)


def load_existing():
    try:
        with open(OUT_FILE, encoding='utf-8') as f:
            return {v['id']: v for v in json.load(f).get('videos', [])}
    except (OSError, ValueError):
        return {}


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    videos = []
    for entry in root.findall('atom:entry', NS):
        video_id = entry.findtext('yt:videoId', default='', namespaces=NS).strip()
        if not video_id:
            continue
        thumb = entry.find('media:group/media:thumbnail', NS)
        description = entry.findtext('media:group/media:description', default='', namespaces=NS).strip()
        videos.append({
            'id': video_id,
            'title': entry.findtext('atom:title', default='', namespaces=NS).strip(),
            'published': entry.findtext('atom:published', default='', namespaces=NS).strip(),
            'thumbnail': thumb.get('url') if thumb is not None else None,
            'description': description,
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
    existing = load_existing()
    for video in videos:
        video['blurb'] = existing.get(video['id'], {}).get('blurb')
    add_blurbs(videos)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'videos': videos}, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'Wrote {len(videos)} videos to {OUT_FILE}')


if __name__ == '__main__':
    main()
