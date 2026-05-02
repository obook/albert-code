# Fiche de sécurité - Albert Code

**Date de mise à jour :** 2026-05-02
**Référentiel :** ANSSI-PA-102 (Sécurité de l'IA générative, 29/04/2024), ANSSI-PA-073 (Développement sécurisé, 24/03/2022), OWASP Top 10

## Surface d'attaque

### Permissions et capacités du processus

Albert Code est un agent local qui s'exécute avec les droits de l'utilisateur. Les capacités sensibles sont gardées par un système d'approbation explicite et par un registre de dossiers de confiance.

| Capacité | Justification | Garde |
|----------|---------------|-------|
| Lecture du système de fichiers | Outils `Read`, `Grep`, `Glob` pour explorer le projet | Limitée au dossier courant marqué comme « de confiance » |
| Écriture sur le système de fichiers | Outils `Write`, `Edit` pour appliquer les modifications | Approbation utilisateur (sauf mode `accept-edits` ou `auto-approve`) |
| Exécution de commandes shell | Outil `Bash` (build, tests, git, ...) | Approbation utilisateur, désactivable par profil d'agent |
| Accès réseau sortant | Provider LLM, MCP HTTP, WebFetch / WebSearch, mise à jour PyPI / GitHub, télémétrie opt-in, Vibe Nuage (téléport) | Surface concentrée dans `core/llm/backend/`, `core/tools/builtins/web*.py`, `core/tools/mcp/`, `cli/update_notifier/`, `core/teleport/`, `core/telemetry/` |
| Lancement de sous-processus | Serveurs MCP stdio, éditeur externe (`$EDITOR`), `git`, `ripgrep` | Liste blanche dans la configuration |

### Réseau

- **Provider LLM** : un seul endpoint actif à la fois (Albert API par défaut, Anthropic / Mistral / Vertex / OpenAI-compatible en option). HTTPS imposé.
- **En-têtes** : `Authorization: Bearer <clé>`, `Content-Type: application/json`, `Accept: application/json` ou `text/event-stream` pour le streaming.
- **MCP** : transports stdio (sous-processus local) ou HTTP. Les serveurs MCP sont déclarés explicitement dans la configuration utilisateur ; aucun n'est activé par défaut.
- **Mise à jour** : un GET HTTPS vers PyPI (ou GitHub Releases) au démarrage, avec cache filesystem et schéma d'URL validé avant ouverture de tout lien.
- **Télémétrie** : désactivée par défaut. Quand activée explicitement par l'utilisateur, envoie des événements anonymes vers un endpoint configurable.
- **Vibe Nuage (téléport)** : appel uniquement déclenché par la commande `/teleport`, après authentification GitHub explicite.

### Stockage local

| Donnée | Emplacement | Protection |
|--------|-------------|-----------|
| Clé API du provider | `~/.albert-code/.env` | Permissions fichier utilisateur (`0600` recommandé) |
| Configuration | `~/.config/albert-code/config.toml` (XDG) | Permissions fichier utilisateur |
| Configuration projet | `.vibe.toml` à la racine du projet | Versionnable, ne doit pas contenir de secret |
| Historique de session | `~/.albert-code/sessions/*.jsonl` | Permissions fichier utilisateur |
| Historique de saisie | `~/.albert-code/history` | Permissions fichier utilisateur |
| Logs ACP | `~/.albert-code/logs/acp/messages.jsonl` (rotation 1 Mo, 3 fichiers) | Permissions fichier utilisateur |
| Dossiers de confiance | `~/.config/albert-code/trusted_folders.toml` | Permissions fichier utilisateur |
| Identifiants chiffrés (téléport) | `core/auth/crypto.py` | Chiffrement symétrique avant écriture sur disque |

Aucune donnée n'est synchronisée vers un service tiers. La sortie réseau est strictement limitée aux endpoints listés ci-dessus.

## Modèle de menaces

| Menace | Mesure |
|--------|--------|
| Injection de commande via la sortie du modèle | Toute exécution shell passe par l'outil `Bash`, qui propose la commande à l'utilisateur dans une boîte d'approbation avant exécution (sauf profils auto-approve explicitement choisis). |
| Modification de fichiers hors du projet | Les outils d'écriture (`Write`, `Edit`) refusent d'écrire en dehors du dossier marqué comme « de confiance ». Le premier accès à un dossier déclenche un dialogue de confirmation explicite (`setup/trusted_folders/trust_folder_dialog.py`). |
| Lecture de fichiers sensibles (`.env`, clés SSH, ...) | L'agent peut lire ces fichiers s'il en reçoit l'instruction. La sécurité repose sur le périmètre du dossier de confiance et sur la responsabilité de l'utilisateur. Le système prompt rappelle au modèle d'éviter ces fichiers. |
| Prompt injection depuis le contenu d'un fichier ou d'une page web | Le contenu retourné par `Read`, `WebFetch`, `WebSearch` est cadré comme « tool result » dans la conversation et n'est jamais traité comme une instruction utilisateur. Les approbations restent côté utilisateur. |
| Fuite de secrets via la conversation | Aucun filtrage automatique de secrets dans les messages envoyés au provider. La responsabilité de la sanitisation revient à l'utilisateur. La clé API n'apparaît jamais dans la conversation, uniquement en en-tête HTTP. |
| Interception réseau (MITM) | HTTPS imposé pour tous les endpoints. Clé API transmise via en-tête `Authorization` (jamais dans l'URL). |
| Serveur MCP malveillant | Les serveurs MCP sont déclarés explicitement par l'utilisateur. Aucun MCP n'est lancé sans configuration explicite. Les capacités d'un serveur MCP sont celles d'un sous-processus utilisateur. |
| Abus de l'API (rate limiting) | Détection du code HTTP 429, backoff adaptatif (`core/llm/throttling.py`), affichage du délai à l'utilisateur, fallback automatique optionnel (`/fallback`). |
| Coût incontrôlé en mode programmatique | Garde-fou `--max-price` (interruption si coût cumulé dépassé) et `--max-turns`. Le middleware `PriceLimitMiddleware` applique la limite à chaque tour. |
| Dépassement de la fenêtre de contexte | Middleware `ContextWarningMiddleware` (alerte) et `AutoCompactMiddleware` (compaction automatique de l'historique). |
| Téléchargement d'une mise à jour compromise | Mise à jour via PyPI (canal officiel pip), schéma d'URL validé. Pas de téléchargement de binaire arbitraire. |

## Profils d'agent et garde-fous

Les profils d'agent règlent le compromis entre autonomie et contrôle :

| Profil | Approbation outils | Tour limit | Lecture seule |
|--------|--------------------|------------|---------------|
| `default` | Oui (sauf outils non sensibles) | Non | Non |
| `plan` | Oui | Oui | Oui (middleware `ReadOnlyAgentMiddleware`) |
| `accept-edits` | Auto pour `Write` / `Edit`, oui pour `Bash` | Non | Non |
| `auto-approve` | Auto pour tous les outils | Non | Non |
| Profil personnalisé | Configurable (`~/.albert-code/agents/<nom>.toml`) | Configurable | Configurable |

Le mode `auto-approve` est le mode par défaut en exécution programmatique (`-p`). Il est conseillé de le combiner avec `--max-turns`, `--max-price` et `--enabled-tools` pour borner l'autonomie.

## Pratiques de développement

- **Typage statique** : `pyright` strict en pré-commit ; toute régression de typage bloque le merge.
- **Lint et format** : `ruff check --fix --unsafe-fixes` et `ruff format --check` en pré-commit.
- **Validation des fichiers de workflow** : `action-validator` sur les workflows GitHub Actions.
- **Tests** : ~1400 tests pytest (unitaires, intégration, e2e) et 56 tests de snapshot Textual exécutés en CI sur chaque push et chaque PR.
- **Pas de dépendance non auditée** : toutes les dépendances sont déclarées dans `pyproject.toml` avec contraintes de version. Les composants sensibles (cryptographie, HTTPS) reposent sur des bibliothèques maintenues (`cryptography`, `httpx`).
- **Frontière des couches** : `core/` n'importe ni `textual` ni `acp`, ce qui isole la logique métier des adapters d'interface et facilite l'audit.

## Conformité RGPD

- Aucun appel réseau en dehors des endpoints configurés par l'utilisateur.
- La télémétrie est **désactivée par défaut** ; elle ne s'active que sur opt-in explicite.
- Les sessions enregistrées sur disque restent locales ; aucun envoi automatique vers un service tiers.
- Les clés API sont stockées localement dans `~/.albert-code/.env` ou via le keyring système (`keyring`), jamais transmises à un endpoint autre que le provider LLM choisi.
- L'utilisateur peut effacer toutes les données locales en supprimant `~/.albert-code/` et `~/.config/albert-code/`.

## Signalement d'une vulnérabilité

Pour signaler une vulnérabilité de sécurité, ouvrir un ticket privé sur le dépôt GitHub du projet ou contacter directement le mainteneur. Ne pas divulguer publiquement la vulnérabilité avant la mise à disposition d'un correctif.
