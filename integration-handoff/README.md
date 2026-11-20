# Passation intégrateur et galerie — RESTAURATION-T4

- `T4_CLOUDFLARE_BOUNDARY_V1.json` sépare explicitement le plan de contrôle Cloudflare du rendu GitHub Actions et interdit toute fausse déclaration de déploiement.
- `T4_GALLERY_HANDOFF_V1.json` décrit la mise à jour du catalogue commun et le blocage réel de permission.

Le dépôt T4 est administrable par `vitrinevideo0-bot`. Le dépôt commun `j9028379-hue/vitrine-video-gabarits` n’accorde actuellement que la permission `READ` à ce compte. La mise à jour galerie peut être préparée et validée localement, mais ne doit jamais être annoncée comme poussée avant l’obtention d’un droit d’écriture ou d’une stratégie de fork explicitement autorisée.
