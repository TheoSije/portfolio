# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Théo Jégousse's personal portfolio — [jegousse.com](https://jegousse.com). A single-page site in vanilla HTML/CSS/JS, no framework, no build step, no dependencies. Static hosting (Cloudflare Pages style — see `_headers`, `_redirects`, `CNAME`).

## Running locally

```bash
npx serve .
# or just open index.html in a browser
```

No build, lint, or test commands exist — there's no package.json. Changes are previewed by opening the file directly or serving the directory statically.

## Architecture

`index.html` (~3800 lines, ~180KB) is the entire main app: markup, all CSS-in-`<style>`/external CSS links, and all JS in inline `<script>` tags. Don't expect a component split — search within this one file for the relevant section.

### Mini-sites (Playground projects)
Each Playground project (`incipit/`, `vinyle/`, `unheard/`, `soundhands/`, `chess/`, `emojy/`, `meteomiche/`, `surfcams/`, `inkiphot/`, etc.) is an **independent static site in its own top-level folder**, loaded into the home page through an `<iframe>` overlay:

- `openMiniSite(slug)` → `_showMiniSite(slug)` sets `frame.src = BASE_PATH + slug + '/'`, shows `#minisite-overlay`, swaps the theme to `css/pro.css`, and updates the nav.
- `closeMiniSite()` / `_hideMiniSite()` reverse this and restore the home nav/theme.
- The iframe can ask to be closed via `postMessage('close-minisite')`, handled by `window.addEventListener('message', ...)`.
- `persoLabels` maps slug → display name shown in the nav while a mini-site is open.
- `BASE_PATH` is computed from `location.pathname` so routing works whether the site is served from `/`, `/portfolio/`, or a custom domain.
- Direct landings on `/<slug>` (or `404.html?from=slug` redirects) are handled by the IIFE near the bottom of the mini-site block, which calls `_showMiniSite` or `showProject` based on whether the slug matches `persoLabels` or the `P` projects object.

Some Playground cards link straight to external sites instead of opening a mini-site (e.g. Inkipit → `https://inkipit.app/`, Thinkerbooks → `https://thinkerbook.org/`) via `onclick="window.open(url, '_blank')"`.

### Routing / history
Custom client-side routing via `history.pushState`/`popstate` — no router library. State objects look like `{minisite: slug}` or `{project: id}`; `popstate` re-derives the view from `e.state`.

### Project showcase ("Work")
Galeries Lafayette / case-study projects live in the `P` object (`const P = {...}`, around line 2187) and are rendered by `showProject(id, push)`.

### Themes / "moods"
The site has a theme switcher (`nextMood()`/`setTheme()`) that swaps `<link id="theme-css">` between stylesheets in `css/`: `pro.css` (default), `win2000.css`, `noaccess.css`, plus several others (`dark`, `editorial`, `fire`, `retro`, `skeuomorph`, `soft`, `swiss`, `anarchist`). Mini-sites and project views always force `pro.css`.

### Hero / profile chip
`.hero-sub` includes a `.profile-chip` with a thumbnail + hover popup (`img/theo-profile.jpg`). Keep profile imagery **hosted locally** (`img/`) rather than linking to third-party CDNs (e.g. Malt's `dam.malt.com`) — external hotlinks get blocked by ad-blockers/privacy extensions and can break without warning.

## CMS-backed mini-sites

Some mini-sites have their own admin/CMS under `<slug>/admin/` (e.g. `inkipit/admin/`), self-contained HTML apps with their own login, styling, and data fetching — independent of the main `index.html`.

## Automation

`.github/workflows/update-tracks.yml` runs monthly (and on pushes to `claude/dreamy-cannon`) to refresh `vinyle/tracks.json` from the iTunes Search API and auto-commits the result.

`scripts/` contains one-off Python utilities used to build/maintain specific mini-sites' content (e.g. `compile_thinkerbooks.py`, `download_covers.py`, `extract_verbatims.py`) — not part of the site's runtime.

## Content security policy

`_headers` sets a strict CSP (`default-src 'self'`, `img-src 'self' https: data:`, etc.). Keep new external resources (scripts, fonts, frames, connections) consistent with this policy or update it deliberately.
