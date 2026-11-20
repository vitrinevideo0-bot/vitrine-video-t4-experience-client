# Vitrine Vidéo — RESTAURATION-T4 · Expérience client

Quatrième gabarit restauration : accueil, service, dégustation réelle et ambiance finale.

## Direction créative active — V3 hybride cinématique

Deux candidats ont permis de fixer le bon équilibre :

- V1 rejetée : effets trop exagérés et trop présents à l’intérieur des rushes ;
- V2 rejetée : fondus naturels trop basiques au moment des changements ;
- **V3 active : trois transitions cinématiques distinctes, impressionnantes mais limitées aux trois coupes.**

| Coupe | Instant | Signature |
|---|---:|---|
| Bienvenue → Service | 6 s | whip-pan horizontal rapide |
| Service → Dégustation | 14 s | zoom traversant le plat |
| Dégustation → Ambiance | 21 s | whip-zoom d’ouverture |

Chaque raccord dure huit images, commence quatre images avant la coupe et finit quatre images après. La dernière image retombe exactement sur le rush entrant. Les 876 autres images restent naturelles et plein écran, soit **97,33 %** du montage.

Contrats actifs :

- `approvals/CHOIX_TRANSITIONS_HYBRIDES_V3_2026-11-18.json` ;
- `config/T4_HYBRID_CINEMATIC_TRANSITIONS_V3_0_0.json` ;
- `reverse-engineering/T4_TRANSITIONS_HYBRIDES_30S_V3.json` ;
- `config/T4_EXPERIENCE_CLIENT_TEMPLATE_V3_0_0.json`.

Les contrats V1 et V2 restent uniquement comme historique.

## Questions et parcours de capture

- `form/questions_T4.json` — six questions compatibles T1/T2/T3 ;
- `capture-guide/consignes_T4.json` — quatre prises 6/8/7/9 s ;
- `config/T4_CAPTURE_FLOW_V1_0_0.json` — exactement douze écrans A/B/C ;
- `ui-screens/manifest.json` — douze preuves PNG et leur planche ;
- `simulation/T4_12_ECRANS_EXECUTABLE.html` — simulation autonome des six questions et des douze états, générée depuis les deux JSON.

| Scène | Durée | Contenu |
|---|---:|---|
| S1 — BIENVENUE | 6 s | entrée, salle ou accueil |
| S2 — LE SERVICE | 8 s | plat pris en charge, déplacé et présenté |
| S3 — LA DÉGUSTATION | 7 s | bouchée et réaction naturelle d’une personne consentante |
| S4 — VENEZ / COMMANDEZ | 9 s | ambiance puis trois secondes finales stables |

Chaque scène possède trois états stables : **A Guide**, **B Enregistrement**, **C Validation**.

## Candidat silencieux V3

Le workflow `.github/workflows/render-silent.yml` :

1. compile et teste les contrats ;
2. reconstruit les douze écrans et la timeline V3 ;
3. télécharge quatre rushes Pexels verrouillés par taille et SHA-256 ;
4. produit les trois signatures hybrides sur un runner GitHub ;
5. valide 30 s, 720×1280, 30 i/s, 900 images, H.264/yuv420p ;
6. contrôle les fenêtres, l’impact visible et les points d’entrée/sortie propres ;
7. vérifie l’absence d’audio, de texte, de mosaïque, grille et glitch ;
8. publie un artefact et une pré-Release immuable.

Les rushes bruts ne sont jamais suivis par Git ni publiés séparément.

## Rendu complet — VOIX-B et quatre musiques Afrobeat

La voix propriétaire est **VOIX-B / `voice-07`**, approuvée dans `approvals/APPROBATION_VOIX_B_T4_2026-11-20.json`. Son stem mono 48 kHz de 30 secondes est verrouillé par le SHA-256 `74ec6378ba0b724631793c02c2d3f0308913c1790f6606784e587ccd2e34a759`.

Le paquet `config/T4_MUSIC_PACK_V1_0_0.json` contient exactement quatre pistes Pixabay approuvées : Ovrsoull (`260354`), 37660440 (`154868`), Gis_photography (`162186`) et 47643651 (`321930`). Une vidéo n’en utilise qu’une. L’algorithme retire toujours la dernière réussite ; un choix explicite identique est rejeté et un échec ne modifie pas l’état.

Le mix suit le modèle P1/T1 :

