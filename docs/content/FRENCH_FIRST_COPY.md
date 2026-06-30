# FRENCH-FIRST PLAYER COPY — Phase 5

## 1. Language policy

French is the canonical player language. German and English are complete maintained translations, not runtime machine translations. Spell names remain the official French names in all locales; surrounding instructions are translated.

Fallback order:

1. selected locale;
2. French;
3. in development, show the missing key beside the French fallback;
4. in production, never expose a raw translation key.

## 2. Core French copy

### Landing

- product name: `Solveur Grougalorasalar`;
- headline: `Une capture d’écran. Un tour vérifié, étape par étape.`;
- explanation: `Le solveur reconstruit le plateau, vous demande de confirmer les éléments incertains, puis calcule une séquence déterministe.`;
- CTA: `Ajouter une capture`;
- paste hint: `Glissez une image ici, choisissez un fichier ou collez depuis le presse-papiers.`;
- privacy note: `La capture est supprimée automatiquement à l’expiration de l’analyse. Aucun compte n’est requis.`;
- scope note: `Version actuelle : combat solo uniquement.`

### Recognition and review

- `Vérification du fichier…`;
- `Repérage de l’arène…`;
- `Alignement de la grille…`;
- `Lecture des piliers et des glyphes…`;
- `L’analyse automatique est terminée. Vérifiez les éléments marqués.`;
- `Ce champ doit être confirmé avant le calcul.`;
- `Confirmer cette détection`;
- `Corriger`;
- `Afficher l’autre possibilité`;
- `L’ensemble des piliers est-il complet ?`;
- `Oui, aucun pilier ne manque`;
- `Budget d’actions non visible`;
- `Saisissez la valeur affichée dans le combat.`

### Solver actions

- review CTA: `Vérifier l’analyse`;
- rule blocker CTA: `Règles non vérifiées`;
- automatic solve status: `Analyse automatique`;
- solving: `Calcul déterministe en cours…`;
- stale: `Le plateau a été modifié. Recalculez le tour.`;
- copy: `Copier les étapes`;
- new analysis: `Analyser le tour suivant`.

### Result sentence templates

- cast to pillar: `{order}. Lancez {spell} sur le pilier {pillarLabel}.`;
- cast to cell: `{order}. Lancez {spell} sur la case indiquée.`;
- end: `{order}. Terminez le tour.`;
- final cell: `Position finale attendue : la case entourée.`;
- Crocoburio: `Aucun glyphe noir ne touche un pilier : Crocoburio avance.`;
- dragon: `Un glyphe noir touche un pilier : Grougalorasalar avance.`;
- recharge: `{spell} récupère une charge.`;
- progress unknown: `La direction de la course est calculée, mais la victoire ou la défaite immédiate ne peut pas être confirmée car la piste n’est pas lisible.`;
- assumption: `Ce résultat dépend d’une règle encore soutenue par une seule source : {statement}.`;

### Domain outcomes

- no safe solution: `Aucune séquence sûre n’a été trouvée avec l’état confirmé et les règles actuellement disponibles.`;
- blocked rule: `Le calcul est bloqué par une règle de combat non vérifiée.`;
- invalid state: `L’état confirmé contient une contradiction. Corrigez les éléments signalés.`;
- capacity: `La recherche a atteint sa limite technique. Ce résultat ne signifie pas qu’aucune solution existe.`

### Privacy and deletion

- ephemeral: `Conserver uniquement pendant cette analyse`;
- quality consent: `Partager une copie pour améliorer la reconnaissance`;
- consent detail: `Le partage est facultatif et séparé de l’utilisation du solveur.`;
- delete: `Supprimer cette analyse`;
- delete confirmation: `La capture, les corrections et le résultat seront supprimés de l’espace temporaire.`;
- deleted: `Analyse supprimée.`

## 3. Tone rules

- command text is literal and executable;
- do not use “l’IA pense”, “probablement” or celebratory filler;
- name the exact missing field or rule;
- give one next action per blocker;
- use `case`, not raw `(x,y)`, in normal instructions;
- use `pilier`, `glyphe noir`, `glyphe blanc`, `charge` consistently;
- never imply guaranteed success when a rule assumption remains.

## 4. Translation QA

Every shipping key must exist in `fr`, `de` and `en`. Tests fail on missing placeholders, mismatched interpolation variables, HTML in plain-text keys, or translations that change a stable reason-code meaning.
