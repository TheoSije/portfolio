# theo.design — Portfolio de Théo Jégousse

> **Product Designer** · [jegousse.com](https://jegousse.com)

Portfolio personnel de Théo Jégousse — designer produit basé à Paris, spécialisé en UX/UI, design system et expériences digitales. Construit entièrement en HTML/CSS/JS vanilla, sans framework.

---

## 🔗 Live

**[jegousse.com](https://jegousse.com)**

---

## 🗂 Projets sélectionnés

| Projet | Année | Secteur |
|--------|-------|---------|
| **Galeries Lafayette** | 2024 | Retail / E-commerce |
| **Deezer** | 2023 | Music streaming |
| **Devialet** | 2023 | Audio / Luxury tech |
| **Mauboussin** | 2025 | Joaillerie / Luxury |
| **Gotaxfree** | 2024 | Fintech |

---

## 🧪 Playground

Une collection de mini-projets interactifs, chacun dans son propre minisite embarqué via iframe.

| Minisite | Description |
|----------|-------------|
| 🖊 **[Inkipit](https://jegousse.com/incipit/)** | Générateur d'incipit littéraires avec effet machine à écrire |
| 💿 **[Platine](https://jegousse.com/vinyle/)** | Player musical autour d'un vinyle interactif |
| 🎵 **[Unheard](https://jegousse.com/unheard/)** | Découverte de tracks à 0 plays sur Spotify |
| ✋ **[Sound Hands](https://jegousse.com/soundhands/)** | Contrôle audio par gestes via la caméra |
| ♟ **[Chess Puzzles](https://jegousse.com/chess/)** | Puzzles d'échecs du plus simple au plus complexe |
| 🤖 **[Legalmate](https://jegousse.com/legalmate/)** | Conseils légaux par IA |
| 🎬 **[Cinémoji](https://jegousse.com/emojy/)** | Devine le film caché derrière les emojis |
| 🌱 **[Météomiche](https://jegousse.com/meteomiche/)** | Météo jardinière live à Eymoutiers (87) |
| 🌊 **[Surf Basque](https://jegousse.com/surfcams/)** | Livecams & forecast surf sur 10 spots de la Côte Basque |
| 🫦 **[Inkip'hot](https://jegousse.com/inkiphot/)** | Passages de littérature érotique · Réage, Bataille, Nin, Duras… |

---

## ⚙️ Stack technique

Aucune dépendance, aucun framework. Tout est écrit à la main.

```
HTML · CSS · JavaScript (vanilla)
```

**APIs utilisées :**
- [Open-Meteo Marine API](https://marine-api.open-meteo.com) — forecast vagues & vent (Surf Basque)
- [Windy Embed](https://embed.windy.com) — carte météo marine interactive
- [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) — données musicales (Platine, Unheard)
- [GitHub API](https://api.github.com) — données publiques
- [YouTube Embed](https://developers.google.com/youtube/iframe_api_reference) — intégration vidéo

**Polices :**
- [Playfair Display](https://fonts.google.com/specimen/Playfair+Display) — titres éditoriaux
- [DM Sans](https://fonts.google.com/specimen/DM+Sans) — interface
- [DM Mono](https://fonts.google.com/specimen/DM+Mono) — données & chiffres
- Roboto · Roboto Condensed — sections principal

---

## 🏗 Architecture

```
portfolio/
├── index.html          # Page principale (SPA-like avec iframe minisites)
├── css/                # Styles globaux
├── img/                # Assets visuels
├── incipit/            # Minisite Inkipit
├── inkiphot/           # Minisite Inkip'hot
├── vinyle/             # Minisite Platine
├── unheard/            # Minisite Unheard
├── soundhands/         # Minisite Sound Hands
├── chess/              # Minisite Chess Puzzles
├── emojy/              # Minisite Cinémoji
├── legalmate/          # Minisite Legalmate
├── meteomiche/         # Minisite Météomiche
├── surfcams/           # Minisite Surf Basque
└── sitemap.xml
```

Les minisites s'ouvrent via un système `openMiniSite(slug)` qui charge chaque projet dans un `<iframe>` en plein écran, avec gestion du retour arrière (`postMessage`).

---

## 🤝 Contact

- ✉️ [theosije@gmail.com](mailto:theosije@gmail.com)
- 💼 [linkedin.com/in/theojegousse](https://www.linkedin.com/in/theojegousse/)
- 🐙 [github.com/TheoSije](https://github.com/TheoSije)

---

*Made with [Claude](https://claude.ai) & VS Code · © 2026 theo.design*