- musique à −3 dB hors parole et −10 dB sous parole ;
- attaque 120 ms, relâchement 450 ms ;
- cible −16 LUFS, plafond −2 dBTP ;
- AAC stéréo 48 kHz à 192 kb/s ;
- contrôle de la marge parole/musique, de l’écrêtage et du flux vidéo.

Le workflow `.github/workflows/render-complete.yml` produit un seul MP4 complet. Pour l’exemplaire approuvé, il retélécharge le master officiel et conserve son flux H.264 bit pour bit avec `-c:v copy`. Les lancements issus du Worker reconstruisent les quatre captures client avec le moteur V3, puis conservent ce nouveau flux pendant le mux audio.

Au moment des captures datées, aucune des quatre pages Pixabay n’affichait **Content ID Registered**. Cette observation n’est pas une garantie absolue future. Les preuves, l’approbation propriétaire et le certificat interne de provenance sont archivés, sans prétendre disposer d’un certificat Pixabay authentifié. Les MP3 dérivés ne sont jamais joints séparément aux Releases et le projet ne les inscrit jamais dans Content ID.

## Plan de contrôle Cloudflare

`cloudflare/src/index.ts` porte les capacités T2 : R2, SHA-256, RenderJob, dispatch GitHub, RenderResult/RenderError, callback validé, stockage du MP4 final et rotation transactionnelle après `COMPLETED` + QC PASS seulement. Cloudflare ne rend pas la vidéo.

Le test d’intégration couvre notamment : rejeu idempotent, échec sans mutation, choix explicite répétitif rejeté et conflit concurrent sur la même prochaine musique. Le détail est dans `docs/T4_COMPLETE_AUDIO_AND_CONTROL_PLANE.md`.

## Contrat catalogue et paquet intégrateur

`config/T4_EXPERIENCE_CLIENT_PACKAGE_V1_0_0.json` aligne T4 sur le niveau architectural T3. Le rendu complet GitHub `44696445339` et sa pré-Release additive `t4-experience-client-v4.0.0-complete-candidate-1` ont été revalidés. Le master V4 est verrouillé par sa taille, son SHA-256 `b5393c641ddb260167e86858779f2a9b494d789befb081ec3f386d9cda058a1a` et le hash de son flux H.264.

`packages/t4-experience-client-v1/package_spec.json`, le constructeur déterministe et le validateur après extraction propre ont passé le workflow serveur `44697329915`. Les deux constructions étaient bit à bit identiques ; la validation après extraction puis la revalidation de la Release ont chacune passé 28/28 contrôles. Le ZIP immuable `restauration-t4-experience-client-v1.0.0.zip`, SHA-256 `c97da4deecae09f58b587c1fc508c8f48fce729c5800e4258c774a3dfca8c883`, est publié dans `t4-experience-client-integrator-v1.0.0-1`.

L’audit `reports/AUDIT_ARCHITECTURE_T3_T4_GALLERY_2026-11-20.md` ne déclare toutefois pas 100 %. La mise à jour de la galerie commune est préparée, mais le compte actif n’y possède actuellement que la permission `READ` ; aucun push galerie n’est revendiqué. Aucun déploiement Cloudflare/R2 production, Android ou OTA n’est non plus revendiqué.

## Contrôles locaux

```bash
python -m pip install -r requirements.txt
python tools/build_t4_capture_flow.py
python tools/build_t4_transition_contract.py
python tools/generate_t4_ui_screens.py
python tools/build_t4_simulation.py --output /tmp/T4_12_ECRANS_EXECUTABLE.html
cmp simulation/T4_12_ECRANS_EXECUTABLE.html /tmp/T4_12_ECRANS_EXECUTABLE.html
python tools/build_t4_cloudflare_contracts.py --check
pytest -q
(cd audio/voice/t4-voice-v1 && sha256sum -c SHA256SUMS.txt)
(cd audio/music/t4-afrobeat-v1 && sha256sum -c SHA256SUMS.txt)
npm ci --prefix cloudflare
npm test --prefix cloudflare
```

Préflight vidéo facultatif :

```bash
python tools/fetch_rushes.py
python engine/render_silent.py
python tools/validate_silent.py
```

Le candidat présenté au propriétaire doit provenir de GitHub Actions. Aucun déploiement Cloudflare n’est effectué par ce dépôt.
