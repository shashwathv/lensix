#!/usr/bin/env bash

# Stop on first error
set -e

# --- Configuration ---
# IMPORTANT: CHANGE THIS TO YOUR GITHUB USERNAME AND REPOSITORY NAME
GITHUB_REPO="shashwathv/lensix" 
INSTALL_DIR="$HOME/.local/share/lensix"

# --- Welcome Message ---
echo "Bootstrapping Lensix installation..."
echo "Target repository: $GITHUB_REPO"
echo "Installation directory: $INSTALL_DIR"
echo ""

# --- Dependency Check ---
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed. Please install git and try again."
    exit 1
fi

# --- Clone or Update Repository ---
if [ -d "$INSTALL_DIR" ]; then
    echo "Existing installation found. Updating..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "https://github.com/$GITHUB_REPO.git" "$INSTALL_DIR"
fi

# --- Run Main Installer ---
echo "Running the main installer..."
cd "$INSTALL_DIR"
chmod +x scripts/install.sh
./scripts/install.sh

# --- Success Message ---
echo ""
echo "Bootstrap complete. Please follow any further instructions from the installer."