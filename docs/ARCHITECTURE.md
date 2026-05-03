# Architecture - Albert Code

## Vue d'ensemble

Albert Code est un agent CLI de programmation propulsé par l'API Albert, l'endpoint compatible OpenAI opéré par le gouvernement français, avec un support optionnel pour Anthropic, Mistral, Vertex AI et tout backend compatible OpenAI. Le projet est écrit en Python (>=3.12) et expose deux points d'entrée : une interface en terminal interactive fondée sur Textual (`albert-code`) et un serveur Agent Client Protocol (`albert-acp`) utilisé par les intégrations IDE telles que Zed.

Le code suit une architecture en couches avec une séparation stricte entre la logique métier pure, les adaptateurs de présentation et les adaptateurs de protocole.

## Cartographie des modules

Le paquet `albert_code/` se découpe en quatre sous-paquets de premier niveau, plus un assistant de configuration initiale. La logique pure vit dans `core/` ; les couches utilisateur (`cli/`, `acp/`) en dépendent, mais jamais l'inverse.

```
albert_code/
  core/                              (logique pure, aucun import UI / protocole)
    agent_loop.py                    Boucle principale de l'agent (orchestration des tours)
    middleware.py                    Pipeline de middlewares de conversation
    config.py                        Pydantic settings, source unique de vérité
    system_prompt.py                 Assemblage du prompt système
    types.py                         Types du domaine (LLMMessage, AgentStats, ...)
    output_formatters.py             Formatage des blocs de code et du markdown
    programmatic.py                  API non interactive (-p)
    proxy_setup.py                   Configuration du proxy HTTP
    logger.py                        Journalisation structurée
    utils.py                         Utilitaires divers (heure UTC, correspondance de noms)

    llm/                             Abstraction des backends LLM
      backend/
        base.py                      Protocole APIAdapter
        factory.py                   BackendFactory (sélection du fournisseur)
        anthropic.py                 API native Anthropic
        mistral.py                   API Mistral
        vertex.py                    Google Vertex AI
        generic.py                   Compatible OpenAI (Albert, etc.)
      types.py                       LLMMessage, ChunkEvent
      message_utils.py               Aides à la manipulation des messages
      format.py                      Résolution des appels d'outils
      quota.py                       Récupération des quotas Albert (/v1/me/info, /v1/me/usage),
                                     table statique des paliers EXP / PROD documentés
      quota_state.py                 Persistance du dernier 429 daily-quota dans
                                     ~/.albert-code/throttle_state.json
      throttling.py                  Limitation de débit côté client (rolling 60 s + débounce
                                     pré-appel), auto-fallback sur 429 répétés, snapshot pour
                                     la jauge /rpm
      exceptions.py                  BackendError, TerminalRateLimitError (429 fail-fast),
                                     dépassement de contexte, échecs d'authentification

    tools/                           Cadre d'outils et implémentations
      base.py                        BaseTool, ToolStreamEvent
      manager.py                     Découverte, indexation et dispatch des outils
      builtins/                      Bash, Read, Write, Edit, Grep, Glob,
                                     WebSearch, WebFetch, AskUserQuestion,
                                     Task, Todo
      mcp/                           Intégration Model Context Protocol
        registry.py                  Registre des serveurs MCP (stdio + HTTP)
        tools.py                     Wrappers proxy, listing des outils
      mcp_sampling.py                Gestionnaire d'échantillonnage MCP
      ui.py, utils.py                Aides au rendu des outils

    skills/                          Système de plugins de compétences
      manager.py                     Découverte des compétences (globales + locales au projet)
      models.py, parser.py           Parsing du frontmatter

    agents/                          Profils d'agent (default, plan, ...)

    session/
      session_logger.py              Journal de conversation en append seulement
      session_loader.py              Désérialisation d'une session passée
      session_migration.py           Mise à jour du schéma

    auth/
      crypto.py                      Chiffrement symétrique des identifiants stockés
      github.py                      OAuth GitHub (utilisé par téléport)

    paths/
      config_paths.py                Répertoire de configuration XDG / macOS / Windows
      global_paths.py                Sessions, compétences, prompts, chemin du .env
      local_config_walk.py           Recherche de .vibe.toml local au projet

    teleport/                        Sandbox distant (Vibe Nuage)
      teleport.py, nuage.py, git.py

    telemetry/
      send.py                        Événements anonymes opt-in

    autocompletion/                  Indexation de chemins et fichiers pour les mentions @
    prompts/                         Prompts système intégrés

  cli/                               Interface terminal interactive (Textual)
    entrypoint.py                    Argparse, --setup, --install, --resume
    cli.py                           Orchestration CLI de haut niveau
    commands.py                      Registre des commandes slash
    history_manager.py               Historique de saisie persistant
    clipboard.py                     Copie multiplateforme
    terminal_setup.py                Détection des capacités du terminal
    autocompletion/                  Auto-complétion des chemins et des commandes slash
    update_notifier/                 Vérification des mises à jour (ports / adapters)
      ports/                         Passerelle de mise à jour, dépôt de cache
      adapters/                      Passerelle GitHub, passerelle PyPI, cache filesystem
    textual_ui/
      app.py                         AlbertApp (App Textual racine)
      handlers/event_handler.py      Pont entre saisie utilisateur et boucle d'agent
      external_editor.py             Intégration $EDITOR
      ansi_markdown.py               Rendu Markdown vers ANSI pour le terminal
      windowing/                     Pagination de l'historique des messages
      notifications/                 Notifications de bureau (ports / adapters)
      widgets/
        messages.py                  Messages utilisateur, assistant, bash
        tools.py, tool_widgets.py    Rendu des appels d'outils, interface d'approbation
        chat_input/                  Saisie multiligne avec popup d'auto-complétion
        approval_app.py              Modale : approbation d'outil
        question_app.py              Modale : ask-user-question
        config_app.py                Modale : éditeur de configuration
        session_picker.py            Modale : reprise d'une session passée
        banner.py, loading.py,
        spinner.py, status_message.py
        teleport_message.py
        context_progress.py          Jauge d'utilisation des tokens

  acp/                               Serveur Agent Client Protocol (pont IDE)
    entrypoint.py                    Démarrage du serveur ACP
    acp_agent_loop.py                Implémentation AcpAgent
    acp_logger.py                    Adaptateur de journal des messages ACP
    utils.py                         Aides à la construction des messages ACP
    tools/
      base.py                        Wrapper BaseAcpTool
      builtins/                      Bash, Read, Write, SearchReplace, Todo
                                     adaptés pour ACP
      session_update.py              Synchronisation de session ACP

  setup/                             Première expérience utilisateur
    onboarding/                      Cadre de l'assistant + écrans
    trusted_folders/                 Dialogue de confiance des dossiers

tests/                               Suite pytest
  snapshots/                         Tests de snapshot Textual
  ...
```

