#!/usr/bin/env python3
"""
Ré-extraction ciblée — Médias, les nouveaux GUIGNOLS ? Bruno Gaccio
YouTube: https://www.youtube.com/watch?v=TFk_w_N2xXM
"""

import json, re, os, unicodedata, time
from youtube_transcript_api import YouTubeTranscriptApi

OUTPUT_JSON = '/Users/tjegousse/Downloads/thinkerbooks/data/verbatims.json'
WINDOW_SECS = 120
CUTOFF = 0.80  # chercher dans les 20% finaux

EPISODE = {
    "title": "Médias, les nouveaux GUIGNOLS ? Bruno Gaccio",
    "youtube": "https://www.youtube.com/watch?v=TFk_w_N2xXM",
    "books": [
        {"title": "Manuel indocile de sciences sociales", "author": "FONDATION COPERNIC"},
        {"title": "Et l'homme créa les dieux", "author": "Pascal Boyer"},
        {"title": "Qui a tué mon père", "author": "Édouard Louis"},
    ]
}

def normalize(s):
    s = s.lower().strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r"[''\"«»]", ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s

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

def find_mention(full_text, offsets, keywords, window_secs, cutoff=0.80):
    if offsets:
        last_sec = offsets[-1][0]
        cutoff_sec = last_sec * cutoff
        print(f"    Durée vidéo: {last_sec:.0f}s, recherche après {cutoff_sec:.0f}s ({int(cutoff*100)}%)")
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
            words = [w for w in norm_kw.split() if len(w) > 4]
            if len(words) >= 2:
                pattern = r'\b' + r'.{0,30}'.join(re.escape(w) for w in words[:2]) + r'\b'
                m = re.search(pattern, norm_text)
                if m:
                    idx = m.start()
                    kw = f"{kw} (fuzzy)"
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

        print(f"    → Trouvé à {mention_sec:.0f}s pour: {kw!r}")
        start_sec = max(0, mention_sec - window_secs // 3)
        end_sec = mention_sec + window_secs
        passage_parts = []
        for i, (sec, char_off) in enumerate(offsets):
            if start_sec <= sec <= end_sec:
                next_off = offsets[i+1][1] if i+1 < len(offsets) else len(full_text)
                passage_parts.append(full_text[char_off:next_off])
        return ' '.join(passage_parts).strip(), mention_sec

    return None, None

def main():
    with open(OUTPUT_JSON) as f:
        verbatims = json.load(f)

    vid_id = "TFk_w_N2xXM"
    print(f"Téléchargement transcription {vid_id}...")
    segments = fetch_transcript(vid_id)
    full_text, offsets = full_text_with_time(segments)
    print(f"{len(segments)} segments, {len(full_text)} caractères")

    print(f"\n--- Fin de transcription ---")
    print(full_text[-500:])
    print()

    for book in EPISODE["books"]:
        title = book["title"]
        author = book["author"]
        key = f"{title}||{author}"

        keywords = [title, author]
        title_words = [w for w in title.split() if len(w) > 5]
        if title_words:
            keywords.append(' '.join(title_words[:3]))

        print(f"\nRecherche: {title} ({author})")

        passage, mention_sec = find_mention(full_text, offsets, keywords, WINDOW_SECS, CUTOFF)

        if not passage:
            print(f"  → Non trouvé dans les {int((1-CUTOFF)*100)}% finaux")
            verbatims[key] = {"episode": EPISODE["title"], "found": False, "verbatim": None}
            continue

        print(f"  → Passage ({len(passage)} chars):")
        print(f"  {passage[:400]}")

        verbatims[key] = {
            "episode": EPISODE["title"],
            "found": True,
            "mention_sec": int(mention_sec),
            "verbatim": passage,
            "needs_cleaning": True
        }

        with open(OUTPUT_JSON, 'w') as f:
            json.dump(verbatims, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Passages bruts sauvegardés.")

if __name__ == '__main__':
    main()
