# Albert Code sous Windows

> [!WARNING]
> **Sous Windows, Albert Code nécessite Windows Terminal pour afficher son interface.** L'invite de commande classique (`cmd.exe`) et la fenêtre PowerShell ouverte directement depuis le menu Démarrer ne savent pas afficher la TUI Textual ; l'application semble alors figée.

## Installation de Windows Terminal

Windows Terminal est l'application de terminal moderne de Microsoft, gratuite. Sur Windows 11, elle est installée par défaut. Sur Windows 10, l'installation manuelle est nécessaire :

1. Ouvrir le **Microsoft Store** depuis le menu Démarrer.
2. Rechercher **Windows Terminal**, ou ouvrir directement le lien https://aka.ms/terminal (qui redirige vers la page Store https://apps.microsoft.com/detail/9n0dx20hk701).
3. Cliquer sur **Obtenir** ou **Installer**. L'opération prend quelques secondes.

Pour les machines sans Microsoft Store, le `.msixbundle` de la dernière version est téléchargeable depuis la page des releases : https://github.com/microsoft/terminal/releases.

## Utilisation avec Albert Code

1. Ouvrir le menu Démarrer et taper **Terminal** (sous Windows, le programme est listé sous ce nom et non "Windows Terminal"). L'icône est noire et porte un chevron. Le lancer.
2. Par défaut, Windows Terminal ouvre un onglet **PowerShell** : ce comportement est normal et tout à fait approprié. PowerShell est un shell parfaitement compatible avec Albert Code. Windows Terminal n'est qu'un *conteneur de terminal* ; le shell qu'il héberge importe peu (PowerShell, cmd, WSL, etc. fonctionnent tous).
3. Se déplacer jusqu'au dossier d'Albert Code et lancer le `.bat` (le préfixe `.\` est requis sous PowerShell pour exécuter un script du dossier courant) :

   ```powershell
   cd C:\chemin\vers\albert-code
   .\albert-code.bat
   ```

Pour confirmer que la session s'exécute bien dans Windows Terminal, taper la commande suivante : `echo $env:WT_SESSION`. La variable doit afficher un identifiant. Si elle est vide, la session n'est pas dans Windows Terminal.

## Sans Windows Terminal

Le mode programmatique `albert-code.bat -p "votre prompt"` n'utilise pas la TUI et fonctionne dans n'importe quelle console (cmd.exe, PowerShell standard). Il convient aux usages scriptés mais ne fournit pas l'interface interactive.

## Menu d'installation

Lancer `.\albert-code.bat` sans argument affiche un menu interactif :

1. **Lancer Albert Code** : démarre l'application normalement.
2. **Installer la commande dans le PATH utilisateur** : ajoute le dossier d'Albert Code au `PATH` afin que `albert-code` soit disponible depuis n'importe quel répertoire (équivalent CLI : `albert-code.bat --install`).
3. **Désinstaller la commande du PATH utilisateur** : retire l'entrée du `PATH` (équivalent CLI : `albert-code.bat --uninstall`). Le dossier et l'application restent en place.
4. **Quitter** : ferme le menu sans rien lancer.

Avec des arguments (par exemple `albert-code.bat -p "..."` ou `albert-code.bat --version`), le menu est court-circuité et la commande s'exécute directement.

## Ajout au `PATH` utilisateur

Pour pouvoir taper `albert-code` depuis n'importe quel dossier, le lanceur Windows propose une sous-commande d'installation qui ajoute le dossier d'Albert Code au `PATH` utilisateur :

```powershell
.\albert-code.bat --install      # ajoute le dossier au PATH
.\albert-code.bat --uninstall    # retire le dossier du PATH
```

Ces sous-commandes font la même chose que les options 2 et 3 du menu interactif. Ouvrir une nouvelle fenêtre Windows Terminal après l'installation pour que la modification du `PATH` soit prise en compte.