### Règles de couches

- `core/` n'importe ni `textual`, ni `acp`, ni quoi que ce soit de `cli/`, `acp/` ou `setup/`.
- `cli/` importe librement `core/` ; `acp/` importe librement `core/`. Aucun des deux n'importe l'autre.
- `setup/` n'est utilisé que par les points d'entrée, avant le démarrage de la boucle d'agent.
- Les points de sortie réseau sont concentrés dans `core/llm/backend/*`, `core/tools/builtins/webfetch.py`, `core/tools/builtins/websearch.py`, `core/tools/mcp/*`, `core/teleport/nuage.py`, `core/telemetry/send.py` et `cli/update_notifier/adapters/*`.

## Points d'entrée

Les deux points d'entrée sont déclarés dans `pyproject.toml` :

```
[project.scripts]
albert-code = "albert_code.cli.entrypoint:main"
albert-acp  = "albert_code.acp.entrypoint:main"
```

### `albert-code` (CLI interactif)

`cli/entrypoint.py` analyse les arguments, exécute l'onboarding au premier lancement si nécessaire, valide le statut "dossier de confiance" du répertoire courant, construit une `VibeConfig`, puis :

- lance `AlbertApp` (la TUI Textual) pour l'usage interactif, ou
- exécute la boucle programmatique (`core/programmatic.py`) lors d'un appel `-p / --prompt`, en auto-approuvant tous les outils et en produisant une sortie exploitable par script (`text` / `json` / `streaming`).

