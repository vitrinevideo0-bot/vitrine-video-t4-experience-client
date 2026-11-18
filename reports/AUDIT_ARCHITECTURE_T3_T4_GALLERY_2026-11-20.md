# Audit architectural T3 → T4 → galerie commune

Date effective : 20 novembre 2026.

## Résultat actuel

L’audit a comparé T4 au niveau d’intégration atteint par T3 et au dossier T4 obsolète de la galerie commune. Les manques ont été corrigés automatiquement : schémas, adaptateur, état musical, simulation exécutable, Worker Cloudflare, tests d’intégration, workflows complets, spécification, fermeture de l’inventaire et outils du paquet intégrateur.

**Addendum de migration stricte :** le pool actif de remplacement est `260354→154868→162186→321930`. L’état initial impose la première piste; chaque succès/QC PASS impose le successeur exact; échec sans mutation; choix explicite sans saut; registre durable `successful_render_jobs`; rejeu d’un ancien succès après un tour complet sans mutation. La suite locale passe 38 tests, l’intégration Worker/R2 locale couvre le cycle complet et aucun déploiement production n’a été effectué. Les références de runs et de Releases ci-dessous restent les preuves historiques additives auxquelles elles se rapportent.

Le commit complet `0a02f82bf1fe4726f21900362929e1ff5529c037` a été poussé et sa CI GitHub `44696224313` est PASS. Le rendu complet GitHub `44696445339` est PASS. Sa pré-Release additive `t4-experience-client-v4.0.0-complete-candidate-1` a été téléchargée et revalidée indépendamment : quinze actifs sur quinze correspondent au manifeste SHA-256, le QC vaut 26/26, et le master complet est verrouillé par taille, SHA-256 et hash du flux vidéo.

Le verrouillage a été poussé dans `7ab0090d6dd0928a3e7bdb2723ac69b2d4d844a2`, avec CI `44697117316` PASS. Le workflow intégrateur `44697329915` a ensuite construit deux ZIP bit à bit identiques, validé une extraction propre 28/28 et publié la pré-Release additive `t4-experience-client-integrator-v1.0.0-1`. Cette Release a été téléchargée ; ses quatre actifs contrôlés correspondent au manifeste, puis le ZIP a repassé indépendamment les 28 contrôles d’extraction propre.

Le statut **100 % n’est toujours pas déclaré**. La galerie commune reste en lecture seule, aucun déploiement Cloudflare/R2 production n’est prouvé, et aucune intégration Android/OTA n’est revendiquée.

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
| Rotation persistante stricte `1→2→3→4→1` avec registre durable | Oui | `adapter/t4_adapter.py`, `cloudflare/src/index.ts` |
| RenderJob / Result / Error | Oui | `schemas/` |
| Worker R2 + callback + état transactionnel | Oui, testé hors production | `cloudflare/src/index.ts` |
| Test noir Worker | PASS local et CI | `cloudflare/test/control_plane_integration.py` |
| Rendu complet GitHub | PASS, run `44696445339` | `proofs/T4_GITHUB_COMPLETE_MASTER_REVALIDATION_2026-11-20.json` |
| Master V4 complet | Verrouillé | SHA-256 `b5393c641ddb260167e86858779f2a9b494d789befb081ec3f386d9cda058a1a` |
| Paquet intégrateur | PASS, run `44697329915`, extraction 28/28 | `proofs/T4_INTEGRATOR_PACKAGE_SERVER_VALIDATION_2026-11-20.json` |
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

## Paquet intégrateur validé

- run : `44697329915` ;
- pré-Release : `t4-experience-client-integrator-v1.0.0-1` ;
- fichier : `restauration-t4-experience-client-v1.0.0.zip` ;
- taille : `28 068 769` octets ;
- SHA-256 : `c97da4deecae09f58b587c1fc508c8f48fce729c5800e4258c774a3dfca8c883` ;
- inventaire : `143` entrées ;
- deux constructions GitHub : identiques ;
- extraction propre GitHub : **PASS 28/28** ;
- revalidation après téléchargement de la Release : **PASS 28/28** ;
- originaux Pixabay complets : absents ;
- ressources musicales autonomes de Release : absentes ;
- secrets injectés : aucun ;
- déploiement Cloudflare : non.

## Différence correcte entre rendu approuvé et rendu client

Le rendu manuel de l’exemplaire approuvé retélécharge le master V3 officiel et conserve son flux H.264 bit pour bit pendant le mux.

Un job client Cloudflare utilise nécessairement les quatre nouvelles captures. GitHub Actions les vérifie, reconstruit le visuel avec le moteur V3 approuvé, puis copie bit pour bit ce nouveau flux pendant le mux. Le hash du master V3 reste alors une référence de design, jamais une fausse identité de fichier.

## Galerie commune

Le dépôt commun identifié est `j9028379-hue/vitrine-video-gabarits`. Son dossier T4 indique encore « À DÉVELOPPER » et ne reflète pas l’implémentation indépendante actuelle.

L’identité GitHub active `vitrinevideo0-bot` possède la permission **READ** sur ce dépôt, contre **ADMIN** sur le dépôt T4. Il est donc possible de préparer une mise à jour et un contrat de passation, mais pas de pousser honnêtement la branche commune. Aucun fork ne sera créé sans autorisation explicite.

Preuve machine : `integration-handoff/T4_GALLERY_HANDOFF_V1.json`.

## Portes restantes avant une affirmation à 100 %

1. pousser la mise à jour galerie lorsque la permission le permet ;
2. déclarer un déploiement Cloudflare uniquement si endpoint, compte, secrets et bucket R2 production sont réellement prouvés ;
3. revendiquer Android ou OTA uniquement après une intégration réellement exécutée et testée.
