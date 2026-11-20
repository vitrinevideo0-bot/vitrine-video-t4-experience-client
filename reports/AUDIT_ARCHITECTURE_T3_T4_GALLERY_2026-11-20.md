# Audit architectural T3 → T4 → galerie commune

Date effective : 20 novembre 2026.

## Résultat actuel

L’audit a comparé T4 au niveau d’intégration atteint par T3 et au dossier T4 obsolète de la galerie commune. Les manques locaux ont été corrigés automatiquement : schémas, adaptateur, état musical, simulation exécutable, Worker Cloudflare, tests d’intégration, workflow complet, spécification et outils du paquet intégrateur.

Le statut **100 % n’est pas déclaré**. Les preuves serveur et la permission galerie restent des portes réelles.

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
| Worker R2 + callback + état transactionnel | Oui, local | `cloudflare/src/index.ts` |
| Test noir Worker | PASS local | `cloudflare/test/control_plane_integration.py` |
| Workflow de rendu complet | Préparé | `.github/workflows/render-complete.yml` |
| Paquet déterministe | Outils prêts | `tools/build_t4_integrator_package.py` |
| Déploiement Cloudflare production | **Non** | frontière explicite |

## Différence correcte entre rendu approuvé et rendu client

Le rendu manuel de l’exemplaire approuvé retélécharge le master V3 officiel et conserve son flux H.264 bit pour bit pendant le mux.

Un job client Cloudflare utilise nécessairement les quatre nouvelles captures. GitHub Actions les vérifie, reconstruit le visuel avec le moteur V3 approuvé, puis copie bit pour bit ce nouveau flux pendant le mux. Le hash du master V3 reste alors une référence de design, jamais une fausse identité de fichier.

## Galerie commune

Le dépôt commun identifié est `j9028379-hue/vitrine-video-gabarits`. Son dossier T4 indique encore « À DÉVELOPPER » et ne reflète pas l’implémentation indépendante actuelle.

L’identité GitHub active `vitrinevideo0-bot` possède la permission **READ** sur ce dépôt, contre **ADMIN** sur le dépôt T4. Il est donc possible de préparer une mise à jour et un contrat de passation, mais pas de pousser honnêtement la branche commune. Aucun fork ne sera créé sans autorisation explicite.

Preuve machine : `integration-handoff/T4_GALLERY_HANDOFF_V1.json`.

## Portes avant 100 %

1. commit et push de cette implémentation ;
2. CI complète PASS ;
3. rendu complet GitHub PASS ;
4. pré-Release additive téléchargée et revalidée ;
5. hash du master injecté dans le golden lock et la spécification du paquet ;
6. ZIP déterministe construit deux fois à l’identique ;
7. validation après extraction propre PASS ;
8. mise à jour galerie poussée lorsque la permission le permet ;
9. déploiement Cloudflare déclaré uniquement si endpoint, compte et bucket R2 production sont réellement prouvés.
