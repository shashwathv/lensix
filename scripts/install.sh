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
declare -A deps=(
    ["python3"]="python3"
    ["pip"]="python3-pip"
    ["tesseract"]="tesseract-ocr"
    ["scrot"]="scrot"
)
missing_deps=()

for cmd in "${!deps[@]}"; do
    if ! command_exists "$cmd"; then
        missing_deps+=("${deps[$cmd]}")
    fi
done

if [ ${#missing_deps[@]} -ne 0 ]; then
    echo "Error: Missing system dependencies. Please install them first."
    echo "On Debian/Ubuntu, you can use the following command:"
    echo "sudo apt update && sudo apt install ${missing_deps[*]}"
    exit 1
fi

# --- Python Dependency Installation ---
echo "Installing Python dependencies via pip..."
pip install -r requirements.txt

# --- Playwright Browser Installation ---
echo "Installing Playwright browser binaries (this might take a moment)..."
playwright install

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