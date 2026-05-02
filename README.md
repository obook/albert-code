# Albert Code 🇫🇷

<img src="media/20260502_195508.png" alt="Albert Code en cours d'utilisation dans le terminal" width="393" />

**Assistant IA de programmation en ligne de commande, propulsé par l'API Albert.**

> ⚠️ **Projet non officiel et expérimental.** Ce projet n'est affilié ni à la DINUM ni à Mistral AI. C'est un fork personnel de [Mistral Vibe](https://github.com/mistralai/mistral-vibe), adapté pour fonctionner avec l'[API Albert](https://albert.api.etalab.gouv.fr). Aucune garantie de stabilité ou de support.

## 1 -Obtenir ta clé API Albert

1. Aller sur https://albert.sites.beta.gouv.fr/access/ et remplir le formulaire
2. Recevoir son accès (délai de quelques heures, 24h max)
3. Se connecter au Playground : https://albert.playground.etalab.gouv.fr/
4. Créer une clé API et la copier (elle ressemble à `eyJhbGciOi...`)

> 💡 Support clé API → Salon Tchap **Albert API - Support & retours utilisateurs**

## 2 - Installation

Pré-requis : Python 3.12 ou supérieur.

```bash
git clone https://github.com/obook/albert-code.git
cd albert-code
./albert-code.sh
```

Le lanceur crée automatiquement un environnement virtuel Python (`.venv/`), installe les dépendances et démarre albert-code. Au premier lancement, albert-code te demandera ta clé API.

Sous Windows, utiliser `albert-code.bat` à la place de `albert-code.sh`.

## 3 - Utilisation

```bash
cd ton-projet/
/chemin/vers/albert-code/albert-code.sh
```

Tape `/help` pour voir toutes les commandes disponibles. Quelques commandes utiles spécifiques à Albert :

- `/limits` (alias `/quota`) : affiche les quotas par routeur (rpm, rpd, tpm, tpd) lus depuis `/v1/me/info`.
- `/fallback` : active ou désactive le basculement automatique de modèle après deux 429 consécutifs (par défaut actif, bascule de `albert-code` vers `albert-large` pendant 60 s).
- `/status` : statistiques de la session (étapes, tokens, coût).

## Remerciements

Ce fork s'inspire de [AlbertCode](https://github.com/XenocodeRCE/AlbertCode) de **Simon Roux** pour plusieurs idées clés autour de l'API Albert : auto-fallback de modèle sur 429 répétés, jauge RPM, mode plan-first avec checkpoints, snapshots Git automatiques avant édit. Les implémentations dans ce fork sont indépendantes mais doivent beaucoup à ses choix de design.

## Licence

Basé sur [Mistral Vibe](https://github.com/mistralai/mistral-vibe) -Apache 2.0. Voir [LICENSE](LICENSE).
