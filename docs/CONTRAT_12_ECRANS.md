# RESTAURATION-T4 — Contrat des douze écrans

Le parcours contient **exactement quatre scènes × trois états stables**. Le décompte `3 · 2 · 1` entre A et B est transitoire et n’est pas un treizième écran.

| N° | Identifiant | État | Durée | Action positive |
|---:|---|---|---:|---|
| 1 | `T4_CAPTURE_S1_A_GUIDE` | guide BIENVENUE | 6 s | `COMMENCER À FILMER` |
| 2 | `T4_CAPTURE_S1_B_RECORDING` | caméra + chrono | 6 s | arrêt automatique |
| 3 | `T4_CAPTURE_S1_C_REVIEW` | relecture sonore | 6 s | `SCÈNE SUIVANTE` |
| 4 | `T4_CAPTURE_S2_A_GUIDE` | guide LE SERVICE | 8 s | `COMMENCER À FILMER` |
| 5 | `T4_CAPTURE_S2_B_RECORDING` | caméra + chrono | 8 s | arrêt automatique |
| 6 | `T4_CAPTURE_S2_C_REVIEW` | relecture sonore | 8 s | `SCÈNE SUIVANTE` |
| 7 | `T4_CAPTURE_S3_A_GUIDE` | guide LA DÉGUSTATION | 7 s | `COMMENCER À FILMER` |
| 8 | `T4_CAPTURE_S3_B_RECORDING` | caméra + chrono | 7 s | arrêt automatique |
| 9 | `T4_CAPTURE_S3_C_REVIEW` | relecture sonore | 7 s | `SCÈNE SUIVANTE` |
| 10 | `T4_CAPTURE_S4_A_GUIDE` | guide VENEZ / COMMANDEZ | 9 s | `COMMENCER À FILMER` |
| 11 | `T4_CAPTURE_S4_B_RECORDING` | caméra + chrono | 9 s | arrêt automatique |
| 12 | `T4_CAPTURE_S4_C_REVIEW` | relecture sonore | 9 s | `VOIR MON MONTAGE` |

## Sources JSON

- questions : `form/questions_T4.json` ;
- consignes et textes : `capture-guide/consignes_T4.json` ;
- états, actions et liaisons : `config/T4_CAPTURE_FLOW_V1_0_0.json` ;
- preuves visuelles : `ui-screens/manifest.json` et `ui-screens/T4_PLANCHE_12_ECRANS.png` ;
- contrat racine : `config/T4_EXPERIENCE_CLIENT_TEMPLATE_V1_0_0.json`.

Les douze PNG sont régénérables par `python tools/generate_t4_ui_screens.py`. Le CI reconstruit les JSON et les images, puis exige une identité binaire avec les fichiers suivis par Git.
