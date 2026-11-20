# T4 — audio complet, rotation et plan de contrôle

## Portée

Ce contrat ajoute au master visuel **Hybride cinématique** :

- la voix française explicitement choisie **VOIX-B / `voice-07`** ;
- quatre placements de scène à 1,2 s, 6,8 s, 14,7 s et 21,8 s ;
- exactement une musique Afrobeat par vidéo, parmi quatre variantes approuvées ;
- ducking, mastering, contrôle d’intelligibilité et mux final H.264/AAC ;
- un plan de contrôle Cloudflare inspiré du T2, sans rendu vidéo dans Cloudflare.

## Deux modes visuels explicites

### Rendu manuel de l’exemplaire approuvé

`approved_master_stream_copy` télécharge le master officiel de la Release V3, impose :

- SHA-256 fichier `5acd4eb958c1ec00a663066d57b39bbb43e61f39dbd9c1403db458b5e34bed9a` ;
- SHA-256 du flux H.264 `213bf4226341d3770faf18a86610b79e0cec78644c091e6666e96201afd9ede0` ;
- 720 × 1280, 30 i/s, 900 images, 30,000 s, aucune piste audio.

Le mux final utilise `-c:v copy`. Le rapport exige que le flux H.264 de sortie soit identique bit pour bit.

### Rendu client piloté par Cloudflare

`runtime_hybrid_render` :

1. stocke quatre captures S1/S2/S3/S4 dans R2 avec leur SHA-256 ;
2. les retélécharge et les vérifie sur GitHub Actions ;
3. reconstruit le visuel avec le moteur V3 approuvé et ses trois signatures ;
4. conserve les trois dernières secondes de S4 sans effet ;
5. effectue ensuite le mux audio avec copie bit pour bit de ce nouveau flux H.264.

Le hash du master V3 reste une référence de design, pas une fausse promesse d’identité avec des images client différentes.

## Voix et mix

- approbation : `approvals/APPROBATION_VOIX_B_T4_2026-11-20.json` ;
- stem : `audio/voice/t4-voice-v1/t4_voice_stem_30s.wav` ;
- SHA-256 : `74ec6378ba0b724631793c02c2d3f0308913c1790f6606784e587ccd2e34a759` ;
- stem : mono, 48 kHz, 30 s, −19,71 LUFS, −3,08 dBTP ;
- musique ouverte : −3 dB ;
- musique sous parole : −10 dB ;
- attaque : 120 ms ; relâchement : 450 ms ;
- master : cible −16 LUFS, plafond −2 dBTP ;
- livraison : AAC stéréo 48 kHz, 192 kb/s.

`audio/scripts/build_t4_complete.py` vérifie les sources voix, les quatre dérivés musicaux, le mode visuel, les caractéristiques du fichier, le flux vidéo copié, le niveau final, les échantillons non finis, l’écrêtage et la marge parole/musique.

## Rotation transactionnelle

Identifiants autorisés, dans l’ordre propriétaire :

1. `t4_music_569473` — ARPMedia ;
2. `t4_music_153058` — FASSounds ;
3. `t4_music_573648` — alex-morgan ;
4. `t4_music_439622` — SigmaMusicArt.

Règles :

- le choix automatique est déterministe à partir de `SHA-256(render_job_id)` ;
- la dernière réussite est retirée du pool avant le modulo ;
- un choix explicite identique à la dernière réussite est rejeté ;
- un échec ou un QC non PASS ne modifie pas l’état ;
- un callback réussi rejoué avec le même job est sans effet ;
- deux réussites concurrentes qui tentent la même musique ne peuvent pas toutes deux être commitée ;
- l’état n’avance qu’après `COMPLETED` + `quality.status=PASS` + MP4 vérifié dans R2.

Schéma : `schemas/T4_music_selection_state.schema.json`.

## Plan de contrôle Cloudflare

Code : `cloudflare/src/index.ts`.

Fonctions :

- idempotence de création de job ;
- validation stricte des six champs commerçant ;
- dépôt de quatre captures avec types, taille, métadonnées et SHA-256 ;
- création du RenderJob et sélection musicale ;
- `repository_dispatch` vers GitHub ;
- téléchargement contrôlé des captures par GitHub Actions ;
- dépôt du MP4 final dans R2 avec taille et SHA-256 ;
- validation de `RenderResult` ou `RenderError` ;
- commit conditionnel de l’état musical dans R2.

Routes principales :

- `POST /v1/jobs` ;
- `PUT /v1/jobs/{id}/captures/{S1..S4}` ;
- `POST /v1/jobs/{id}/dispatch` ;
- `GET /v1/jobs/{id}/payload` ;
- `GET /v1/jobs/{id}/captures/{S1..S4}` ;
- `PUT|GET /v1/jobs/{id}/output` ;
- `POST /v1/jobs/{id}/events` ;
- `GET /v1/music-state`.

Cloudflare est uniquement le plan de contrôle et le stockage. Le rendu visuel, le mixage et le QC restent sur GitHub Actions.

## Licence et Content ID

Les quatre pages publiques déclaraient la Pixabay Content License et **Content ID Registered**. Le dépôt conserve les pages HTML compressées, captures PNG, URL officielles et SHA-256. Il ne prétend pas posséder un certificat de téléchargement Pixabay lié à un compte authentifié.

- certificat interne : `audio/music/t4-afrobeat-v1/evidence/T4_MUSIC_PROVENANCE_CERTIFICATE.json` ;
- instantané : `audio/music/t4-afrobeat-v1/evidence/PIXABAY_CONTENT_LICENSE_SNAPSHOT_2026-11-20.md`.

Les originaux complets ne sont pas commités. Les MP3 dérivés ne doivent jamais être publiés comme ressources autonomes de Release. Une réclamation Content ID reste possible.

## Validation et déploiement

Tests locaux :

```bash
pytest -q
python tools/build_t4_cloudflare_contracts.py --check
(cd audio/voice/t4-voice-v1 && sha256sum -c SHA256SUMS.txt)
(cd audio/music/t4-afrobeat-v1 && sha256sum -c SHA256SUMS.txt)
npm ci --prefix cloudflare
npm test --prefix cloudflare
```

Le test d’intégration démarre Wrangler localement, un faux endpoint GitHub, puis couvre les rejeux, échecs, répétitions explicites et conflits concurrents.

**Aucun test local ni `wrangler deploy --dry-run` n’est un déploiement Cloudflare production.** Un déploiement réel exige un compte, le bucket R2, les secrets `CLIENT_API_TOKEN`, `CALLBACK_TOKEN`, `GITHUB_TOKEN`, ainsi que l’URL publique finale.
