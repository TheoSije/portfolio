#!/usr/bin/env python3
"""Download book covers for ThinkerBooks — parallel version."""

import os, re, json, unicodedata, hashlib, threading
import urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

README_URL  = 'https://raw.githubusercontent.com/sebastienp7669/Thinkerview-Recommandations-lecture/master/README.md'
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), '..', 'img', 'thinkerbooks')
MANIFEST    = os.path.join(OUTPUT_DIR, 'covers.json')
WORKERS     = 20

os.makedirs(OUTPUT_DIR, exist_ok=True)

manifest_lock = threading.Lock()

# ── helpers ────────────────────────────────────────────────────────────────

def clean(s):
    if not s: return ''
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
    s = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', s)
    s = s.replace('`', '')
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s)
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
    last = author.strip().split()[-1] if author.strip() else ''

    # 1) Google Books — titre + auteur
    q = f'intitle:{title}'
    if last: q += f'+inauthor:{last}'
    data = safe_json(f'https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(q)}&maxResults=3')
    if data and data.get('items'):
        links = data['items'][0].get('volumeInfo', {}).get('imageLinks', {})
        thumb = links.get('thumbnail') or links.get('smallThumbnail')
        if thumb:
            return thumb.replace('http://', 'https://').replace('zoom=1', 'zoom=2').replace('&edge=curl', '')

    # 2) Google Books — titre seul
    data = safe_json(f'https://www.googleapis.com/books/v1/volumes?q=intitle:{urllib.parse.quote(title)}&maxResults=3')
    if data and data.get('items'):
        links = data['items'][0].get('volumeInfo', {}).get('imageLinks', {})
        thumb = links.get('thumbnail') or links.get('smallThumbnail')
        if thumb:
            return thumb.replace('http://', 'https://').replace('zoom=1', 'zoom=2').replace('&edge=curl', '')

    # 3) Open Library — titre + auteur
    q2 = urllib.parse.quote(f'{title} {author}'.strip())
    data2 = safe_json(f'https://openlibrary.org/search.json?q={q2}&limit=1&fields=cover_i')
    if data2 and data2.get('docs'):
        cid = data2['docs'][0].get('cover_i')
        if cid: return f'https://covers.openlibrary.org/b/id/{cid}-M.jpg'

    # 4) Open Library — titre seul
    data3 = safe_json(f'https://openlibrary.org/search.json?title={urllib.parse.quote(title)}&limit=1&fields=cover_i')
    if data3 and data3.get('docs'):
        cid = data3['docs'][0].get('cover_i')
        if cid: return f'https://covers.openlibrary.org/b/id/{cid}-M.jpg'

    # 5) BnF (Bibliothèque nationale de France) — excellent pour les livres français
    bnf_q = urllib.parse.quote(f'bib.title adj "{title}"')
    bnf_data = safe_json(
        f'https://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve'
        f'&query={bnf_q}&maximumRecords=1&recordSchema=unimarcxchange', timeout=10
    )
    if bnf_data:
        # BnF returns XML — look for ISBN in response to build cover URL
        import re as _re
        raw_bnf = safe_get(
            f'https://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve'
            f'&query={bnf_q}&maximumRecords=1&recordSchema=unimarcxchange', timeout=10
        )
        if raw_bnf:
            isbn_match = _re.search(rb'<datafield[^>]*tag="010"[^>]*>.*?<subfield[^>]*code="a"[^>]*>([0-9X\-]+)</subfield>', raw_bnf, _re.DOTALL)
            if isbn_match:
                isbn = isbn_match.group(1).decode().replace('-', '').strip()
                if len(isbn) in (10, 13):
                    cover = safe_get(f'https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg')
                    if cover and len(cover) > 1000:
                        return f'https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg'

    return None

# ── worker ─────────────────────────────────────────────────────────────────

counters = {'ok': 0, 'fail': 0, 'skip': 0, 'total': 0}
counters_lock = threading.Lock()

def process_book(args):
    i, b, manifest = args
    title, author, key = b['title'], b['author'], b['key']

    with manifest_lock:
        existing = manifest.get(key, 'MISSING')
    # Skip if already has a local file; retry if null (not found previously)
    if existing != 'MISSING' and existing is not None:
        with counters_lock:
            counters['skip'] += 1
        return None

    cover_url = fetch_cover_url(title, author)

    if not cover_url:
        with manifest_lock:
            manifest[key] = None
        with counters_lock:
            counters['fail'] += 1
        print(f'[{i:4}] NONE  {title[:60]}')
        return None

    h = hashlib.md5(key.encode()).hexdigest()[:6]
    fname = f'{slug(title)}-{h}.jpg'
    fpath = os.path.join(OUTPUT_DIR, fname)

    img = safe_get(cover_url)
    if img and len(img) > 500:
        with open(fpath, 'wb') as f:
            f.write(img)
        with manifest_lock:
            manifest[key] = f'img/thinkerbooks/{fname}'
        with counters_lock:
            counters['ok'] += 1
        print(f'[{i:4}] OK    {title[:55]:55s} → {fname}')
        return key
    else:
        with manifest_lock:
            manifest[key] = None
        with counters_lock:
            counters['fail'] += 1
        print(f'[{i:4}] FAIL  {title[:60]}')
        return None

# ── main ───────────────────────────────────────────────────────────────────

print('Fetching README…')
raw = safe_get(README_URL)
books = parse_readme(raw.decode('utf-8'))
print(f'→ {len(books)} unique books\n')

manifest = {}
if os.path.exists(MANIFEST):
    with open(MANIFEST) as f:
        manifest = json.load(f)

args_list = [(i, b, manifest) for i, b in enumerate(books, 1)]

saved_count = 0
with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    futures = {executor.submit(process_book, a): a for a in args_list}
    for fut in as_completed(futures):
        fut.result()
        with counters_lock:
            total = counters['ok'] + counters['fail'] + counters['skip']
        if total % 50 == 0:
            with manifest_lock:
                with open(MANIFEST, 'w') as f:
                    json.dump(manifest, f, ensure_ascii=False)

with open(MANIFEST, 'w') as f:
    json.dump(manifest, f, ensure_ascii=False)

print(f'\n✓ {counters["ok"]} covers downloaded  ✗ {counters["fail"]} not found  → {counters["skip"]} skipped')
print(f'Manifest: {MANIFEST}')
