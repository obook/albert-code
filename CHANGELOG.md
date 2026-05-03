# Journal des modifications

Toutes les modifications notables de ce projet sont consignées dans ce fichier.

Le format suit [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) et le projet adhère au [versionnage sémantique](https://semver.org/spec/v2.0.0.html).

## [Non publié]

### Ajouté

- Récupération des quotas de l'API Albert via `GET /v1/me/info` (module `albert_code/core/llm/quota.py`).
- Commandes slash `/limits` (et alias `/quota`) qui affichent les rpm / rpd / tpm / tpd par routeur sous forme de tableau Markdown, ainsi que le palier documenté EXP / PROD du modèle actif quand il est connu.
- Table statique `DOCUMENTED_MODEL_LIMITS` (`quota.py`) qui consigne les paliers Albert publiés sur https://albert.sites.beta.gouv.fr/prices/ pour les modèles `gpt-oss-120b`, `Qwen3-Coder-30B`, `mistral-small-3.2-24b` et `ministral-3-8b`. Permet de comparer le compte courant aux paliers documentés sans appel API supplémentaire.
- Commande slash `/rpm` : jauge en direct de la consommation RPM et TPM du modèle actif sur la fenêtre glissante de 60 s, avec barre de progression `[###···]`, débounce courant, éventuel `Retry-After` actif et indication de la source de la limite (`documented EXP tier` ou `max across routers`).
- Limiteur côté client adaptatif (`albert_code/core/llm/throttling.py`) : fenêtres glissantes de 60 s pour les requêtes et les tokens, mise en attente avant d'atteindre la limite `rpm` / `tpm` la plus permissive. Pour les modèles présents dans la table documentée, le throttler utilise désormais la limite EXP propre au modèle plutôt que le maximum compte-tout-routeur, ce qui évite par exemple de prendre 500 rpm (routeur embeddings) pour un modèle de chat à 50 rpm.
- Débounce global pré-appel : un délai minimum `60 / rpm + 0,05 s` est imposé entre deux appels HTTP, en plus de la fenêtre glissante. Inspiré du `_wait_for_slot` du fork [AlbertCode](https://github.com/XenocodeRCE/AlbertCode) de Simon Roux.
- Détection des 429 terminaux (quota journalier `rpd` ou `tpd` épuisé, motif `per day` dans le corps de réponse) : nouvelle exception `TerminalRateLimitError` levée par `_handle_429`, qui contourne `async_retry` et fait remonter immédiatement l'erreur au lieu de gaspiller deux retries supplémentaires sur un quota qui ne se rétablira qu'au reset de minuit UTC.
- Coupure des retries 429 quand l'auto-fallback est armé : `Throttler.is_fallback_trigger_reached(model_alias)` (getter pur) permet à `_handle_429` de lever `TerminalRateLimitError(reason="fallback-armed")` dès que le seuil de bascule est atteint, plutôt que de laisser `async_retry` consommer un troisième essai sur le modèle primaire.
- Persistance du dernier 429 daily-quota dans `~/.albert-code/throttle_state.json` (module `albert_code/core/llm/quota_state.py`). Au prochain démarrage, le bandeau d'accueil avertit que le modèle concerné est probablement encore saturé jusqu'au reset UTC suivant.
- Avertissement de quota au démarrage de la TUI : combine la persistance ci-dessus et une estimation en direct calculée à partir de `GET /v1/me/usage` (somme des `prompt_tokens` du jour pour le modèle actif, comparée au `tpd` documenté). Seuils d'alerte à 80 % et 95 %.
- Auto-fallback sur 429 répétés : après 2 réponses 429 consécutives sur un modèle, l'agent bascule sur son `ModelConfig.fallback_model` pendant 60 s puis restaure le modèle initial. Mapping Albert par défaut : `albert-code` -> `albert-large`.
- Commande slash `/fallback` pour activer ou désactiver la stratégie d'auto-fallback (clé de configuration `auto_fallback_enabled`).
- Toasts d'interface lors des transitions d'auto-fallback (activation, restauration).
- Parser incrémental d'appels d'outils XML pour les réponses Qwen en streaming (`XmlToolCallStreamParser`) ; restaure le streaming Albert qui était auparavant bridé par `force_non_streaming`.
- Champ de provider `streaming_xml_tool_calls` pour activer ce parser de flux XML.
- Logo tricolore ASCII `AlbertLogo` (remplace le petit widget de drapeau français).
- Indicateur de modèle en pied d'interface affichant `⚙ alias (nom-court)` pour le modèle actif.
- Lanceurs `albert-code.sh` et `albert-code.bat` qui amorcent un venv Python et installent en mode editable (avec un marqueur SHA-256 sur `pyproject.toml` pour rafraîchir les dépendances en cas de changement).

### Changé

- Build, installation et CI n'utilisent plus `uv`. Le projet s'installe désormais via `python -m venv` standard puis `pip install -e .`. Workflows, `action.yml` et scripts d'installation ont été portés.
- `textual` épinglé en `>=7.4.0,<8.1` pour conserver le thème `textual-ansi` (renommé en `ansi-dark` en amont à partir de la 8.1).
- `OpenAIAdapter.parse_response` ne tente plus l'extraction XML sur les chunks de streaming ; le parser incrémental les prend en charge.
- Les `tool_calls` natifs non-streamés renvoyés sans `index` (Albert / vLLM) sont post-traités pour recevoir un index séquentiel, ce qui corrige `Tool call chunk missing index` lors de l'accumulation.
- Le message d'erreur de rate limit dans l'interface affiche maintenant le `detail` brut renvoyé par Albert (par exemple `2460000 input tokens per day exceeded`) et distingue visuellement les 429 transitoires des quotas journaliers épuisés (avec recommandation explicite de changer de modèle via `/config`).
- `Throttler.usage_snapshot()` renvoie désormais une dataclass typée `UsageSnapshot` plutôt qu'un dictionnaire, pour fiabiliser la consommation par la jauge `/rpm`.
- L'auto-continue est désactivé quand le modèle renvoie une réponse vide (pas de contenu, pas d'appel d'outil) : retenter immédiatement gaspillait un appel pleine-conversation sans chance de produire un résultat différent.
- Bandeau d'accueil de la TUI : le bloc d'informations à droite est aligné sur la ligne de pied du logo (baseline) au lieu d'être centré verticalement.

### Corrigé

- Parsing de `/v1/me/info` : `id` peut être renvoyé comme entier par Albert ; converti en chaîne via un `field_validator` Pydantic. `extra="ignore"` permet au modèle d'accepter tout champ supplémentaire sans casser.
- `get_active_model()` résout désormais par alias et tombe en repli sur la recherche par `name`, ce qui permet aux configurations qui stockent l'identifiant complet du modèle dans `active_model` d'être résolues correctement.
- Le corps des réponses 429 est maintenant journalisé dans `~/.albert-code/logs/albert-code.log`, ce qui permet d'identifier rétroactivement quel quota précis a déclenché un blocage.
- Réinitialisation des throttlers entre les tests (`tests/conftest.py`) pour éviter qu'un compteur 429 d'un test précédent ne contamine le suivant.

## [2.3.0] - 2026-02-27

### Ajouté

- Commande `/resume` pour choisir la session à reprendre.
- Outils web search et web fetch pour rechercher et récupérer du contenu web.
- Support du sampling MCP : les serveurs MCP peuvent demander des complétions LLM via le protocole de sampling.
- Cache de découverte des serveurs MCP (`MCPRegistry`) : survit aux changements d'agent sans redécouvrir les serveurs inchangés.
- Mode chat pour ACP (`session/set_config_options` avec `mode=chat`).
- Support `session/set_config_options` côté ACP pour changer de mode et de modèle.
- Streaming des appels d'outils : les arguments d'appel d'outil sont désormais streamés de façon incrémentale dans l'interface.
- Indicateur de notification dans la CLI : sonnerie du terminal et changement de titre de fenêtre quand une action est requise ou achevée.
- Traces des sous-agents enregistrées dans le sous-dossier `agents/` du répertoire de session parent.
- Détection de l'IDE dans la télémétrie `new_session`.
- Découverte des agents, outils et compétences dans les sous-dossiers des répertoires de confiance (support des monorepos).
- Infrastructure de tests E2E pour la TUI CLI.

### Changé

- Prompts système réécrits pour améliorer le comportement du modèle (workflow en 3 phases Orient / Plan / Execute, règles de concision).
- Affichage des appels d'outils refactorisé avec les modèles `ToolCallDisplay` / `ToolResultDisplay` et personnalisation d'interface par outil.
- Pipeline de middlewares qui remplace le pattern observateur pour les injections de messages système.
- Gestion des permissions améliorée pour `write_file`, `read_file`, `search_replace` (globs allowlist / denylist, détection des chemins hors répertoire courant).
- Interface de configuration de proxy mise à jour avec un assistant guidé en bas de panneau.
- Transitions de couleur plus fluides dans l'animation de chargement CLI.
- Suppression des classes d'état d'outil mortes (`Grep`, `ReadFile`, `WriteFile`).

### Corrigé

- Le changement d'agent (Shift+Tab) ne fige plus l'interface (déplacé dans un thread worker).
- Les messages assistant vides ne sont plus affichés.
- Les résultats d'outils sont renvoyés au LLM dans l'ordre correspondant aux appels d'outils.
- L'auto-scroll est suspendu quand l'utilisateur a remonté ; reprend en bas.
- Gestion des retries et des timeouts dans le backend Mistral (stratégie de backoff, timeout configurable).

### Retiré


## [2.2.1] - 2026-02-18

### Ajouté

- Plusieurs stratégies de copie dans le presse-papiers : OSC52 d'abord, puis fallback pyperclip quand le presse-papiers système est disponible (par exemple GUI locale, SSH sans OSC52).
- Ctrl+Z pour mettre Vibe en arrière-plan.

### Changé

- Performances améliorées autour du streaming et du défilement.
- Le surveillance de fichiers est désormais opt-out par défaut ; opt-in via la configuration.
- Montée de version de Textual dans les dépendances.
- Style du code inline : gras jaune sur fond transparent pour une meilleure lisibilité.

### Corrigé

- Bandeau : synchronisation du compteur de skills après le mount initial de l'application (corrige un compteur erroné dans certains cas).
- Résultats d'outils repliés : suppression des sauts de ligne lors de la troncature pour retirer une ligne vide superflue.
- Widget de tokens de contexte : préservation des listeners de stats à travers `/clear` pour que le pourcentage de tokens se mette à jour correctement.
- Vertex AI : mise en cache des credentials pour éviter de bloquer la boucle d'événements à chaque requête LLM.
- Outil bash : suppression de `NO_COLOR` de l'environnement du sous-processus pour réparer les tests de snapshot et la sortie colorée.


## [2.2.0] - 2026-02-17

### Ajouté

- Support de Google Vertex AI.
- Télémétrie : événements d'interaction utilisateur et d'usage des outils envoyés vers le datalake (configurable via `enable_telemetry`).
- Découverte des skills depuis `.agents/skills/` (standard Agent Skills) en plus de `.vibe/skills/`.
- ACP : `session/load` et `session/list` pour charger et lister les sessions.
- Nouveaux prompts de comportement de modèle (CLI et explore).
- Assistant Proxy (PoC) pour la CLI et pour ACP.
- Documentation de la configuration de proxy.
- Documentation pour le registre ACP JetBrains.

### Changé

- Dossiers de confiance : la présence de `.agents` est désormais considérée comme un contenu digne de confiance.
- Gestion des logs mise à jour.
- `cryptography` épinglé en `>=44.0.0,<=46.0.3` ; uv sync pour cryptography.

### Corrigé

- Auto-scroll lors du basculement vers la zone de saisie.
- MCP stdio : redirection de stderr vers le logger pour éviter les sorties indésirables sur la console.
- Alignement des versions minimales de `pyproject.toml` avec `uv.lock` pour les installations pip.
- Injection de middleware : utilisation de messages utilisateur autonomes plutôt que de muter des messages déjà envoyés.
- Annulation du bump de cryptography 46.0.5 pour la compatibilité.
- Version de bandeau épinglée dans les tests de snapshot d'interface pour la stabilité.


## [2.1.0] - 2026-02-11

### Ajouté

- Chargement incrémental des sessions longues : fenêtrage (20 messages), bouton "Load more" pour récupérer les messages plus anciens, défilement vers le bas à la reprise.
- Support ACP du thinking (agent-client-protocol 0.8.0).
- Support des chemins FIFO pour le fichier d'environnement.

### Changé

- **Refonte de l'interface :** nouvelle apparence et nouvelle disposition pour la CLI.
- Optimisations de l'interface Textual : ChatScroll pour réduire les recalculs de style, VerticalGroup pour les messages, layout en flux pour les blocs en streaming, requêtes DOM mises en cache.
- Montée de version d'agent-client-protocol en 0.8.0.
- Utilisation de la date UTC pour les horodatages.
- Améliorations du comportement du presse-papiers.
- Documentation mise à jour pour les discussions GitHub.
- Bandeau de mise à niveau Pro rendu moins proéminent.

### Corrigé

- Compteur de tokens dans l'interface inexact dans certains cas.
- Les surcharges de prompt d'agent étaient ignorées.
- Configuration du terminal : ne plus écraser la configuration Wezterm.

### Retiré

- Module de thème terminal hérité et widget d'indicateur d'agent.
- Écran d'onboarding de sélection de thème (remplacé par la refonte).


## [2.0.2] - 2026-01-30

### Ajouté

- Les variables d'environnement peuvent désormais être surchargées par des fichiers dotenv.
- Affichage de messages de rate limit personnalisés selon le type de plan.

### Changé

- Message d'offre de plan rendu plus discret dans l'interface.
- Scan de la dernière session accéléré et validation durcie.
- Configuration pytest-xdist mise à jour pour planifier des chunks de tests unitaires.

### Corrigé

- Suppression des doublons de messages dans les sessions persistées.
- Outil bash ACP : passage de la chaîne de commande complète pour les commandes chaînées.
- Le prompt d'agent global n'était pas chargé correctement.
- Ne plus proposer de "reprendre" quand il n'y a rien à reprendre.


## [2.0.1] - 2026-01-28

### Corrigé

- Problèmes d'encodage sous Windows.


## [2.0.0] - 2026-01-27

### Ajouté

- Support des sous-agents.
- Outil AskUserQuestion pour la saisie utilisateur interactive.
- Commandes slash personnalisées via les skills.
- Affichage du message "What's new" lors d'une mise à jour de version.
- Fonctionnalité d'auto-update.
- Variables d'environnement et timeout pour les serveurs MCP.
- Support des raccourcis d'éditeur.
- Support de Shift+Enter pour VS Code Insiders.
- Propriété d'identifiant de message pour les messages.
- Notification client des événements de compaction.
- Support de debugpy pour le débogage macOS.

### Changé

- Système de modes refactorisé en Agents.
- Standardisation des managers.
- Prompt système amélioré.
- Stockage de session mis à jour pour séparer les métadonnées des messages.
- Utilisation de l'environnement shell pour déterminer le shell dans l'outil bash.
- Gestion étendue de la saisie utilisateur.
- Montée de version d'agent-client-protocol en 0.7.1.
- Refactorisation de l'interface pour exiger un AgentLoop à la construction de VibeApp.
- README mis à jour avec la nouvelle configuration des serveurs MCP.
- Lisibilité améliorée de la sortie de l'outil AskUserQuestion.

### Corrigé

- Utilisation de `ensure_ascii=False` pour tous les `json.dumps`.
- Suppression des fichiers temporaires de session de longue durée.
- Le prompt système est ignoré lors de la sauvegarde et du chargement des messages de session.
- Gestion du timeout de l'outil bash.
- Presse-papiers : pas de parsing de markup sur les textes sélectionnés.
- Imports canoniques.
- Suppression du dernier message utilisateur lors de la compaction.
- Pause du timer d'outil pendant l'attente d'une action utilisateur.

### Retiré

- Support de `instructions.md`.
- Réglage `workdir` dans le fichier de configuration.


## [1.3.5] - 2026-01-12

### Corrigé

- Outil bash non découvert par vibe-acp.

## [1.3.4] - 2026-01-07

### Corrigé

- Markup dans les messages clignotants.
- Robustesse autour de Bash et de AGENTS.md.
- Permissions explicites pour les workflows GitHub Actions.
- Performances de rendu améliorées dans les sessions longues.

## [1.3.3] - 2025-12-26

### Corrigé

- Problèmes de désynchronisation de la configuration.

## [1.3.2] - 2025-12-24

### Ajouté

- Champ de reasoning définissable par l'utilisateur.

### Corrigé

- Problème de rendu du spinner.

## [1.3.1] - 2025-12-24

### Corrigé

- Crash lors de la reprise de conversation.
- Flake Nix qui n'exporte plus python.

## [1.3.0] - 2025-12-23

### Ajouté

- Support d'agentskills.io.
- Support du reasoning.
- Support des thèmes natifs du terminal.
- Templates de tickets pour les rapports de bug et les demandes de fonctionnalité.
- Mise à jour automatique de l'extension Zed lors de la création d'une release.

### Changé

- Système ToolUI amélioré avec un meilleur rendu et une meilleure organisation.
- Utilisation d'actions épinglées dans les workflows CI.
- Suppression de la migration de configuration 100k -> 200k tokens.

### Corrigé

- Mode `-p` qui auto-approuve les appels d'outils.
- Crash lors d'un changement de mode.
- Certains cas où la copie dans le presse-papiers ne fonctionnait pas.

## [1.2.2] - 2025-12-22

### Corrigé

- Suppression de code mort.
- Artefacts attachés automatiquement à la release.
- Refactorisation de l'agent post-streaming.

## [1.2.1] - 2025-12-18

### Corrigé

- Message d'erreur amélioré lors de l'exécution dans le répertoire home.
- Pas d'affichage du workflow de dossier de confiance dans le répertoire home.

## [1.2.0] - 2025-12-18

### Ajouté

- Système de modes modulaire.
- Mécanisme de dossiers de confiance pour les répertoires `.vibe` locaux.
- Documentation publique de la configuration de vibe-acp pour Zed, JetBrains et Neovim.
- Drapeau `--version`.

### Changé

- Interface améliorée selon les retours.
- Suppression des logs et flushs inutiles pour de meilleures performances.
- Mise à jour de Textual.
- Mise à jour du flake Nix.
- Automatisation de l'attachement des binaires aux releases GitHub.

### Corrigé

- Prévention des segmentation faults à la sortie via l'arrêt propre des thread pools.
- Espacement excessif avec les messages de l'assistant.

## [1.1.3] - 2025-12-12

### Ajouté

- Méthodes `copy_to_clipboard` supplémentaires pour couvrir tous les cas.
- Bindings pour faire défiler l'historique du chat.

### Changé

- Configuration assouplie pour accepter des entrées supplémentaires.
- Suppression des stats inutiles des événements de l'assistant.
- Actions de défilement améliorées pendant le streaming.
- Plus d'une vérification de mise à jour par jour exclue.
- Utilisation de PyPI dans le notifier de mise à jour.

### Corrigé

- Gestion des permissions d'outils pour l'option "allow always" en ACP.
- Faille de sécurité : prévention des injections de commande dans la gestion de prompt de la GitHub Action.
- Problèmes avec vLLM.

## [1.1.2] - 2025-12-11

### Changé

- Méthode d'authentification `terminal-auth` ajoutée à l'agent ACP uniquement si le client la prend en charge.
- En-tête `user-agent` corrigé pour le backend Mistral via un hook du SDK.

## [1.1.1] - 2025-12-10

### Changé

- Ajout de `include_commit_signature` dans `config.toml` pour désactiver la signature des commits.

## [1.1.0] - 2025-12-10

### Corrigé

- Crash dans certains cas rares lors d'un copier-coller.

### Changé

- Longueur de contexte étendue de 100k à 200k.

## [1.0.6] - 2025-12-10

### Corrigé

- Étapes manquantes dans le script `bump_version`.
- Déplacement de `pytest-xdist` dans les dépendances de développement.
- Prise en compte de la configuration pour le timeout de bash.

### Changé

- Performances de Textual améliorées.
- README amélioré :
  - instructions d'installation Windows clarifiées ;
  - référence du prompt système par défaut mise à jour ;
  - configuration des permissions d'outils MCP documentée.

## [1.0.5] - 2025-12-10

### Corrigé

- Streaming corrigé sur l'adaptateur OpenAI.

## [1.0.4] - 2025-12-09

### Changé

- Renommage de l'agent dans `distribution/zed/extension.toml` en albert-code.

### Corrigé

- Icône et description corrigées dans `distribution/zed/extension.toml`.

### Retiré

- Suppression du fichier `.envrc`.

## [1.0.3] - 2025-12-09

### Ajouté

- Lien symbolique LICENCE dans `distribution/zed` pour la compatibilité avec le processus de release de l'extension Zed.

## [1.0.2] - 2025-12-09

### Corrigé

- Flux de configuration corrigé pour les builds de vibe-acp.

## [1.0.1] - 2025-12-09

### Corrigé

- Notification de mise à jour corrigée.

## [1.0.0] - 2025-12-09

### Ajouté

- Première version publique.
