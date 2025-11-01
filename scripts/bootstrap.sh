#!/usr/bin/env bash

# Stop on first error
set -e

# --- Configuration ---
GITHUB_REPO="shashwathv/lensix" 
INSTALL_DIR="$HOME/.local/share/lensix"

# --- Welcome Message ---
echo "=========================================="
echo "   Lensix Bootstrap Installer"
echo "=========================================="
echo ""
echo "Repository: https://github.com/$GITHUB_REPO"
echo "Installation directory: $INSTALL_DIR"
echo ""

# --- Dependency Check ---
echo "Checking prerequisites..."

if ! command -v git &> /dev/null; then
    echo "❌ Error: git is not installed."
    echo ""
    echo "Install git with:"
    echo "  Ubuntu/Debian: sudo apt install git"
    echo "  Fedora: sudo dnf install git"
    echo "  Arch: sudo pacman -S git"
    exit 1
fi
echo "   ✓ git found"

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed."
    echo ""
    echo "Install python3 with:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    echo "  Arch: sudo pacman -S python python-pip"
    exit 1
fi
echo "   ✓ python3 found"

# --- Clone or Update Repository ---
echo ""
if [ -d "$INSTALL_DIR" ]; then
    echo "Existing installation found at $INSTALL_DIR"
    read -p "Update existing installation? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    echo "Updating repository..."
    cd "$INSTALL_DIR"
    git fetch origin
    git reset --hard origin/main
    git pull origin main
    echo "   ✓ Repository updated"
else
    echo "Cloning repository..."
    git clone "https://github.com/$GITHUB_REPO.git" "$INSTALL_DIR"
    echo "   ✓ Repository cloned"
fi

# --- Run Main Installer ---
echo ""
echo "Running main installer..."
cd "$INSTALL_DIR"

if [ ! -f "scripts/install.sh" ]; then
    echo "❌ Error: install.sh not found in repository!"
    echo "The repository structure may be incorrect."
    exit 1
fi

chmod +x scripts/install.sh
./scripts/install.sh

# --- Success Message ---
echo ""
echo "=========================================="
echo "   Bootstrap Complete!"
echo "=========================================="
echo ""