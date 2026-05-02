# Déclaration d'accessibilité - Albert Code

**Date de mise à jour :** 2026-05-02

## État de conformité

Albert Code est une application en ligne de commande dotée d'une interface texte (TUI). Elle est en **conformité partielle** avec le RGAA 4.1 (Référentiel Général d'Amélioration de l'Accessibilité), niveau AA, dans la mesure où le RGAA s'applique à ce type d'interface.

L'environnement d'exécution principal étant un émulateur de terminal, l'accessibilité dépend conjointement de l'application, du terminal et du lecteur d'écran utilisé.

## Technologies utilisées

- Python 3.12+
- Textual (framework TUI) pour l'interface interactive
- ANSI / SGR pour le rendu coloré
- Markdown pour le formatage des messages

## Environnements de test

| Terminal | Système | Lecteur d'écran |
|----------|---------|-----------------|
| GNOME Terminal | Linux | Orca |
| Konsole | Linux | Orca |
| iTerm2 | macOS | VoiceOver |
| Windows Terminal | Windows | Narrator / NVDA |

## Critères vérifiés

### Couleurs et contraste

| Critère | Statut | Détail |
|---------|--------|--------|
| Contraste texte / fond >= 4.5:1 | Conforme | Palette adaptée aux thèmes clair et sombre du terminal. Le logo tricolore utilise un bleu plus clair pour rester lisible sur fond sombre. |
| Information non véhiculée uniquement par la couleur | Conforme | Les états (succès, erreur, en cours) utilisent un libellé textuel en plus de la couleur. Les boutons d'approbation sont étiquetés explicitement (`Approuver`, `Refuser`). |
| Respect des thèmes du terminal | Conforme | Albert Code respecte les couleurs ANSI du terminal hôte. Les utilisateurs ayant configuré un thème à fort contraste le conservent. |

### Navigation au clavier

| Critère | Statut | Détail |
|---------|--------|--------|
| Toutes les fonctionnalités accessibles au clavier | Conforme | Aucune action ne nécessite la souris. La liste complète des raccourcis est documentée dans `COMMANDES.md`. |
| Focus visible | Conforme | Les widgets Textual mettent en évidence le focus (bordure et inversion vidéo). |
| Ordre de tabulation cohérent | Conforme | L'ordre suit la disposition visuelle dans les modales (approbation, question, picker de session, configuration). |
| Échappatoire dans les modales | Conforme | `Échap` ferme tous les dialogues et restitue le focus à la zone de saisie. |

### Structure et étiquetage

| Critère | Statut | Détail |
|---------|--------|--------|
| Étiquettes des champs de saisie | Conforme | La zone de saisie principale, les champs du dialogue de configuration et le picker de session disposent de libellés explicites. |
| Annonces des changements d'état | Partiellement conforme | Les événements importants (réponse de l'agent, approbation requise, erreur) sont rendus textuellement. Les annonces dynamiques aux lecteurs d'écran via Textual restent à valider en pratique. |
| Messages d'erreur explicites | Conforme | Les erreurs (clé API manquante, dossier non approuvé, quota atteint) sont affichées en clair avec une suggestion d'action. |

### Saisie et édition

| Critère | Statut | Détail |
|---------|--------|--------|
| Édition multiligne | Conforme | `Shift+Enter` ou `Ctrl+J` pour insérer un saut de ligne ; `Ctrl+G` pour basculer vers l'éditeur externe défini par `$EDITOR`. |
| Historique navigable | Conforme | Les flèches haut / bas rappellent les saisies précédentes. |
| Auto-complétion | Conforme | Les chemins (`@chemin`) et les commandes slash (`/`) sont auto-complétés via une liste navigable au clavier. |
| Confirmation avant action irréversible | Conforme | Toute exécution shell, écriture ou modification de fichier passe par un dialogue d'approbation explicite (sauf profils auto-approve choisis par l'utilisateur). |

### Sortie et lecture

| Critère | Statut | Détail |
|---------|--------|--------|
| Mode programmatique non graphique | Conforme | L'option `-p / --prompt` produit une sortie textuelle pure (text / JSON / streaming JSON) sans interface, exploitable par un lecteur d'écran ou un script. |
| Désactivation des effets | Partiellement conforme | Le rendu Markdown et les spinners sont actifs par défaut. Une variable d'environnement permet de désactiver les couleurs (`NO_COLOR`). |
| Largeur de terminal | Conforme | Le rendu s'adapte aux terminaux étroits ; les blocs de code défilent horizontalement plutôt que de couper. |

## Mode accessible recommandé

Pour les utilisateurs de lecteurs d'écran, deux pistes :

1. **Mode programmatique** : `albert-code -p "votre prompt" --output text` produit une réponse textuelle linéaire, sans TUI, idéale avec un lecteur d'écran.
2. **Mode interactif épuré** : exporter `NO_COLOR=1` désactive les codes couleur ; le rendu reste lisible.

## Axes d'amélioration

- Test approfondi avec Orca, NVDA et VoiceOver pour valider les annonces dynamiques de Textual.
- Documentation d'un mode « lecteur d'écran » explicite (combinaison de variables d'environnement et d'options).
- Ajout d'un raccourci pour basculer entre rendu Markdown enrichi et rendu texte brut.
- Captures audio / vidéo d'usage avec lecteur d'écran à fournir avec la documentation.

## Contact

Pour signaler un problème d'accessibilité ou suggérer une amélioration : ouvrir un ticket sur le dépôt GitHub du projet.
