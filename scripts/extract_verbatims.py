#!/usr/bin/env python3
"""
Extrait les verbatims Thinkerview par livre depuis les transcriptions YouTube.
Etape 1 : récupère la transcription
Etape 2 : cherche les mentions du livre (titre + auteur, fuzzy)
Etape 3 : extrait une fenêtre de ~90s autour de chaque mention
Etape 4 : nettoie avec Claude API
Etape 5 : sauvegarde dans verbatims.json
"""

import json, re, os, unicodedata, time
import anthropic
from youtube_transcript_api import YouTubeTranscriptApi

# ── CONFIG ──────────────────────────────────────────────────────────────────
EPISODES_JSON = os.path.join(os.path.dirname(__file__), '..', 'thinkerbooks', 'data', 'episodes.json')
OUTPUT_JSON   = os.path.join(os.path.dirname(__file__), '..', 'thinkerbooks', 'data', 'verbatims.json')
WINDOW_SECS   = 90   # secondes de contexte autour de la mention
MAX_EPISODES  = 20   # limiter aux N premiers épisodes

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
    """Retourne le texte complet et un index (start_sec → char_offset)."""
    parts = []
    offsets = []
    pos = 0
    for seg in segments:
        offsets.append((seg['start'], pos))
        parts.append(seg['text'])
        pos += len(seg['text']) + 1
    return ' '.join(parts), offsets

def find_mention(full_text, offsets, keywords, window_secs, total_duration):
    """Cherche la première mention d'un keyword dans le dernier tiers, retourne le passage +/- window_secs."""
    # Les recommandations ont lieu à la fin des interviews — on ne cherche que dans le dernier 30%
    if offsets:
        last_sec = offsets[-1][0]
        cutoff_sec = last_sec * 0.70  # on commence à 70% de la durée
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
            # Essaie mot par mot (au moins 2 mots significatifs)
            words = [w for w in norm_kw.split() if len(w) > 4]
            if len(words) >= 2:
                pattern = r'\b' + r'.{0,30}'.join(re.escape(w) for w in words[:2]) + r'\b'
                m = re.search(pattern, norm_text)
                if m:
                    idx = m.start()
        if idx == -1:
            continue
        # idx est relatif à search_text, reconvertir en position absolue dans full_text
        abs_idx = start_char + idx
        # Trouver le timestamp correspondant à abs_idx
        mention_sec = None
        for (sec, char_off) in reversed(offsets):
            if char_off <= abs_idx:
                mention_sec = sec
                break
        if mention_sec is None:
            continue
        # Extraire la fenêtre
        start_sec = max(0, mention_sec - window_secs // 3)
        end_sec   = mention_sec + window_secs
        passage_parts = []
        for seg in [s for s in [{'start': o[0], 'text': full_text[o[1]:offsets[offsets.index(o)+1][1] if offsets.index(o)+1 < len(offsets) else len(full_text)]} for o in offsets]]:
            if start_sec <= seg['start'] <= end_sec:
                passage_parts.append(seg['text'])
        passage = ' '.join(passage_parts).strip()
        return passage, mention_sec
    return None, None

def clean_with_claude(client, episode_title, book_title, book_author, raw_passage):
    """Nettoie la transcription brute avec Claude."""
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
4. Retire tout passage hors-sujet qui ne concerne pas le livre (si le livre n'est mentionné qu'en passant et que le reste est sans rapport, garde uniquement le passage pertinent)
5. Retourne uniquement le texte nettoyé, sans introduction ni commentaire de ta part

Si le livre n'est pas clairement mentionné dans ce passage, retourne uniquement: [non trouvé]
"""
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    client = None  # Claude API non utilisé dans ce mode batch

    with open(EPISODES_JSON) as f:
        episodes = json.load(f)

    # Charger verbatims existants si présents
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON) as f:
            verbatims = json.load(f)
    else:
        verbatims = {}

    for ep in episodes[:MAX_EPISODES]:
        print(f"\n=== {ep['title']} ===")
        vid_id = extract_video_id(ep.get('youtube', ''))
        if not vid_id:
            print("  Pas d'URL YouTube, skip")
            continue

        print(f"  Téléchargement transcription {vid_id}...")
        try:
            segments = fetch_transcript(vid_id)
        except Exception as e:
            print(f"  Erreur transcription: {e}")
            continue

        full_text, offsets = full_text_with_time(segments)
        print(f"  {len(segments)} segments, {len(full_text)} caractères")

        for book in ep['books']:
            title  = book['title']
            author = book['author']
            key    = f"{title}||{author}"

            if key in verbatims:
                print(f"  SKIP (déjà traité): {title}")
                continue

            # Mots-clés à chercher : titre complet, mots du titre, auteur
            keywords = [title, author]
            # Ajoute les mots significatifs du titre (> 5 chars)
            title_words = [w for w in title.split() if len(w) > 5]
            if title_words:
                keywords.append(' '.join(title_words[:3]))

            print(f"  Livre: {title} ({author})")
            passage, mention_sec = find_mention(full_text, offsets, keywords, WINDOW_SECS, len(full_text))

            if not passage:
                print(f"    → Non trouvé dans la transcription")
                verbatims[key] = {"episode": ep['title'], "found": False, "verbatim": None}
                continue

            print(f"    → Trouvé à {mention_sec:.0f}s, passage de {len(passage)} chars")
            verbatims[key] = {
                "episode": ep['title'],
                "found": True,
                "mention_sec": int(mention_sec),
                "verbatim": passage,
                "needs_cleaning": True
            }
            print(f"    → Passage brut sauvegardé (needs_cleaning=True)")

            # Sauvegarde intermédiaire
            with open(OUTPUT_JSON, 'w') as f:
                json.dump(verbatims, f, ensure_ascii=False, indent=2)

            time.sleep(0.5)  # rate limit Claude

    print(f"\nTerminé. {sum(1 for v in verbatims.values() if v.get('found'))} verbatims trouvés / {len(verbatims)} livres traités")
    print(f"Sauvegardé dans {OUTPUT_JSON}")

if __name__ == '__main__':
    main()
