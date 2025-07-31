#!/usr/-bin/env python3

import subprocess
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

import cv2
import pytesseract
from PIL import Image
from playwright.sync_api import sync_playwright, TimeoutError


def preprocess_image(image_path):
    """Enhanced image processing for better OCR"""
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError("Could not read image file with OpenCV")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        denoised = cv2.medianBlur(gray, 3)

        thresh = cv2.adaptiveThreshold(denoised, 255,
                                     cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 11, 2)

        processed_path = Path("/tmp/processed_ocr.png")
        cv2.imwrite(str(processed_path), thresh)
        return processed_path

    except Exception as e:
        print(f"Image preprocessing failed, using original: {e}")
        return image_path


def is_valid_text(text):
    """Check if extracted text is meaningful"""
    if not text or len(text.strip()) < 3:
        return False
    return sum(c.isalnum() for c in text) >= 3


def capture_screenshot():
    """Capture screen region with error handling, preferring flameshot."""
    temp_file = Path("/tmp/screen_selection.png")
    tools = [
        ["flameshot", "gui", "-p", str(temp_file)],
        ["maim", "-s", str(temp_file)],
        ["scrot", "-s", "-q", "100", "-o", str(temp_file)] 
    ]

    for tool in tools:
        try:
            subprocess.run(tool, check=True,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
            if temp_file.exists() and temp_file.stat().st_size > 0:
                print(f"Screenshot captured with {tool[0]}.")
                return temp_file
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
            
    print("Error: No functional screenshot tool (flameshot, maim, scrot) found.")
    return None


def upload_to_google_lens(image_path):
    print("\nUploading to Google Lens...")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            file_input = page.locator('input[type="file"]')

            print("Uploading image and waiting for results...")
            with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
                file_input.set_input_files(str(image_path))

            print("\nUpload successful! The browser will stay open.")
            input("Press Enter in this terminal to close the browser and exit.")

        except TimeoutError:
            print("\n[ERROR] The automated upload timed out.")
            print("Please check your internet connection or try again.")
            input("Press Enter to exit.")
            
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred during the upload: {e}")
            input("Press Enter to exit.")


def main():
    print("Circle to Search - Select an area to analyze")
    image_path = capture_screenshot()
    if not image_path:
        print("Screenshot capture cancelled or failed.")
        return

    try:
        print("Processing image for text...")
        processed_path = preprocess_image(image_path)
        
        text = pytesseract.image_to_string(
            Image.open(processed_path),
            config='--oem 3 --psm 6'
        ).strip()

        if is_valid_text(text):
            print(f"\nFound text: {text}")
            url = f"https://www.google.com/search?q={quote_plus(text)}"
            webbrowser.open(url)
        else:
            print("\nNo readable text found - using Google Lens.")
            upload_to_google_lens(image_path)

    except Exception as e:
        print(f"\nAn unexpected processing error occurred: {e}")
        print("Defaulting to Google Lens upload.")
        upload_to_google_lens(image_path)


if __name__ == "__main__":
    main()