### `albert-acp` (serveur ACP)

`acp/entrypoint.py` démarre un serveur ACP qui lit `initialize` / `prompt` / `set_session_model` sur stdio, délègue chaque prompt à `acp/acp_agent_loop.py`, et réutilise les mêmes briques `core` (gestionnaire d'outils, backends LLM, middlewares) emballées dans des adaptateurs `BaseAcpTool` qui émettent des mises à jour de session ACP.

## Flux de données

### Tour interactif (CLI)

```
Saisie dans le widget chat-input
  -> textual_ui/handlers/event_handler.py
  -> core/agent_loop.py (tour suivant)
       -> pipeline de middlewares (alerte de contexte, plafond de prix,
                                   limite de tours, auto-compaction,
                                   garde lecture seule, focus todo)
       -> core/llm/format.py (construction des messages + définitions d'outils)
       -> core/llm/backend/<fournisseur>.py (point de sortie réseau unique)
       -> chunks en streaming
            -> widgets Textual (rendu incrémental)
       -> appels d'outils extraits de la réponse
            -> le manager dispatche vers builtin / MCP / skill
            -> modale d'approbation (sauf si le profil d'agent auto-approuve)
            -> résultat de l'outil renvoyé au LLM
  -> session/session_logger.py (ajout du message et des stats sur disque)
```

### Tour ACP (IDE)

```
IDE -> requête ACP (JSON-RPC sur stdio)
  -> acp/entrypoint.py
  -> acp/acp_agent_loop.py
       -> mêmes core/agent_loop.py et core/tools / core/llm
       -> événements de mise à jour de session ACP émis pendant le tour
  -> réponse ACP renvoyée à l'IDE
```

### Invocation d'un outil

```
agent_loop                         (un appel d'outil décodé)
  -> tools/manager.py              (résolution par nom + filtres glob/regex)
  -> sous-classe de BaseTool.invoke()    (générateur asynchrone de ToolStreamEvent)
       -> pour MCP : tools/mcp/tools.py relaie vers un serveur MCP stdio ou HTTP
       -> pour les builtins : implémentation Python directe
  -> résultat agrégé + marqueur de troncature
  -> renvoi dans la liste de messages du LLM
```

## Décisions de conception

**Découpage pur / IO.** `core/` est pensé pour être importable depuis n'importe quel hôte (CLI, serveur ACP, futur SDK) sans tirer Textual ou la plomberie stdio. La boucle d'agent, le pipeline de middlewares, les backends LLM et le cadre d'outils y vivent. Les paquets CLI et ACP sont de fins adaptateurs qui câblent l'IO, les invites d'approbation et le rendu autour du même noyau.

**Backends LLM enfichables.** `core/llm/backend/factory.py` choisit entre `anthropic`, `mistral`, `vertex` et `generic` (compatible OpenAI, utilisé pour Albert). Chaque backend convertit le modèle canonique `LLMMessage` / `AvailableTool` au format de requête du fournisseur et reparse la réponse en streaming en `ChunkEvent` communs. Ajouter un fournisseur revient à implémenter un `APIAdapter`.

**Pipeline de middlewares.** Les préoccupations transverses (alerte de fenêtre de contexte, plafond de prix, limite de tours, auto-compaction, mode lecture seule pour le profil plan, rappel de focus todo) ne sont pas codées en dur dans la boucle ; ce sont des classes de middleware qui implémentent `before_turn()` et qui sont composées dans une liste. La boucle d'agent reste courte, et les profils d'agent peuvent activer ou désactiver les garde-fous indépendamment.

**Profils d'agent.** Un profil est un triplet (mode, ensemble de middlewares, outils autorisés) stocké en TOML. Les profils intégrés sont `default`, `plan` (lecture seule + plan d'abord), `accept-edits` (auto-approbation des éditions de fichiers) et `auto-approve`. Les profils utilisateur dans `~/.albert-code/agents/<nom>.toml` les surchargent ou les étendent. Le profil actif est sélectionnable via `--agent` ou `Shift+Tab` à l'exécution.

