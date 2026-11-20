# T4 — quatre voix françaises comparables

Ce lot archive quatre voix masculines publicitaires françaises proposées pour `RESTAURATION-T4`.

## Comparabilité

- même texte pour les quatre voix ;
- fichiers d'écoute mono 48 kHz ;
- cible −20 LUFS, tolérance ±0,15 LU ;
- crête vraie ≤ −3 dBTP ;
- aucune accélération, aucun ralentissement et aucun changement de durée ;
- les identifiants internes sont masqués par les lettres A à D dans l'interface d'écoute.

## Porte propriétaire

La porte propriétaire est clôturée : **VOIX-B / `voice-07`** a été sélectionnée explicitement le 20 novembre 2026. Le silence ne vaut jamais approbation ; les quatre autres fichiers restent des preuves comparables et ne changent pas la sélection finale.

## Reproduction

```bash
python3 normalize_candidates.py
sha256sum -c SHA256SUMS.txt
```
