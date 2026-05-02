#!/bin/bash
#
# albert-code.sh - Lanceur principal (Linux / Mac).
#
# Ce script est le point d'entree pour lancer albert-code depuis
# le terminal en utilisant un venv Python local (sans uv).
# Il gere automatiquement l'environnement virtuel :
#   1. Au premier lancement : cree le venv et installe le projet.
#   2. Aux lancements suivants : active le venv existant.
#   3. Lance albert-code avec les arguments transmis.
#
# Usage :
#   ./albert-code.sh              -> lance albert-code dans le repertoire courant
#   ./albert-code.sh --help       -> affiche l'aide d'albert-code
#   ./albert-code.sh --install    -> installe le lien ~/.local/bin/albert-code
#                                    (commande disponible globalement, cwd preserve)
#   ./albert-code.sh --uninstall  -> retire le lien ~/.local/bin/albert-code
#
# Inspire de albert-cli/albert-cli.sh.
#
# Projet : albert-code
# Licence : Apache-2.0
#

set -euo pipefail

# Dossier du script. On resout les liens symboliques manuellement pour que
# `--install` (qui place un symlink dans ~/.local/bin/albert-code) ne fasse
# pas pointer SCRIPT_DIR vers ~/.local/bin. La boucle est portable BSD/Linux,
# contrairement a `readlink -f` qui n'existe pas sur macOS par defaut.
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    SOURCE_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    case "$SOURCE" in
        /*) ;;  # absolute already
        *) SOURCE="$SOURCE_DIR/$SOURCE" ;;
    esac
done
SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SYMLINK_PATH="$HOME/.local/bin/albert-code"

# ---- Sous-commandes d'installation / desinstallation du lien global ----
case "${1:-}" in
    --install)
        mkdir -p "$(dirname "$SYMLINK_PATH")"
        ln -sf "$SCRIPT_DIR/albert-code.sh" "$SYMLINK_PATH"
        echo "Lien cree : $SYMLINK_PATH -> $SCRIPT_DIR/albert-code.sh"
        case ":$PATH:" in
            *":$HOME/.local/bin:"*)
                echo "OK : ~/.local/bin est deja dans le PATH."
                ;;
            *)
                echo
                echo "Note : ~/.local/bin n'est pas dans ton PATH."
                echo "Ajoute la ligne suivante a ton ~/.bashrc ou ~/.zshrc :"
                echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
                echo "Puis ouvre un nouveau terminal."
                ;;
        esac
        echo
        echo "Tu peux maintenant lancer 'albert-code' depuis n'importe quel dossier."
        echo "Le repertoire courant est utilise comme dossier de travail."
        exit 0
        ;;
    --uninstall)
        if [ -L "$SYMLINK_PATH" ] || [ -e "$SYMLINK_PATH" ]; then
            rm -f "$SYMLINK_PATH"
            echo "Lien supprime : $SYMLINK_PATH"
        else
            echo "Aucun lien trouve a $SYMLINK_PATH (deja desinstalle)."
        fi
        exit 0
        ;;
esac

# Verifier que python3 est disponible
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Erreur : $PYTHON_BIN introuvable. Installe Python 3.12+ avant de continuer." >&2
    exit 1
fi

# Verifier la version de Python (>= 3.12)
PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
PYTHON_MAJOR="${PYTHON_VERSION%%.*}"
PYTHON_MINOR="${PYTHON_VERSION##*.}"
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 12 ]; }; then
    echo "Erreur : albert-code requiert Python 3.12 ou superieur (detecte : $PYTHON_VERSION)." >&2
    exit 1
fi

# Creer le venv s'il n'existe pas (premier lancement uniquement)
if [ ! -d "$VENV_DIR" ]; then
    echo "Creation de l'environnement virtuel ($VENV_DIR)..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Determiner s'il faut (re)installer le projet :
#   - entry point absent (premier lancement)
#   - pyproject.toml modifie depuis la derniere install (suivi via hash)
PYPROJECT="$SCRIPT_DIR/pyproject.toml"
INSTALL_MARKER="$VENV_DIR/.albert-code-install-hash"
NEEDS_INSTALL=0

if ! command -v albert-code >/dev/null 2>&1; then
    NEEDS_INSTALL=1
elif [ -f "$PYPROJECT" ]; then
    CURRENT_HASH="$(sha256sum "$PYPROJECT" | awk '{print $1}')"
    if [ ! -f "$INSTALL_MARKER" ] || [ "$(cat "$INSTALL_MARKER")" != "$CURRENT_HASH" ]; then
        NEEDS_INSTALL=1
    fi
fi

if [ "$NEEDS_INSTALL" -eq 1 ]; then
    echo "Installation des dependances et du projet (mode editable)..."
    pip install --upgrade --disable-pip-version-check pip >/dev/null
    pip install --disable-pip-version-check -e "$SCRIPT_DIR"
    if [ -f "$PYPROJECT" ]; then
        sha256sum "$PYPROJECT" | awk '{print $1}' > "$INSTALL_MARKER"
    fi
    echo "Lancement de albert-code, veuillez patienter..."
    echo
fi

# Lancer albert-code -- "$@" transmet tous les arguments passes au script
exec albert-code "$@"
