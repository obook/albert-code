# Albert Code 🇫🇷

**Assistant IA de programmation en ligne de commande, propulsé par l'API Albert.**

> ⚠️ **Projet non officiel et expérimental.** Ce projet n'est affilié ni à la DINUM ni à Mistral AI. C'est un fork personnel de [Mistral Vibe](https://github.com/mistralai/mistral-vibe), adapté pour fonctionner avec l'[API Albert](https://albert.api.etalab.gouv.fr). Aucune garantie de stabilité ou de support.

## 1 -Obtenir ta clé API Albert

1. Aller sur https://albert.sites.beta.gouv.fr/access/ et remplir le formulaire
2. Recevoir son accès (délai de quelques heures, 24h max)
3. Se connecter au Playground : https://albert.playground.etalab.gouv.fr/
4. Créer une clé API et la copier (elle ressemble à `eyJhbGciOi...`)

> 💡 Support clé API → Salon Tchap **Albert API - Support & retours utilisateurs**

## 2 - Installation

```bash
uv tool install "albert-code @ git+https://github.com/simonaszilinskas/albert-code"
albert-code --api-key TA_CLE_API
```

## 3 -Utilisation

```bash
cd ton-projet/
albert-code
```

Tape `/help` pour voir les commandes disponibles.

## Licence

Basé sur [Mistral Vibe](https://github.com/mistralai/mistral-vibe) -Apache 2.0. Voir [LICENSE](LICENSE).
