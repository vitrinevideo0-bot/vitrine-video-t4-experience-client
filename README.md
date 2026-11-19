# Vitrine Vidéo — RESTAURATION-T4 · Expérience client

Implémentation du quatrième gabarit restauration : accueil, service, dégustation réelle et ambiance finale.

## Contrats reliés

- `form/questions_T4.json` — six questions compatibles T1/T2/T3 ;
- `capture-guide/consignes_T4.json` — quatre prises 6/8/7/9 s ;
- `config/T4_CAPTURE_FLOW_V1_0_0.json` — exactement douze écrans A/B/C ;
- `ui-screens/manifest.json` — douze preuves PNG et leur planche ;
- `config/T4_CREATIVE_CONTRACT_V1_0_0.json` — fusion créative A+B+C+D ;
- `reverse-engineering/T4_TRANSITIONS_30S.json` — calendrier de 48 événements ;
- `config/T4_EXPERIENCE_CLIENT_TEMPLATE_V1_0_0.json` — contrat racine.

## Parcours de capture

| Scène | Durée | Contenu |
|---|---:|---|
| S1 — BIENVENUE | 6 s | entrée, salle ou accueil |
| S2 — LE SERVICE | 8 s | plat pris en charge, déplacé et présenté |
| S3 — LA DÉGUSTATION | 7 s | bouchée et réaction naturelle d’une personne consentante |
| S4 — VENEZ / COMMANDEZ | 9 s | ambiance puis trois secondes finales stables |

Chaque scène possède trois états stables : **A Guide**, **B Enregistrement**, **C Validation**. Le décompte `3·2·1` est transitoire.

## Candidat silencieux

Le workflow `.github/workflows/render-silent.yml` :

1. compile et teste les contrats ;
2. reconstruit les douze écrans et vérifie leur identité ;
3. télécharge quatre rushes Pexels verrouillés par taille et SHA-256 ;
4. rend la fusion A+B+C+D sur un runner GitHub ;
5. valide 30 s, 720×1280, 30 i/s, 900 images, H.264/yuv420p ;
6. vérifie l’absence de piste audio et de texte incrusté ;
7. publie un artefact et, sur demande, une pré-Release immuable.

Les rushes bruts ne sont jamais suivis par Git ni publiés séparément.

## Commandes locales de contrôle

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

Le rendu présenté au propriétaire doit provenir de GitHub Actions. Aucun déploiement Cloudflare n’est effectué par ce dépôt.