**Outils comme interface stable.** Les outils intégrés et les outils MCP partagent le même contrat `BaseTool`, qui produit des événements asynchrones en streaming. L'intégration MCP est un proxy : `core/tools/mcp/tools.py` instancie à la volée des sous-classes de `BaseTool` qui relaient les appels vers un serveur MCP stdio ou HTTP. Les compétences (outils Python personnalisés) se branchent de la même façon. La boucle d'agent n'a jamais besoin de savoir si un outil est intégré ou distant.

**Persistance des sessions.** Chaque tour interactif est ajouté à un journal JSONL dans `~/.albert-code/sessions/`. La reprise (`--continue` / `--resume`) rejoue le journal dans l'état de l'agent. Un module de migration gère les mises à jour de schéma quand le format sur disque évolue.

**Mode programmatique.** `-p` court-circuite entièrement la TUI, passe par `core/programmatic.py`, auto-approuve tous les outils et émet la réponse finale (ou le flux de messages) sur stdout. Combiné à `--max-turns`, `--max-price` et `--enabled-tools`, c'est la surface CI / scripting.

**Dossiers de confiance.** Avant que l'agent ne touche au système de fichiers, le répertoire courant doit figurer dans la liste de confiance. Lors du premier usage, `setup/trusted_folders/trust_folder_dialog.py` demande explicitement à l'utilisateur. La décision est persistée globalement.

**Notification de mise à jour.** La CLI consulte PyPI pour vérifier la disponibilité d'une nouvelle version au démarrage (avec un cache filesystem), affiche les notes de version issues de `whats_new.md` et propose une mise à jour en place. Le contrôle est implémenté en ports / adapters, ce qui permet de remplacer ou de mocker la passerelle (PyPI ou GitHub) et le backend de cache pendant les tests.

**Limitation de débit Albert et 429.** Le client implémente trois lignes de défense contre les `429 Too Many Requests` de l'API Albert. La première est `core/llm/throttling.py` : un singleton `Throttler` par fournisseur tient une fenêtre glissante de 60 s pour les requêtes et les tokens, met l'agent en attente quand la consommation projetée approche le seuil, et impose un débounce minimum `60 / rpm + 0,05 s` entre deux appels. Quand la table `DOCUMENTED_MODEL_LIMITS` connaît le modèle actif, le throttler utilise sa limite EXP propre plutôt que le maximum compte-tout-routeur (Albert n'expose pas le mapping modèle → routeur via `/v1/models`, et le maximum global remonte typiquement les 500 rpm du routeur d'embeddings). La deuxième ligne est la lecture du `Retry-After` (en-tête conforme RFC 7231 plus regex de secours sur les corps qui mentionnent `"N requests per minute"`) : un sleep adapté précède le retry suivant. La troisième ligne est l'`auto-fallback` : après deux 429 consécutifs sur un modèle, l'agent bascule sur `ModelConfig.fallback_model` pendant 60 s puis restaure le modèle initial.

**Distinction des 429 transitoires et terminaux.** Les 429 dont le corps contient le motif `per day` (quota journalier `rpd` ou `tpd` épuisé) sont reconnus comme terminaux par `is_terminal_rate_limit()` et déclenchent une `TerminalRateLimitError` qui contourne `async_retry`. Le quota ne se rétablira pas avant le reset de minuit UTC ; insister gaspille les retries restants et accélère la saturation du compte. Le même mécanisme est utilisé quand le seuil d'auto-fallback est atteint (`Throttler.is_fallback_trigger_reached`) : retenter le modèle primaire est inutile puisque le tour suivant utilisera de toute façon le modèle de secours.

