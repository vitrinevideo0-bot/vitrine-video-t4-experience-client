# T4 — audit final local de la rotation musicale stricte

Date locale : 2026-11-18
Dépôt : `vitrine-video-t4-experience-client`
Base locale : `4687950` (`main`)
Portée : migration locale non commitée; aucun push, tag, remplacement de Release ni déploiement Cloudflare.

## Contrat final

Ordre canonique :

`260354 → 154868 → 162186 → 321930 → 260354`

Garanties validées :

- état initial : piste 1 (`t4_music_260354`);
- chaque succès terminé avec QC `PASS` valide exactement le successeur;
- un choix explicite n’est accepté que s’il désigne ce successeur;
- un échec ne crée ni ne modifie l’état;
- `successful_render_jobs` conserve tous les succès déjà validés;
- le rejeu du même succès est idempotent, y compris après un cycle complet;
- une concurrence hors séquence est rejetée sans mutation;
- la transition piste 4 vers piste 1 est couverte.

## Résultats locaux finaux

- Python : **38/38 PASS**.
- Contrats Cloudflare générés : **CURRENT**.
- TypeScript sous Node 24 : **PASS**.
- Wrangler sous Node 24, `deploy --dry-run` : **PASS**.
- Intégration noire Worker/R2 locale : **PASS**, cycle complet, concurrence et rejeu historique.
- JSON : **65 fichiers valides**.
- Compilation Python et `git diff --check` : **PASS**.
- Checksums des packs musique et voix : **PASS**.
- Stress déterministe : **10 000 sélections**, exactement **2 500 par piste**.

## Paquet intégrateur reconstruit

Deux constructions indépendantes sont byte-identiques.

- fichier : `restauration-t4-experience-client-v1.0.0.zip`
- taille : **26 693 245 octets**
- SHA-256 : `b2e853187c8b339b0518ff9db8dddf39bef4b87734702ab31d02c839c5030fd8`
- entrées manifestées : **150**
- validation après extraction propre : **30/30 PASS**
- suite embarquée après extraction : **38/38 PASS**
- golden complet conservé et verrouillé : SHA-256 `a1cf0abf8f00724468c1489ce14f5e656b3eb85730c5d1e2a4ec383117fe74bd`

Preuves locales :

- `/home/user/.cache/t4-strict-final2-a/T4_STRICT_VALIDATION.json`
- `/home/user/.cache/t4-strict-final2-a/T4_INTEGRATOR_PACKAGE_BUILD_REPORT.json`
- seconde construction identique : `/home/user/.cache/t4-strict-final2-b/`

## Frontière de livraison

Les runs, commits et Releases déjà référencés dans le dépôt restent historiques et additifs. Ils ne constituent pas une preuve de publication de cette migration stricte. La migration présente est validée localement uniquement jusqu’à création d’un commit dédié, push et contrôle CI ultérieurs.
