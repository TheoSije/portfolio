#!/usr/bin/env python3
"""
Ré-extraction ciblée des verbatims pour l'épisode Bruno Gaccio "La satire avant la guerre ?"
YouTube: https://www.youtube.com/watch?v=vJr1PWWvccQ
"""

import json, re, os, unicodedata, time
import anthropic
from youtube_transcript_api import YouTubeTranscriptApi

OUTPUT_JSON = '/Users/tjegousse/Downloads/thinkerbooks/data/verbatims.json'
WINDOW_SECS = 120

EPISODE = {
    "title": "La satire avant la guerre ? Bruno Gaccio",
    "youtube": "https://www.youtube.com/watch?v=vJr1PWWvccQ",
    "books": [
        {"title": "Pour une socioanalyse du journalisme", "author": "Alain Accardo"},
        {"title": "Un jour dans notre vie", "author": "David Fritz Goeppinger"},
        {"title": "Vice", "author": "Laurent Chalumeau"},
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

def find_all_mentions(full_text, offsets, keywords, window_secs):
    """Cherche TOUTES les mentions dans le dernier 50% de la vidéo."""
    if offsets:
        last_sec = offsets[-1][0]
        cutoff_sec = last_sec * 0.50
        print(f"    Durée vidéo: {last_sec:.0f}s, recherche après {cutoff_sec:.0f}s")
        start_char = next((char_off for (sec, char_off) in offsets if sec >= cutoff_sec), 0)
    else:
        start_char = 0

    search_text = full_text[start_char:]
    norm_text = normalize(search_text)
    results = []

    for kw in keywords:
        norm_kw = normalize(kw)
        if len(norm_kw) < 3:
            continue
        search_from = 0
        while True:
            idx = norm_text.find(norm_kw, search_from)
            if idx == -1:
                break
            abs_idx = start_char + idx
            mention_sec = None
            for (sec, char_off) in reversed(offsets):
                if char_off <= abs_idx:
                    mention_sec = sec
                    break
            if mention_sec is not None:
                results.append((mention_sec, kw, idx))
            search_from = idx + 1

        # Essai mot par mot
        if not results:
            words = [w for w in norm_kw.split() if len(w) > 4]
            if len(words) >= 2:
                pattern = r'\b' + r'.{0,30}'.join(re.escape(w) for w in words[:2]) + r'\b'
                for m in re.finditer(pattern, norm_text):
                    abs_idx = start_char + m.start()
                    mention_sec = None
                    for (sec, char_off) in reversed(offsets):
                        if char_off <= abs_idx:
                            mention_sec = sec
                            break
                    if mention_sec is not None:
                        results.append((mention_sec, kw, m.start()))

    if not results:
        return None, None

    # Prend la première mention trouvée
    results.sort(key=lambda x: x[0])
    mention_sec, kw_found, idx = results[0]
    print(f"    → Mention trouvée à {mention_sec:.0f}s pour: {kw_found!r}")

    start_sec = max(0, mention_sec - window_secs // 3)
    end_sec = mention_sec + window_secs
    passage_parts = []
    for i, (sec, char_off) in enumerate(offsets):
        if start_sec <= sec <= end_sec:
            next_off = offsets[i+1][1] if i+1 < len(offsets) else len(full_text)
            passage_parts.append(full_text[char_off:next_off])
    passage = ' '.join(passage_parts).strip()
    return passage, mention_sec

def clean_with_claude(client, episode_title, book_title, book_author, raw_passage):
    prompt = f"""Voici un passage brut d'une transcription YouTube auto-générée de l'émission Thinkerview.
L'épisode est : « {episode_title} »
Le livre mentionné est : « {book_title} » de {book_author or 'auteur inconnu'}.

Transcription brute :
---
{raw_passage}
---

Ta tâche :
1. Corrige les erreurs de transcription automatique (noms propres mal orthographiés, mots coupés, etc.)
2. Retire les hésitations ("euh", "ben", "voilà voilà"), les répétitions inutiles
3. Garde le sens exact et les mots de l'intervenant — ne reformule pas, ne résume pas
4. Retire tout passage hors-sujet qui ne concerne pas le livre
5. Retourne uniquement le texte nettoyé, sans introduction ni commentaire

Si le livre n'est pas clairement mentionné dans ce passage, retourne uniquement: [non trouvé]
"""
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()

def main():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY non défini — nettoyage Claude désactivé")
    client = anthropic.Anthropic(api_key=api_key) if api_key else None

    with open(OUTPUT_JSON) as f:
        verbatims = json.load(f)

    vid_id = "vJr1PWWvccQ"
    print(f"Téléchargement transcription {vid_id}...")
    segments = fetch_transcript(vid_id)
    full_text, offsets = full_text_with_time(segments)
    print(f"{len(segments)} segments, {len(full_text)} caractères")

    # Afficher un aperçu du début et de la fin
    print(f"\n--- Début de transcription ---")
    print(full_text[:300])
    print(f"\n--- Fin de transcription ---")
    print(full_text[-300:])
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
        print(f"  Mots-clés: {keywords}")

        passage, mention_sec = find_all_mentions(full_text, offsets, keywords, WINDOW_SECS)

        if not passage:
            print(f"  → Non trouvé dans le dernier 50%")
            verbatims[key] = {"episode": EPISODE["title"], "found": False, "verbatim": None}
            continue

        print(f"  → Passage brut ({len(passage)} chars):")
        print(f"  {passage[:200]}...")

        if client:
            print(f"  → Nettoyage avec Claude...")
            cleaned = clean_with_claude(client, EPISODE["title"], title, author, passage)
            print(f"  → Nettoyé: {cleaned[:200]}")
            if cleaned.strip() == "[non trouvé]":
                verbatims[key] = {"episode": EPISODE["title"], "found": False, "verbatim": None}
            else:
                verbatims[key] = {
                    "episode": EPISODE["title"],
                    "found": True,
                    "mention_sec": int(mention_sec),
                    "verbatim": cleaned
                }
        else:
            verbatims[key] = {
                "episode": EPISODE["title"],
                "found": True,
                "mention_sec": int(mention_sec),
                "verbatim": passage,
                "needs_cleaning": True
            }

        with open(OUTPUT_JSON, 'w') as f:
            json.dump(verbatims, f, ensure_ascii=False, indent=2)
        time.sleep(1)

    print(f"\n✅ Terminé. Résultats sauvegardés dans {OUTPUT_JSON}")

if __name__ == '__main__':
    main()
