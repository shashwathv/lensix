#!/usr/bin/env bash

# Stop on first error
set -e

echo "--- Installing Lensix Dependencies ---"

# --- Function to check if a command exists ---
command_exists() {
    command -v "$1" &> /dev/null
}

# --- System Dependency Check ---
echo "Checking for system dependencies..."
# We list the packages needed for Python, OCR, and various screenshot tools
REQUIRED_PKGS="python3 python3-pip tesseract-ocr scrot grim gnome-screenshot spectacle"
MISSING_PKGS=()

# Using dpkg-query is a reliable way to check for installed packages on Debian-based systems
for PKG in $REQUIRED_PKGS; do
    if ! dpkg-query -W -f='${Status}' "$PKG" 2>/dev/null | grep -q "ok installed"; then
        MISSING_PKGS+=("$PKG")
    fi
done

if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
    echo "Error: Missing system dependencies. Please install them first."
    echo "On Debian/Ubuntu, you can use the following command:"
    # The tr command replaces spaces with spaces, which cleans up any extra spacing
    echo "sudo apt update && sudo apt install $(echo ${MISSING_PKGS[@]} | tr ' ' ' ')"
    exit 1
fi

# --- Create Virtual Environment ---
echo "Creating a dedicated virtual environment..."
python3 -m venv .venv

# --- Python Dependency Installation (inside the venv) ---
echo "Installing Python dependencies into the virtual environment..."
./.venv/bin/pip install -r requirements.txt

# --- Playwright Browser Installation (using the venv's playwright) ---
echo "Installing Playwright browser binaries (this might take a moment)..."
./.venv/bin/playwright install

# --- Make Symlink for global command ---
echo "Creating the 'lensix' command in /usr/local/bin..."
INSTALL_DIR=$(pwd)
LAUNCHER_PATH="${INSTALL_DIR}/lensix"

if [ -L "/usr/local/bin/lensix" ]; then
    sudo rm "/usr/local/bin/lensix"
fi
sudo ln -sf "$LAUNCHER_PATH" /usr/local/bin/lensix

echo ""
echo "✅ Installation Complete!"
echo ""
echo "You can now run the program from anywhere by typing:"
echo "lensix"