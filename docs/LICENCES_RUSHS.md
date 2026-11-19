# Licences des rushes de démonstration T4

Les quatre vidéos de démonstration proviennent de **Pexels** et sont utilisées selon la [licence Pexels](https://www.pexels.com/license/), vérifiée le 19 novembre 2026 UTC.

| Scène | Pexels | Créateur | Page source | Usage T4 |
|---|---:|---|---|---|
| S1 — Bienvenue | 8921923 | Ron Lach | https://www.pexels.com/video/people-greeting-each-other-at-a-restaurant-8921923/ | accueil humain |
| S2 — Le service | 5657164 | ROMAN ODINTSOV | https://www.pexels.com/video/a-person-serving-food-5657164/ | déplacement et service du plat |
| S3 — La dégustation | 10058505 | cottonbro studio | https://www.pexels.com/video/close-up-on-two-people-eating-10058505/ | bouchée et sourire naturel |
| S4 — Venez / Commandez | 8922781 | Ron Lach | https://www.pexels.com/video/a-group-of-friends-in-a-bar-8922781/ | ambiance de salle à caméra fixe |

## Verrouillage technique

Les URL de téléchargement, tailles, métadonnées de montage et SHA-256 sont verrouillés dans `rushes/manifest.json`. Le workflow refuse un fichier dont la taille ou le hash diffère.

## Politique de publication

- les MP4 bruts ne sont pas suivis par Git ;
- ils restent dans `rushes/cache/`, dossier ignoré ;
- ils ne sont jamais ajoutés à l’artefact GitHub Actions ni à la pré-Release ;
- seuls le master transformé, les contrats, les rapports et les preuves sont publiés ;
- les médias servent à démontrer le moteur et ne remplacent pas les captations d’un commerçant réel.
