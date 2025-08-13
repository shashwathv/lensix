import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from shutil import which
from urllib.parse import quote_plus

import cv2
import numpy as np
import pytesseract
from PIL import Image
from playwright.sync_api import sync_playwright, TimeoutError

# --- Configuration ---
WAYLAND = os.getenv('XDG_SESSION_TYPE', '').lower() == 'wayland'
DESKTOP = os.getenv('XDG_CURRENT_DESKTOP', '').lower()
TEMP_DIR = Path("/tmp")
SCREENSHOT_PATH = TEMP_DIR / "circle_to_search_capture.png"

# --- Core Functions ---

def check_dependencies():
    """Checks for required tools based on the environment."""
    print("Checking dependencies...")
    has_deps = True
    if WAYLAND:
        if 'gnome' in DESKTOP and not which('gnome-screenshot'):
            print("[ERROR] On GNOME, 'gnome-screenshot' is required.", file=sys.stderr)
            has_deps = False
        elif 'kde' in DESKTOP and not which('spectacle'):
            print("[ERROR] On KDE Plasma, 'spectacle' is required.", file=sys.stderr)
            has_deps = False
        elif not all(which(cmd) for cmd in ["grim", "slurp"]):
            print("[INFO] For wlroots desktops (Sway/Hyprland), 'grim' and 'slurp' are needed.", file=sys.stderr)
            # This is not a fatal error if on GNOME/KDE
    
    if not which("tesseract"):
        print("\n[ERROR] 'tesseract' command is not installed.", file=sys.stderr)
        has_deps = False

    if not has_deps:
        sys.exit(1)
    print("✅ All dependencies found.")


def capture_screenshot():
    """
    FIX: Now detects the desktop environment and uses the best tool.
    This is the main fix for the 'zwlr_layer_shell_v1' error.
    """
    print("Please select a region of your screen...")
    if SCREENSHOT_PATH.exists():
        SCREENSHOT_PATH.unlink()

    command = []
    if WAYLAND:
        if 'gnome' in DESKTOP:
            # Use GNOME's native screenshot tool
            command = ["gnome-screenshot", "-a", "-f", str(SCREENSHOT_PATH)]
        elif 'kde' in DESKTOP:
            # Use KDE's native screenshot tool, Spectacle
            command = ["spectacle", "-b", "-n", "-r", "-o", str(SCREENSHOT_PATH)]
        else:
            # Fallback for wlroots (Sway, Hyprland, etc.)
            try:
                geometry = subprocess.check_output("slurp", text=True).strip()
                if not geometry: return None
                command = ["grim", "-g", geometry, str(SCREENSHOT_PATH)]
            except (subprocess.CalledProcessError, FileNotFoundError):
                 print("[ERROR] slurp/grim failed. Is this a GNOME/KDE session without the right env vars set?", file=sys.stderr)
                 return None
    else: # X11
        command = ["flameshot", "gui", "-p", str(SCREENSHOT_PATH)]

    try:
        # A return code of 1 from spectacle/gnome-screenshot can mean user cancellation
        proc = subprocess.run(command, check=True, capture_output=True)
        if proc.returncode == 0 and SCREENSHOT_PATH.exists() and SCREENSHOT_PATH.stat().st_size > 0:
            print(f"Screenshot captured with '{command[0]}'.")
            return SCREENSHOT_PATH
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # Handle user cancellation gracefully (e.g., pressing Esc)
        if "No such file" not in str(e) and "exit status 1" not in str(e):
             print(f"[ERROR] Screenshot command failed: {e}", file=sys.stderr)
        return None
    
    # Check if the file was created (some tools exit 0 on cancel but create no file)
    if SCREENSHOT_PATH.exists() and SCREENSHOT_PATH.stat().st_size > 0:
        print(f"Screenshot captured with '{command[0]}'.")
        return SCREENSHOT_PATH
    
    return None


def preprocess_image_for_ocr(image_path):
    """Adaptive preprocessing for OCR on mixed-background screenshots."""
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError("Could not read image")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Keep two versions: normal and inverted
        gray_inv = cv2.bitwise_not(gray)

        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        enhanced_inv = clahe.apply(gray_inv)

        # Slight sharpening to keep edges crisp
        kernel_sharp = np.array([[0, -1, 0],
                                 [-1, 5, -1],
                                 [0, -1, 0]])
        sharp = cv2.filter2D(enhanced, -1, kernel_sharp)
        sharp_inv = cv2.filter2D(enhanced_inv, -1, kernel_sharp)

        # Save both processed versions
        processed_path = TEMP_DIR / "processed_ocr.png"
        processed_inv_path = TEMP_DIR / "processed_ocr_inv.png"
        cv2.imwrite(str(processed_path), sharp)
        cv2.imwrite(str(processed_inv_path), sharp_inv)

        return processed_path, processed_inv_path
    except Exception as e:
        print(f"Image preprocessing failed: {e}", file=sys.stderr)
        return image_path, None


