# Commandes - Albert Code

Référence complète des commandes, options et raccourcis disponibles dans Albert Code.

## 1. Commandes système (binaires)

Albert Code expose deux exécutables installés via `pyproject.toml` :

### `albert-code` (CLI interactif et programmatique)

Point d'entrée : `albert_code/cli/entrypoint.py`.

| Option | Description |
|--------|-------------|
| `PROMPT` (positionnel) | Prompt initial pour démarrer la session interactive. |
| `-v`, `--version` | Affiche la version et quitte. |
| `-p`, `--prompt TEXTE` | Mode programmatique : envoie le prompt, auto-approuve tous les outils, écrit la réponse et quitte. |
| `--max-turns N` | Nombre maximum de tours assistant (mode `-p` uniquement). |
| `--max-price DOLLARS` | Coût maximum en dollars (mode `-p`). La session est interrompue si le coût dépasse cette limite. |
| `--enabled-tools OUTIL` | Active des outils précis. En mode `-p`, désactive tous les autres. Accepte des noms exacts, des motifs glob, ou des regex avec le préfixe `re:`. Peut être répété. |
| `--output {text,json,streaming}` | Format de sortie en mode `-p` : `text` (humain, par défaut), `json` (tous les messages à la fin), `streaming` (JSON ligne par ligne). |
| `--agent NOM` | Agent à utiliser : `default`, `plan`, `accept-edits`, `auto-approve`, ou un agent personnalisé depuis `~/.albert-code/agents/NOM.toml`. |
| `--setup` | Configure la clé API et quitte. |
| `--workdir RÉPERTOIRE` | Change le répertoire courant avant de démarrer. |
| `--api-key CLÉ` | Définit la clé API du provider actif et l'enregistre dans `~/.albert-code/.env`. |
| `-c`, `--continue` | Reprend la session sauvegardée la plus récente. |
| `--resume SESSION_ID` | Reprend une session spécifique par son ID (correspondance partielle acceptée). |
| `--install` | Installe le binaire `albert-code` dans le `PATH` utilisateur. |
| `--uninstall` | Désinstalle le binaire `albert-code`. |

### `albert-acp` (serveur Agent Client Protocol)

Point d'entrée : `albert_code/acp/entrypoint.py`. Utilisé par les intégrations IDE (Zed, etc.).

| Option | Description |
|--------|-------------|
| `-v`, `--version` | Affiche la version et quitte. |
| `--setup` | Configure la clé API et quitte. |

## 2. Commandes slash dans la TUI

Tapées dans le champ de saisie sous la forme `/<nom>`. Définies dans `albert_code/cli/commands.py`.

| Commande | Alias | Description |
|----------|-------|-------------|
| `/help` | - | Affiche le message d'aide. |
| `/config` | `/model` | Édite les paramètres de configuration. |
| `/reload` | - | Recharge la configuration depuis le disque. |
| `/clear` | - | Vide l'historique de la conversation. |
| `/log` | - | Affiche le chemin du fichier de log de l'interaction courante. |
| `/compact` | - | Compacte l'historique de la conversation par résumé. |
| `/exit` | - | Quitte l'application. |
| `/terminal-setup` | - | Configure `Shift+Enter` pour insérer un saut de ligne. |
| `/status` | - | Affiche les statistiques de l'agent. |
| `/limits` | `/quota` | Affiche les quotas Albert API (rpm, rpd, tpm, tpd) renvoyés par `/v1/me/info`, et le palier documenté EXP / PROD du modèle actif. |
| `/rpm` | - | Jauge en direct de la consommation RPM et TPM du modèle actif sur la fenêtre glissante de 60 s, avec barre de progression, débounce courant et éventuel `Retry-After` actif. |
| `/fallback` | - | Bascule l'auto-fallback en cas de 429 répétés. |
| `/teleport` | - | Téléporte la session vers Vibe Nuage. |
| `/proxy-setup` | - | Configure le proxy et le certificat SSL. |
| `/resume` | `/continue` | Parcourt et reprend une session passée. |

## 3. Raccourcis clavier (TUI)

### Application principale

Définis dans `albert_code/cli/textual_ui/app.py`.

| Touche | Action |
|--------|--------|
| `Ctrl+C` | Quitte (ou efface la saisie si du texte est présent). |
| `Ctrl+D` | Quitte (forcé). |
| `Ctrl+Z` | Suspend le processus. |
| `Échap` | Interrompt l'agent ou ferme les dialogues. |
| `Ctrl+O` | Bascule l'affichage de la sortie des outils. |
| `Ctrl+Y` | Copie la sélection dans le presse-papiers. |
| `Ctrl+Shift+C` | Copie la sélection dans le presse-papiers (alternative). |
| `Shift+Tab` | Cycle entre les modes (default, plan, accept-edits, auto-approve). |
| `Shift+Up` | Fait défiler le chat vers le haut. |
| `Shift+Down` | Fait défiler le chat vers le bas. |

### Champ de saisie

Définis dans `albert_code/cli/textual_ui/widgets/chat_input/text_area.py`.

| Touche | Action |
|--------|--------|
| `Entrée` | Envoie le message. |
| `Shift+Enter` | Insère un saut de ligne. |
| `Ctrl+J` | Insère un saut de ligne (alternative). |
| `Ctrl+G` | Édite la saisie dans un éditeur externe (`$EDITOR`). |

## 4. Préfixes spéciaux dans la saisie

| Préfixe | Effet |
|---------|-------|
| `!<commande>` | Exécute directement une commande shell. |
| `@chemin/fichier` | Auto-complétion de chemin (fichiers et dossiers du projet). |
| `/` (en début de saisie) | Déclenche l'auto-complétion des commandes slash. |

## 5. Modes d'agent

Sélectionnables via `--agent` ou `Shift+Tab` :

| Mode | Comportement |
|------|--------------|
| `default` | Demande l'approbation pour les outils sensibles. |
| `plan` | Lecture seule, propose un plan avant exécution. |
| `accept-edits` | Auto-approuve les éditions de fichiers, demande pour le reste. |
| `auto-approve` | Auto-approuve tous les outils (équivalent du mode `-p`). |
| `<custom>` | Profil personnalisé chargé depuis `~/.albert-code/agents/<nom>.toml`. |

## 6. Outils intégrés

Chaque outil peut être activé ou désactivé via la configuration ou `--enabled-tools`. Définis dans `albert_code/core/tools/builtins/` :

| Outil | Rôle |
|-------|------|
| `Bash` | Exécute des commandes shell avec capture de sortie et streaming. |
| `Read` | Lit le contenu d'un fichier. |
| `Write` | Écrit un fichier (création ou écrasement complet). |
| `Edit` | Remplace une portion exacte de texte dans un fichier. |
| `Grep` | Recherche par motif (ripgrep) dans le projet. |
| `Glob` | Liste les fichiers correspondant à un motif. |
| `WebFetch` | Récupère le contenu d'une URL. |
| `WebSearch` | Effectue une recherche web. |
| `AskUserQuestion` | Pose une question à l'utilisateur. |
| `Task` | Délègue à un sous-agent. |
| `Todo` | Gère une liste de tâches. |
| `MCP*` | Outils exposés par les serveurs MCP configurés. |
