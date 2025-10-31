#!/usr/bin/env bash

# Stop on first error
set -e

echo "--- Installing Lensix Dependencies ---"

# --- Distro Detection & Package Definition ---
echo "Checking for system dependencies..."
PKG_MANAGER=""
INSTALL_CMD=""
declare -A PKGS

if command -v pacman &> /dev/null; then
    echo "Detected Arch-based Linux (using pacman)."
    PKG_MANAGER="pacman"
    # Note: On Arch, python-pip provides 'pip'. tesseract-data-eng provides English data.
    PKGS=(
        ["python"]="python-pip"
        ["tesseract"]="tesseract"
        ["eng.traineddata"]="tesseract-data-eng"
        ["scrot"]="scrot"
        ["grim"]="grim"
        ["gnome-screenshot"]="gnome-screenshot"
        ["spectacle"]="spectacle"
    )
    INSTALL_CMD="sudo pacman -Syu --noconfirm"
elif command -v apt &> /dev/null; then
    echo "Detected Debian-based Linux (using apt)."
    PKG_MANAGER="apt"
    PKGS=(
        ["python3"]="python3"
        ["pip"]="python3-pip"
        ["tesseract"]="tesseract-ocr"
        ["eng.traineddata"]="tesseract-ocr-eng"
        ["scrot"]="scrot"
        ["grim"]="grim"
        ["gnome-screenshot"]="gnome-screenshot"
        ["spectacle"]="spectacle"
    )
    INSTALL_CMD="sudo apt update && sudo apt install"
else
    echo "Error: Could not detect a supported package manager (apt or pacman)."
    exit 1
fi

# --- Dependency Check ---
MISSING_PKGS=()
for CMD_OR_FILE in "${!PKGS[@]}"; do
    PKG_NAME=${PKGS[$CMD_OR_FILE]}
    IS_INSTALLED=false
    if [[ "$PKG_MANAGER" == "pacman" ]]; then
        # For pacman, we just check if the package is installed
        if pacman -Q "$PKG_NAME" &> /dev/null; then
            IS_INSTALLED=true
        fi
    elif [[ "$PKG_MANAGER" == "apt" ]]; then
        if dpkg-query -W -f='${Status}' "$PKG_NAME" 2>/dev/null | grep -q "ok installed"; then
            IS_INSTALLED=true
        fi
    fi

    if ! $IS_INSTALLED; then
        MISSING_PKGS+=("$PKG_NAME")
    fi
done

if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
    echo "Error: Missing system dependencies. Please install them first."
    echo "You can use the following command:"
    echo "$INSTALL_CMD ${MISSING_PKGS[*]}"
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