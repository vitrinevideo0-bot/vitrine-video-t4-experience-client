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
- `ui-screens/manifest.json` — douze preuves PNG et leur planche.

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

## Contrôles locaux

```bash
python -m pip install -r requirements.txt
python tools/build_t4_capture_flow.py
python tools/build_t4_transition_contract.py
python tools/generate_t4_ui_screens.py
python -m unittest discover -s tests -v
```

Préflight vidéo facultatif :

```bash
python tools/fetch_rushes.py
python engine/render_silent.py
python tools/validate_silent.py
```

Le candidat présenté au propriétaire doit provenir de GitHub Actions. Aucun déploiement Cloudflare n’est effectué par ce dépôt.