def extract_text_with_confidence_multi(image_paths):
    """Run OCR on multiple versions of the image and merge results."""
    custom_config = r'--oem 3 --psm 6'
    all_text = []
    all_confs = []

    for path in filter(None, image_paths):
        data = pytesseract.image_to_data(
            Image.open(path),
            config=custom_config,
            output_type=pytesseract.Output.DICT
        )
        for i, word in enumerate(data['text']):
            if word.strip():
                conf = int(data['conf'][i])
                if conf > 55 or (conf > 40 and len(word) > 3):
                    all_text.append(word)
                    all_confs.append(conf)

    if not all_text:
        return "", 0

    avg_conf = sum(all_confs) / len(all_confs)
    return " ".join(all_text).strip(), avg_conf



def upload_to_google_lens(image_path):
    """Improved Google Lens upload using Playwright with better element selection."""
    print("\nUploading to Google Lens...")
    with sync_playwright() as p:
        browser = None
        try:
            launch_args = ['--start-maximized']
            if WAYLAND:
                launch_args.extend(['--enable-features=WaylandWindowDecorations', '--ozone-platform=wayland'])
            
            browser = p.chromium.launch(headless=False, args=launch_args)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                no_viewport=True,
                # Accept all permissions that might block file upload
                permissions=['clipboard-read', 'clipboard-write']
            )
            page = context.new_page()
            
            # Navigate to Google Lens
            page.goto("https://lens.google.com/upload", wait_until="networkidle")
            
            # Wait for and handle the file input
            try:
                # Try to find the file input with multiple selectors
                file_input = page.locator('input[type="file"]')
                file_input.wait_for(state="attached", timeout=10000)
                
                # Upload the file
                with page.expect_response(lambda response: "https://lens.google.com/v3/upload" in response.url, timeout=30000):
                    file_input.set_input_files(str(image_path))
                
                # Wait for results to load
                page.wait_for_selector('div[aria-label="Visual matches"]', timeout=60000)
                print("\n✅ Upload successful! The browser will stay open.")
                
            except TimeoutError:
                # Fallback method - try clicking the upload button if direct input fails
                try:
                    upload_button = page.locator('button:has-text("Upload an image")')
                    if upload_button.count() > 0:
                        upload_button.click()
                        # Wait for the file dialog to appear (may not work in headful mode)
                        file_input = page.locator('input[type="file"]')
                        file_input.wait_for(state="attached", timeout=5000)
                        file_input.set_input_files(str(image_path))
                        page.wait_for_selector('div[aria-label="Visual matches"]', timeout=60000)
                        print("\n✅ Upload successful (fallback method)! The browser will stay open.")
                    else:
                        raise
                except Exception as fallback_error:
                    print(f"\n[ERROR] Could not upload image automatically: {fallback_error}", file=sys.stderr)
                    print("Please upload the image manually in the browser window.")
            
            input("Press Enter in this terminal to close the browser and exit.")

        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred during upload: {e}", file=sys.stderr)
            input("Press Enter to exit.")
        finally:
            if browser: browser.close()


def is_valid_text(text):
    """Improved text validation with better filtering."""
    if not text:
        return False
    
    cleaned = ' '.join(text.strip().split())  # Normalize whitespace
    alnum_count = sum(c.isalnum() for c in cleaned)
    word_count = len(cleaned.split())
    
    return (len(cleaned) >= 3 and 
            alnum_count >= 3 and 
            word_count >= 1 and
            not cleaned.isnumeric() and  # Exclude pure numbers
            not all(len(word) == 1 for word in cleaned.split()))  # Exclude single-letter "words"


def main():
    """Main execution flow."""
    check_dependencies()
    image_path = capture_screenshot()
    if not image_path:
        print("Screenshot capture cancelled or failed. Exiting.")
        return

    try:
        print("Processing image for text...")
        processed_path = preprocess_image_for_ocr(image_path)
        
        # Extract text with confidence filtering
        text, avg_conf = extract_text_with_confidence_multi(processed_path)
        
        # Show results for user clarity
        print("\n--- OCR RESULTS ---")
        if text:
            print(f"Extracted Text: \"{text}\"")
            print(f"Average Confidence: {avg_conf:.2f}%")
        else:
            print("No high-confidence text found.")
        print("-------------------\n")
        
        if text and avg_conf >= 60 and is_valid_text(text):
            print(f'\n✅ Using text for search: "{text}"')
            search_url = f"https://www.google.com/search?q={quote_plus(text)}"
            webbrowser.open(search_url)
        else:
            print("\n❌ No valid text found. Uploading image to Google Lens.")
            upload_to_google_lens(image_path)

    except Exception as e:
        print(f"\n[ERROR] An unexpected processing error occurred: {e}", file=sys.stderr)
        print("Defaulting to Google Lens upload.")
        upload_to_google_lens(image_path)
if __name__ == "__main__":
    main()