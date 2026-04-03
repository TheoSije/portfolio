#!/usr/bin/env python3
"""
Compile ThinkerBooks episodes from the Thinkerview README to a pre-built JSON file.
Mirrors the parseReadme() logic from thinkerbooks/index.html.
"""

import re
import json
import urllib.request
import os

README_URL = 'https://raw.githubusercontent.com/sebastienp7669/Thinkerview-Recommandations-lecture/master/README.md'
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'thinkerbooks', 'data', 'episodes.json')

IGNORE_TITLES = {'oeuvre', 'oeuvres', 'livre', 'livres', 'ouvrage', 'ouvrages', "l'oeuvre", "l'oeuvres"}


def clean_book_text(text):
    """Mirror of cleanBookText() in JS: strip markdown links, bold/italic markers, trim."""
    # Replace [text](url) with text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove **, _, *
    text = text.replace('**', '').replace('_', '').replace('*', '')
    return text.strip()


def parse_book_line(raw):
    """
    Parse a book line (after stripping the leading '- ').
    Returns {'title': str, 'author': str or ''}.
    Mirrors JS parseReadme() book-parsing logic.
    """
    text = clean_book_text(raw)

    if not text:
        return None

    # Ignore "pas de recommandation" lines
    if re.search(r'pas de recommandation', text, re.IGNORECASE):
        return None

    author = ''
    title = text

    # Pattern 1: dash separator " - UPPERCASE_AUTHOR"
    # e.g. "Le Livre - DUPONT Jean"
    dash_match = re.search(r'\s-\s([A-ZÁÀÂÄÉÈÊËÎÏÔÖÙÛÜ][A-ZÁÀÂÄÉÈÊËÎÏÔÖÙÛÜ\s\-]+)$', text)
    if dash_match:
        candidate_author = dash_match.group(1).strip()
        # Only use if what's before the dash is a reasonable title
        before = text[:dash_match.start()].strip()
        if before:
            title = before
            author = candidate_author
            return {'title': title, 'author': author}

    # Pattern 2: "Titre de/par Auteur" — but not if word before "de" is a generic word
    de_match = re.match(
        r'^(.+?)\s+(?:de|par)\s+([A-ZÁÀÂÄÉÈÊËÎÏÔÖÙÛÜ][^\n]+)$',
        text
    )
    if de_match:
        before = de_match.group(1).strip()
        after = de_match.group(2).strip()
        # Check that the word immediately before "de/par" is not a generic title word
        last_word = before.split()[-1].lower().strip("'") if before.split() else ''
        if last_word not in IGNORE_TITLES:
            title = before
            author = after
            return {'title': title, 'author': author}

    return {'title': title, 'author': ''}


def parse_readme(text):
    """
    Parse the README markdown into a list of episode dicts.
    Mirrors parseReadme() in JS.
    """
    episodes = []

    # Split into blocks on lines starting with "### "
    blocks = re.split(r'\n(?=### )', text)

    for block in blocks:
        lines = block.split('\n')
        if not lines:
            continue

        # Extract episode title from first "### " line
        first_line = lines[0].strip()
        if not first_line.startswith('### '):
            continue
        ep_title = first_line[4:].strip()

        # Extract date (line starting with "> " followed by a digit)
        date = ''
        for line in lines:
            m = re.match(r'^>\s*(\d.+)', line)
            if m:
                date = m.group(1).strip()
                break

        # Extract YouTube URL
        youtube = ''
        for line in lines:
            m = re.search(r'(https?://(?:www\.)?youtube\.com/watch\S+)', line)
            if m:
                youtube = m.group(1).strip()
                break

        # Extract books from "- " lines
        books = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- '):
                raw = stripped[2:].strip()
                book = parse_book_line(raw)
                if book:
                    books.append(book)

        # Only include episodes with at least one book
        if books:
            episodes.append({
                'title': ep_title,
                'date': date,
                'youtube': youtube,
                'books': books,
            })

    return episodes


def main():
    print(f'Fetching README from {README_URL} ...')
    with urllib.request.urlopen(README_URL) as resp:
        text = resp.read().decode('utf-8')

    print('Parsing ...')
    episodes = parse_readme(text)

    total_books = sum(len(ep['books']) for ep in episodes)
    print(f'Found {len(episodes)} episodes, {total_books} books total.')

    output_path = os.path.abspath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)

    print(f'Written to {output_path}')


if __name__ == '__main__':
    main()