**Avertissement de quota au démarrage.** À l'ouverture de la TUI, le worker `_check_quota_warning` combine deux signaux complémentaires. Le premier est persisté dans `~/.albert-code/throttle_state.json` (module `quota_state.py`) : chaque 429 daily-quota y inscrit le modèle, le motif et l'horodatage UTC, avec décrochage automatique au prochain reset de minuit. Le second est calculé en direct depuis `GET /v1/me/usage` : la somme des `prompt_tokens` du jour pour le modèle actif est comparée au `tpd` documenté, avec un seuil d'alerte à 80 % et un seuil critique à 95 %. La combinaison couvre le cas d'une saturation observée par albert-code lors d'une session précédente comme celui d'une saturation observée par un autre client API du même compte.

**TUI testée par snapshots.** `tests/snapshots/` utilise `pytest-textual-snapshot` pour capturer le rendu de la TUI au format SVG et l'asserter octet par octet contre la baseline versionnée. Les régressions visuelles sont détectées en CI ; les évolutions volontaires de l'interface régénèrent la baseline avec `pytest --snapshot-update`.

**Télémétrie opt-in.** `core/telemetry/send.py` n'émet d'événements que si la télémétrie est explicitement activée dans la configuration. Le comportement off par défaut est garanti dans `VibeConfig`.

## Frontières de sécurité

Le découpage `core/` / `cli/` / `acp/` sert trois objectifs de sécurité :

1. **Surface réseau auditable.** Tout le trafic HTTPS vers les fournisseurs de modèles est concentré dans `core/llm/backend/*`. Les outils web (`webfetch`, `websearch`) et les transports MCP HTTP sont les seuls autres points sortants, en plus de la notification de mise à jour (PyPI / GitHub) et du client de téléport (Vibe Nuage). Tout nouveau point de sortie est visible en revue de code.
2. **Médiation du système de fichiers.** Les outils qui modifient le système de fichiers (`Bash`, `Write`, `Edit`) exigent que le répertoire courant figure dans la liste des dossiers de confiance. En mode `plan`, le middleware lecture seule les bloque entièrement.
3. **Approbation systématique.** En mode interactif, les appels d'outils passent par la modale `approval_app.py` sauf si le profil d'agent (`accept-edits`, `auto-approve`) renonce à cette protection. L'utilisateur peut refuser un appel précis sans interrompre le tour.

Gestion des entrées et sorties :

- **Sortant :** le prompt système et l'historique de la conversation sont envoyés tels quels au fournisseur configuré ; il revient à l'utilisateur de retirer les secrets éventuels. Le flux de téléport chiffre les identifiants au repos via `core/auth/crypto.py`.
- **Entrant :** la sortie du modèle en streaming est rendue par `cli/textual_ui/ansi_markdown.py`, qui retire les séquences de contrôle avant affichage.

## Tests et CI

- `pytest --ignore tests/snapshots` exécute les suites unitaires et d'intégration (environ 1 400 tests) sous `pytest-xdist`.
- `pytest tests/snapshots` exécute la suite de snapshots Textual. En cas d'échec, un rapport de diff (`snapshot_report.html`) est téléversé en tant qu'artefact de CI.
- `pre-commit` enchaîne `pyright`, `ruff check --fix --unsafe-fixes`, `ruff format --check`, `typos` et `action-validator`.
- Le workflow GitHub Actions (`.github/workflows/ci.yml`) exécute les trois jobs en parallèle à chaque push sur `main` et à chaque PR.

## Configuration

`VibeConfig` (Pydantic settings) est la source unique de vérité. Elle est chargée depuis :

1. `~/.config/albert-code/config.toml` (XDG_CONFIG_HOME) - valeurs globales par défaut.
2. Le `.vibe.toml` le plus proche en remontant depuis le répertoire courant - surcharges propres au projet.
3. Les variables d'environnement (préfixe `ALBERT_CODE_`) - surcharges CI et ponctuelles.
4. `~/.albert-code/.env` - secrets (clés API).

`/config` (ou `/model`) ouvre l'éditeur intégré ; `/reload` recharge depuis le disque après une édition manuelle.
