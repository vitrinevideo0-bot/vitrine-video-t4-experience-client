# Audit architectural T3 → T4 → galerie commune

Date effective : 20 novembre 2026.

## Résultat actuel

L’audit a comparé T4 au niveau d’intégration atteint par T3 et au dossier T4 obsolète de la galerie commune. Les manques locaux ont été corrigés automatiquement : schémas, adaptateur, état musical, simulation exécutable, Worker Cloudflare, tests d’intégration, workflow complet, spécification et outils du paquet intégrateur.

Le commit complet `0a02f82bf1fe4726f21900362929e1ff5529c037` a été poussé et sa CI GitHub `44696224313` est PASS. Le rendu complet GitHub `44696445339` est également PASS. Sa pré-Release additive `t4-experience-client-v4.0.0-complete-candidate-1` a été téléchargée et revalidée indépendamment : quinze actifs sur quinze correspondent au manifeste SHA-256, le QC vaut 26/26, et le master complet est désormais verrouillé par taille, SHA-256 et hash du flux vidéo.

Le statut **100 % n’est pas déclaré**. Le paquet intégrateur doit encore passer sur GitHub, la galerie commune reste en lecture seule et aucun déploiement Cloudflare production n’est prouvé.

## Capacités désormais présentes dans T4

| Capacité | T4 | Preuve |
|---|---|---|
| Six questions canoniques | Oui | `form/questions_T4.json` |
| Quatre scènes 6/8/7/9 s | Oui | `config/T4_CAPTURE_FLOW_V1_0_0.json` |
| Douze écrans A/B/C | Oui | `ui-screens/manifest.json` |
| Simulation exécutable 6 + 12 | Oui | `simulation/T4_12_ECRANS_EXECUTABLE.html` |
| Contrat canonique + schéma | Oui | `config/T4_EXPERIENCE_CLIENT_PACKAGE_V1_0_0.json` |
| Quatre voix comparables | Oui | `audio/voice/t4-voice-candidates-v1/manifest.json` |
| Sélection propriétaire | VOIX-B | `approvals/APPROBATION_VOIX_B_T4_2026-11-20.json` |
| Quatre musiques approuvées | Oui | `config/T4_MUSIC_PACK_V1_0_0.json` |
| Rotation persistante anti-répétition | Oui | `adapter/t4_adapter.py` |
| RenderJob / Result / Error | Oui | `schemas/` |
| Worker R2 + callback + état transactionnel | Oui, testé hors production | `cloudflare/src/index.ts` |
| Test noir Worker | PASS local et CI | `cloudflare/test/control_plane_integration.py` |
| Rendu complet GitHub | PASS, run `44696445339` | `proofs/T4_GITHUB_COMPLETE_MASTER_REVALIDATION_2026-11-20.json` |
| Master V4 complet | Verrouillé | SHA-256 `b5393c641ddb260167e86858779f2a9b494d789befb081ec3f386d9cda058a1a` |
| Paquet déterministe | Master verrouillé, run serveur à faire | `packages/t4-experience-client-v1/package_spec.json` |
| Déploiement Cloudflare production | **Non** | frontière explicite |

## Master complet GitHub verrouillé

- run : `44696445339` ;
- pré-Release : `t4-experience-client-v4.0.0-complete-candidate-1` ;
- fichier : `VIDEO_T4_COMPLETE_VOIX_B_MUSIQUE_ROTATION_V4_A_VALIDER.mp4` ;
- taille : `12 126 957` octets ;
- SHA-256 fichier : `b5393c641ddb260167e86858779f2a9b494d789befb081ec3f386d9cda058a1a` ;
- SHA-256 flux H.264 : `213bf4226341d3770faf18a86610b79e0cec78644c091e6666e96201afd9ede0` ;
- musique choisie automatiquement : choix 3, alex-morgan ;
- voix : VOIX-B / `voice-07` ;
- QC : **PASS 26/26** ;
- audio final : −16,18 LUFS, −1,93 dBTP, sans écrêtage.

La piste sélectionnée et les trois autres pistes du pool sont marquées **Content ID Registered**. Cette preuve ne promet donc pas l’absence de réclamation automatisée.

## Différence correcte entre rendu approuvé et rendu client

Le rendu manuel de l’exemplaire approuvé retélécharge le master V3 officiel et conserve son flux H.264 bit pour bit pendant le mux.

Un job client Cloudflare utilise nécessairement les quatre nouvelles captures. GitHub Actions les vérifie, reconstruit le visuel avec le moteur V3 approuvé, puis copie bit pour bit ce nouveau flux pendant le mux. Le hash du master V3 reste alors une référence de design, jamais une fausse identité de fichier.

## Galerie commune

Le dépôt commun identifié est `j9028379-hue/vitrine-video-gabarits`. Son dossier T4 indique encore « À DÉVELOPPER » et ne reflète pas l’implémentation indépendante actuelle.

L’identité GitHub active `vitrinevideo0-bot` possède la permission **READ** sur ce dépôt, contre **ADMIN** sur le dépôt T4. Il est donc possible de préparer une mise à jour et un contrat de passation, mais pas de pousser honnêtement la branche commune. Aucun fork ne sera créé sans autorisation explicite.

Preuve machine : `integration-handoff/T4_GALLERY_HANDOFF_V1.json`.

## Portes restantes avant une affirmation à 100 %

1. pousser le commit qui verrouille le master V4 ;
2. construire deux fois le ZIP intégrateur et prouver son identité bit à bit sur GitHub ;
3. valider ce ZIP après extraction propre sur GitHub ;
4. pousser la mise à jour galerie lorsque la permission le permet ;
5. déclarer un déploiement Cloudflare uniquement si endpoint, compte, secrets et bucket R2 production sont réellement prouvés.
