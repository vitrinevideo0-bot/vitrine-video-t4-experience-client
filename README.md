# Vitrine Vidéo — RESTAURATION-T4 · Expérience client

Quatrième gabarit restauration : accueil, service, dégustation réelle et ambiance finale.

## Correction créative V2

Le candidat V1 a été rejeté parce que ses transitions étaient trop exagérées. La règle active V2 est désormais : **laisser les rushes naturels en plein écran et placer une transition rapide seulement lorsqu’un rush change**.

- trois raccords seulement, aux secondes **6, 14 et 21** ;
- quatre images par raccord, soit environ **133 ms** ;
- fondu de mouvement plein écran très léger ;
- **aucune** mosaïque, grille, secousse, cassure rectangulaire ou glitch ;
- 888 images naturelles sans transition, soit **98,67 %** du montage.

Contrats actifs :

- `approvals/CORRECTION_TRANSITIONS_NATURELLES_V2_2026-11-18.json` ;
- `config/T4_NATURAL_TRANSITIONS_CONTRACT_V2_0_0.json` ;
- `reverse-engineering/T4_TRANSITIONS_NATURELLES_30S_V2.json` ;
- `config/T4_EXPERIENCE_CLIENT_TEMPLATE_V2_0_0.json`.

Le contrat A+B+C+D V1 est conservé uniquement comme historique et n’est plus utilisé par le moteur actif.

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

## Candidat silencieux V2

Le workflow `.github/workflows/render-silent.yml` :

1. compile et teste les contrats ;
2. reconstruit les douze écrans et la timeline V2 ;
3. télécharge quatre rushes Pexels verrouillés par taille et SHA-256 ;
4. produit les trois raccords naturels sur un runner GitHub ;
5. valide 30 s, 720×1280, 30 i/s, 900 images, H.264/yuv420p ;
6. vérifie l’absence d’audio, de texte et des cinq familles exagérées V1 ;
7. publie un artefact et une pré-Release immuable.

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
