#!/usr/bin/env python3
"""
Extrait les verbatims Thinkerview par livre depuis les transcriptions YouTube.
Etape 1 : récupère la transcription
Etape 2 : cherche les mentions du livre dans les 20% finaux (recos toujours à la fin)
Etape 3 : extrait une fenêtre de ~120s autour de chaque mention
Etape 4 : sauvegarde dans verbatims.json (needs_cleaning=True pour nettoyage ultérieur)
"""

import json, re, os, unicodedata, time
from youtube_transcript_api import YouTubeTranscriptApi

# ── CONFIG ──────────────────────────────────────────────────────────────────
EPISODES_JSON = '/Users/tjegousse/Downloads/thinkerbooks/data/episodes.json'
OUTPUT_JSON   = '/Users/tjegousse/Downloads/thinkerbooks/data/verbatims.json'
WINDOW_SECS   = 120   # secondes de contexte autour de la mention
MAX_EPISODES  = 999   # tous les épisodes
CUTOFF        = 0.80  # chercher dans les 20% finaux — recos toujours à la fin

# ── HELPERS ─────────────────────────────────────────────────────────────────
def normalize(s):
    s = s.lower().strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r"[''\"«»]", ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s

def extract_video_id(url):
    m = re.search(r'v=([\w-]+)', url)
    return m.group(1) if m else None

def fetch_transcript(video_id):
    api = YouTubeTranscriptApi()
    tl = api.list(video_id)
    t = tl.find_transcript(['fr'])
    segments = list(t.fetch())
    return [{'start': s.start, 'duration': s.duration, 'text': s.text} for s in segments]

def full_text_with_time(segments):
    parts, offsets = [], []
    pos = 0
    for seg in segments:
        offsets.append((seg['start'], pos))
        parts.append(seg['text'])
        pos += len(seg['text']) + 1
    return ' '.join(parts), offsets

def find_mention(full_text, offsets, keywords, window_secs):
    """Cherche la première mention d'un keyword dans les derniers 20% de la vidéo."""
    if offsets:
        last_sec = offsets[-1][0]
        cutoff_sec = last_sec * CUTOFF
        start_char = next((char_off for (sec, char_off) in offsets if sec >= cutoff_sec), 0)
    else:
        start_char = 0

    search_text = full_text[start_char:]
    norm_text = normalize(search_text)

    for kw in keywords:
        norm_kw = normalize(kw)
        if len(norm_kw) < 3:
            continue
        idx = norm_text.find(norm_kw)
        if idx == -1:
            # Essaie mot par mot (au moins 2 mots significatifs > 4 chars)
            words = [w for w in norm_kw.split() if len(w) > 4]
            if len(words) >= 2:
                pattern = r'\b' + r'.{0,30}'.join(re.escape(w) for w in words[:2]) + r'\b'
                m = re.search(pattern, norm_text)
                if m:
                    idx = m.start()
        if idx == -1:
            continue

        abs_idx = start_char + idx
        mention_sec = None
        for (sec, char_off) in reversed(offsets):
            if char_off <= abs_idx:
                mention_sec = sec
                break
        if mention_sec is None:
            continue

        start_sec = max(0, mention_sec - window_secs // 3)
        end_sec = mention_sec + window_secs
        passage_parts = []
        for i, (sec, char_off) in enumerate(offsets):
            if start_sec <= sec <= end_sec:
                next_off = offsets[i+1][1] if i+1 < len(offsets) else len(full_text)
                passage_parts.append(full_text[char_off:next_off])
        passage = ' '.join(passage_parts).strip()
        return passage, mention_sec

    return None, None

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    with open(EPISODES_JSON) as f:
        episodes = json.load(f)

    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON) as f:
            verbatims = json.load(f)
    else:
        verbatims = {}

    total = len(episodes[:MAX_EPISODES])
    found_count = sum(1 for v in verbatims.values() if v.get('found'))
    print(f"Départ : {found_count} verbatims trouvés, {total} épisodes à traiter\n")

    for i, ep in enumerate(episodes[:MAX_EPISODES]):
        print(f"[{i+1}/{total}] {ep['title']}")
        vid_id = extract_video_id(ep.get('youtube', ''))
        if not vid_id:
            print("  → Pas d'URL YouTube, skip")
            continue

        all_keys = [f"{b['title']}||{b['author']}" for b in ep['books']]
        # Skip si tous les livres ont déjà un verbatim trouvé (ou ont été cherchés)
        already_done = [k for k in all_keys if k in verbatims and verbatims[k].get('verbatim') is not None]
        not_found = [k for k in all_keys if k in verbatims and verbatims[k].get('found') is False and verbatims[k].get('verbatim') is None]
        missing = [k for k in all_keys if k not in verbatims]

        if not missing and not already_done and len(not_found) == len(all_keys):
            # Tous déjà marqués not-found, on peut re-tenter
            pass
        elif all_keys and not missing and len(already_done) + len(not_found) == len(all_keys):
            print(f"  → Déjà complet ({len(already_done)} trouvés, {len(not_found)} non trouvés), skip")
            continue

        print(f"  → Téléchargement transcription...")
        try:
            segments = fetch_transcript(vid_id)
        except Exception as e:
            print(f"  → Erreur: {e}")
            continue

        full_text, offsets = full_text_with_time(segments)
        last_sec = offsets[-1][0] if offsets else 0
        print(f"  → {len(segments)} segments, durée ~{last_sec:.0f}s, cutoff à {last_sec*CUTOFF:.0f}s")

        for book in ep['books']:
            title  = book['title']
            author = book['author']
            key    = f"{title}||{author}"

            # Skip seulement si on a déjà un vrai verbatim
            if verbatims.get(key, {}).get('verbatim'):
                print(f"  SKIP (déjà trouvé): {title}")
                continue

            keywords = [title, author]
            title_words = [w for w in title.split() if len(w) > 5]
            if title_words:
                keywords.append(' '.join(title_words[:3]))

            passage, mention_sec = find_mention(full_text, offsets, keywords, WINDOW_SECS)

            if not passage:
                print(f"  [{title[:40]}] → non trouvé dans les {int((1-CUTOFF)*100)}% finaux")
                verbatims[key] = {"episode": ep['title'], "found": False, "verbatim": None}
            else:
                print(f"  [{title[:40]}] → trouvé à {mention_sec:.0f}s ({len(passage)} chars)")
                verbatims[key] = {
                    "episode": ep['title'],
                    "found": True,
                    "mention_sec": int(mention_sec),
                    "verbatim": passage,
                    "needs_cleaning": True
                }

            with open(OUTPUT_JSON, 'w') as f:
                json.dump(verbatims, f, ensure_ascii=False, indent=2)

    found_count = sum(1 for v in verbatims.values() if v.get('found'))
    print(f"\n✅ Terminé. {found_count} verbatims trouvés / {len(verbatims)} livres traités")

if __name__ == '__main__':
    main()
