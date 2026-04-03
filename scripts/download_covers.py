#!/usr/bin/env python3
"""Download book covers for ThinkerBooks from Google Books + Open Library."""

import os, re, json, time, unicodedata, hashlib
import urllib.request, urllib.parse, urllib.error

README_URL   = 'https://raw.githubusercontent.com/sebastienp7669/Thinkerview-Recommandations-lecture/master/README.md'
OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), '..', 'img', 'thinkerbooks')
MANIFEST     = os.path.join(OUTPUT_DIR, 'covers.json')
DELAY        = 0.25   # seconds between API calls

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── helpers ────────────────────────────────────────────────────────────────

def clean(s):
    if not s: return ''
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)   # markdown links
    s = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', s)  # bold/italic
    s = s.replace('`', '')
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s)            # trailing parens
    s = re.sub(r'\s*,\s*(dans|extrait|tiré|paru|traduit|trad\.?)\b.*$', '', s, flags=re.I)
    return s.strip()

def slug(s):
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return s[:70]

def safe_get(url, timeout=12):
    req = urllib.request.Request(url, headers={'User-Agent': 'ThinkerBooks/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except:
        return None

def safe_json(url, timeout=12):
    raw = safe_get(url, timeout)
    if not raw: return None
    try: return json.loads(raw)
    except: return None

# ── parse README ───────────────────────────────────────────────────────────

def parse_readme(text):
    books, seen = [], set()
    for block in re.split(r'\n(?=### )', text):
        if not block.strip().startswith('### '): continue
        for line in block.split('\n')[1:]:
            if not line.startswith('- '): continue
            raw = clean(line[2:].strip())
            if not raw or raw.lower() == 'pas de recommandation': continue
            title, author = raw, ''
            m = re.search(r' - ([A-ZÁÀÂÄÉÈÊËÎÏÔÖÙÛÜ])', raw)
            if m:
                title  = clean(raw[:m.start()])
                author = clean(raw[m.start()+3:])
            if not title: continue
            key = title + '||' + author
            if key not in seen:
                seen.add(key)
                books.append({'title': title, 'author': author, 'key': key})
    return books

# ── cover fetching ─────────────────────────────────────────────────────────

def fetch_cover_url(title, author):
    # 1) Google Books
    last = author.strip().split()[-1] if author.strip() else ''
    q = f'intitle:{title}'
    if last: q += f'+inauthor:{last}'
    gb_url = f'https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(q)}&maxResults=3'
    data = safe_json(gb_url)
    if data and data.get('items'):
        links = data['items'][0].get('volumeInfo', {}).get('imageLinks', {})
        thumb = links.get('thumbnail') or links.get('smallThumbnail')
        if thumb:
            return thumb.replace('http://', 'https://').replace('zoom=1', 'zoom=2').replace('&edge=curl', '')

    time.sleep(DELAY)

    # 2) Open Library fallback
    q2 = urllib.parse.quote(f'{title} {author}'.strip())
    ol_url = f'https://openlibrary.org/search.json?q={q2}&limit=1&fields=cover_i'
    data2 = safe_json(ol_url)
    if data2 and data2.get('docs'):
        cid = data2['docs'][0].get('cover_i')
        if cid: return f'https://covers.openlibrary.org/b/id/{cid}-M.jpg'

    return None

# ── main ───────────────────────────────────────────────────────────────────

print('Fetching README…')
raw = safe_get(README_URL)
books = parse_readme(raw.decode('utf-8'))
print(f'→ {len(books)} unique books\n')

# Load existing manifest
manifest = {}
if os.path.exists(MANIFEST):
    with open(MANIFEST) as f:
        manifest = json.load(f)

ok = fail = skip = 0

for i, b in enumerate(books, 1):
    title, author, key = b['title'], b['author'], b['key']

    if key in manifest:
        skip += 1
        print(f'[{i:4}/{len(books)}] SKIP  {title[:60]}')
        continue

    cover_url = fetch_cover_url(title, author)
    time.sleep(DELAY)

    if not cover_url:
        manifest[key] = None
        fail += 1
        print(f'[{i:4}/{len(books)}] NONE  {title[:60]}')
    else:
        # Build filename — use hash suffix to avoid collisions
        h = hashlib.md5(key.encode()).hexdigest()[:6]
        fname = f'{slug(title)}-{h}.jpg'
        fpath = os.path.join(OUTPUT_DIR, fname)

        img = safe_get(cover_url)
        if img and len(img) > 500:
            with open(fpath, 'wb') as f:
                f.write(img)
            manifest[key] = f'img/thinkerbooks/{fname}'
            ok += 1
            print(f'[{i:4}/{len(books)}] OK    {title[:55]:55s} → {fname}')
        else:
            manifest[key] = None
            fail += 1
            print(f'[{i:4}/{len(books)}] FAIL  {title[:60]}')

    # Save every 20 books
    if i % 20 == 0:
        with open(MANIFEST, 'w') as f:
            json.dump(manifest, f, ensure_ascii=False)

# Final save
with open(MANIFEST, 'w') as f:
    json.dump(manifest, f, ensure_ascii=False)

print(f'\n✓ {ok} covers downloaded  ✗ {fail} not found  → {skip} skipped')
print(f'Manifest: {MANIFEST}')
