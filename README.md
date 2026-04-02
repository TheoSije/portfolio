# 🌊 theo.design

Mon portfolio personnel — [jegousse.com](https://jegousse.com)

Designer produit basé à Paris. Ce repo contient le code source de mon site : une SPA entièrement en HTML/CSS/JS vanilla, sans framework, sans build step.

## 🗂 Structure

```
portfolio/
├── index.html          # Page principale + système de minisites
├── css/                # Styles globaux
├── img/                # Assets
├── incipit/            # 🖊 Inkipit — générateur d'incipit littéraires
├── vinyle/             # 💿 Platine — player vinyle interactif
├── unheard/            # 🎵 Unheard — tracks à 0 plays
├── soundhands/         # ✋ Sound Hands — contrôle audio par gestes
├── chess/              # ♟  Chess Puzzles
├── emojy/              # 🎬 Cinémoji — devine le film
├── legalmate/          # 🤖 Legalmate — conseils légaux par IA
├── meteomiche/         # 🌱 Météomiche — météo jardinière live
├── surfcams/           # 🌊 Surf Basque — forecast & cams côte basque
├── inkiphot/           # 🫦 Inkip'hot — littérature érotique
└── sitemap.xml
```

## 🧪 Playground

Chaque minisite est un projet indépendant chargé en iframe via `openMiniSite(slug)`. Ils s'ouvrent en plein écran et communiquent avec la page principale via `postMessage`.

## ⚙️ Tech

- **Zéro dépendance** — HTML · CSS · JS vanilla
- **APIs** — Open-Meteo Marine (surf forecast), iTunes, Windy Embed, YouTube
- **Polices** — DM Sans · DM Mono · Playfair Display · Roboto

## 🚀 Lancer en local

```bash
git clone https://github.com/TheoSije/portfolio.git
cd portfolio
# Ouvrir index.html dans un navigateur
# ou lancer un serveur local :
npx serve .
```

## ✨ Auteur

Créé par **Théo Jégousse** — [theosije@gmail.com](mailto:theosije@gmail.com) · [LinkedIn](https://www.linkedin.com/in/theojegousse/) · [jegousse.com](https://jegousse.com)

*Made with Claude & VS Code*
