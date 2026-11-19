# T4 V1 — Adaptation historique des références A+B+C+D

> **Statut : remplacé par la correction V2.** Le propriétaire a jugé le rendu V1 trop exagéré. Ce document reste une trace historique et n’est plus le contrat actif. Voir `docs/TRANSITIONS_NATURELLES_V2.md`.

La décision propriétaire V1 validait une fusion contrôlée, pas une copie de template.

- **A — PuzzleGlitch** : structure les mosaïques et les révélations par blocs.
- **B — Grid Style** : organise plusieurs fenêtres temporelles dans des grilles mobiles.
- **C — Shake Transition** : apporte les impacts brefs et les cassures rectangulaires.
- **D — Glitch effect shake** : apporte les micro-glitchs de une à trois images.

## Garde-fous du moteur

- chaque case montre une fenêtre temporelle distincte ou la scène adjacente ;
- aucun média, texte, son, watermark ou univers graphique CapCut n’est copié ;
- aucun trait séparateur bleu/cyan ;
- aucune barre de couleur unie utilisée comme transition ;
- impacts courts uniquement, jamais de vibration permanente ;
- protection du visage pendant la dégustation ;
- les 90 dernières images de S4 n’ont aucun effet ;
- le candidat silencieux ne contient ni texte ni piste audio.

Le calendrier déterministe de 48 événements et les paramètres moteur se trouvent dans `reverse-engineering/T4_TRANSITIONS_30S.json`. Les valeurs numériques sont des décisions moteur destinées au visionnage de validation, pas des mesures exactes des previews CapCut.
