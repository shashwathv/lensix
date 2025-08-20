#!/usr/bin/env python3

# ==============================================================================
#  Circle to Search for Linux (v4.4) - True Circle Capture
# ==============================================================================
#
# FIX:
#   - Now captures exactly the drawn shape, not just the bounding rectangle
#   - Applies mask to exclude content outside the drawn area
#   - Provides true "Circle to Search" experience
#
# ==============================================================================

import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from shutil import which
from urllib.parse import quote_plus

import cv2
import mss
import numpy as np
import pyperclip
import pytesseract
from PIL import Image, ImageDraw
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygon, QPixmap, QImage
from PyQt6.QtWidgets import QApplication, QMainWindow
from playwright.sync_api import sync_playwright, TimeoutError

# --- Configuration ---
USE_FREEFORM_SELECTION = True
WAYLAND = os.getenv('XDG_SESSION_TYPE', '').lower() == 'wayland'
DESKTOP = os.getenv('XDG_CURRENT_DESKTOP', '').lower()
TEMP_DIR = Path("/tmp")
SCREENSHOT_PATH = TEMP_DIR / "circle_to_search_capture.png"


# --- Core Capture Logic ---
class Overlay(QMainWindow):
    def __init__(self, is_wayland, desktop_env, sct_instance=None):
        super().__init__()
        self.is_wayland = is_wayland
        self.desktop_env = desktop_env
        self.sct = sct_instance
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.path = QPolygon()
        self.is_drawing = False
        self.start_point = None

    def paintEvent(self, event):
        if not self.is_drawing: 
            return
            
        painter = QPainter(self)
        pen = QPen(QColor(135, 206, 250, 200), 4, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        
        # Draw the path
        if self.path.count() > 1:
            painter.drawPolyline(self.path)
            
        # Draw a circle if we have a start point and current position
        if self.start_point and self.path.count() > 0:
            current_pos = self.path.point(self.path.count() - 1)
            radius = int(((current_pos.x() - self.start_point.x())**2 + 
                         (current_pos.y() - self.start_point.y())**2)**0.5)
            painter.drawEllipse(self.start_point, radius, radius)

    def mousePressEvent(self, event):
        self.is_drawing = True
        self.start_point = event.pos()
        self.path.append(event.pos())

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.path.append(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        self.is_drawing = False
        self.hide()
        
        if self.path.count() < 2:
            QApplication.quit()
            return
            
        # Get the bounding rectangle of the drawn path
        rect = self.path.boundingRect()
        
        try:
            if self.is_wayland:
                # First capture the full screen area
                fullscreen_temp_path = TEMP_DIR / "fullscreen_temp.png"
                if self.capture_wayland_fullscreen(fullscreen_temp_path):
                    # Then crop and mask the captured area
                    self.crop_and_mask_screenshot(fullscreen_temp_path, rect)
                    fullscreen_temp_path.unlink(missing_ok=True)
            else:
                # Capture the rectangular area
                sct_img = self.sct.grab(rect.topLeft().x(), rect.topLeft().y(), 
                                       rect.width(), rect.height())
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(SCREENSHOT_PATH))
                
                # Apply mask to the captured area
                self.apply_mask_to_screenshot(rect)
                
        except Exception as e:
            print(f"An unexpected error occurred during capture: {e}", file=sys.stderr)
        finally:
            QApplication.quit()
            
    def capture_wayland_fullscreen(self, output_path):
        """Capture full screen on Wayland"""
        methods = [
            self.capture_with_slurp_grim_fullscreen,
            self.capture_with_gnome_screenshot_fullscreen,
            self.capture_with_spectacle_fullscreen
        ]
        
        for method in methods:
            try:
                if method(output_path):
                    return True
            except Exception:
                continue
                
        return False
        
    def capture_with_slurp_grim_fullscreen(self, output_path):
        """Use grim for fullscreen capture"""
        if not which("grim"):
            return False
            
        try:
            subprocess.run(["grim", str(output_path)], 
                          check=True, capture_output=True, timeout=10)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False

    def capture_with_gnome_screenshot_fullscreen(self, output_path):
        """Use GNOME screenshot tool for fullscreen"""
        if not which("gnome-screenshot"):
            return False
            
        try:
            subprocess.run([
                "gnome-screenshot", "-f", str(output_path)
            ], check=True, capture_output=True, timeout=10)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False

    def capture_with_spectacle_fullscreen(self, output_path):
        """Use KDE Spectacle for fullscreen capture"""
        if not which("spectacle"):
            return False
            
        try:
            subprocess.run([
                "spectacle", "-b", "-f", "-o", str(output_path)
            ], check=True, capture_output=True, timeout=10)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False
            
    def crop_and_mask_screenshot(self, fullscreen_path, rect):
        """Crop and apply mask to the screenshot"""
        # Open the full screenshot
        with Image.open(fullscreen_path) as img:
            # Crop to the bounding rectangle
            cropped_img = img.crop((rect.left(), rect.top(), rect.right(), rect.bottom()))
            
            # Create a mask for the drawn shape
            mask = Image.new('L', cropped_img.size, 0)
            draw = ImageDraw.Draw(mask)
            
            # Convert QPolygon points to relative coordinates within the crop
            points = []
            for i in range(self.path.count()):
                point = self.path.point(i)
                points.append((point.x() - rect.left(), point.y() - rect.top()))
            
            # Draw the polygon on the mask
            if len(points) > 2:
                draw.polygon(points, fill=255)
            else:
                # Fallback to ellipse if not enough points for polygon
                center_x = rect.width() / 2
                center_y = rect.height() / 2
                radius = min(rect.width(), rect.height()) / 2
                draw.ellipse((center_x - radius, center_y - radius, 
                             center_x + radius, center_y + radius), fill=255)
            
            # Apply the mask
            result = Image.new('RGBA', cropped_img.size, (0, 0, 0, 0))
            result.paste(cropped_img, (0, 0), mask)
            result.save(SCREENSHOT_PATH, "PNG")
            
    def apply_mask_to_screenshot(self, rect):
        """Apply mask to the already captured rectangular screenshot"""
        # Open the captured screenshot
        with Image.open(SCREENSHOT_PATH) as img:
            # Create a mask for the drawn shape
            mask = Image.new('L', img.size, 0)
            draw = ImageDraw.Draw(mask)
            
            # Convert QPolygon points to relative coordinates within the crop
            points = []
            for i in range(self.path.count()):
                point = self.path.point(i)
                points.append((point.x() - rect.left(), point.y() - rect.top()))
            
            # Draw the polygon on the mask
            if len(points) > 2:
                draw.polygon(points, fill=255)
            else:
                # Fallback to ellipse if not enough points for polygon
                center_x = img.width / 2
                center_y = img.height / 2
                radius = min(img.width, img.height) / 2
                draw.ellipse((center_x - radius, center_y - radius, 
                             center_x + radius, center_y + radius), fill=255)
            
            # Apply the mask
            result = Image.new('RGBA', img.size, (0, 0, 0, 0))
            result.paste(img, (0, 0), mask)
            result.save(SCREENSHOT_PATH, "PNG")

def capture_freeform_screenshot():
    print("Please draw a circle or shape around the area to capture...")
    print("If a permission dialog appears, please grant screen capture access.")
    
    if SCREENSHOT_PATH.exists(): 
        SCREENSHOT_PATH.unlink()
        
    app = QApplication.instance() or QApplication(sys.argv)
    sct_instance = mss.mss() if not WAYLAND else None
    
    # Check for Wayland dependencies
    if WAYLAND:
        wayland_tools = ["grim", "gnome-screenshot", "spectacle"]
        available_tools = [tool for tool in wayland_tools if which(tool)]
        
        if not available_tools:
            print("ERROR: No supported screenshot tools found for Wayland.")
            print("Please install one of: grim, gnome-screenshot, or spectacle")
            return None
            
        print(f"Available screenshot tools: {', '.join(available_tools)}")
    
    overlay = Overlay(is_wayland=WAYLAND, desktop_env=DESKTOP, sct_instance=sct_instance)
    overlay.show()
    app.exec()
    
    if sct_instance: 
        sct_instance.close()
        
    if SCREENSHOT_PATH.exists() and SCREENSHOT_PATH.stat().st_size > 0:
        print("Screenshot captured.")
        return SCREENSHOT_PATH
        
    return None

# --- Helper Functions ---
def capture_screenshot_fallback():
    print("Fallback capture mode not fully implemented. Please use freeform selection.", file=sys.stderr)
    return None

def preprocess_image_for_ocr(image_path):
    try:
        img = cv2.imread(str(image_path))
        if img is None: raise ValueError("Could not read image")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_inv = cv2.bitwise_not(gray)
        processed_path = TEMP_DIR / "processed_ocr.png"
        processed_inv_path = TEMP_DIR / "processed_ocr_inv.png"
        cv2.imwrite(str(processed_path), gray)
        cv2.imwrite(str(processed_inv_path), gray_inv)
        return processed_path, processed_inv_path
    except Exception as e:
        print(f"Image preprocessing failed: {e}", file=sys.stderr)
        return image_path, None

def extract_text_with_confidence_multi(image_paths):
    custom_config = r'--oem 3 --psm 6'
    all_text, all_confs = [], []
    for path in filter(None, image_paths):
        data = pytesseract.image_to_data(Image.open(path), config=custom_config, output_type=pytesseract.Output.DICT)
        for i, word in enumerate(data['text']):
            if word.strip() and int(data['conf'][i]) > -1:
                conf = int(data['conf'][i])
                if conf > 50:
                    all_text.append(word)
                    all_confs.append(conf)
    if not all_text: return "", 0
    return " ".join(all_text).strip(), sum(all_confs) / len(all_confs)

def is_valid_text(text):
    if not text: return False
    cleaned = ' '.join(text.strip().split())
    return len(cleaned) >= 3 and sum(c.isalnum() for c in cleaned) >= 3

def upload_to_google_lens(image_path):
    print("\nUploading to Google Lens...")
    with sync_playwright() as p:
        browser = None
        try:
            launch_args = ['--start-maximized']
            if WAYLAND: launch_args.extend(['--enable-features=WaylandWindowDecorations', '--ozone-platform=wayland'])
            browser = p.chromium.launch(headless=False, args=launch_args)
            context = browser.new_context(no_viewport=True)
            page = context.new_page()
            page.goto("https://lens.google.com/upload", wait_until="domcontentloaded")
            file_input = page.locator('input[type="file"]')
            file_input.wait_for(state="attached", timeout=15000)
            with page.expect_navigation(wait_until="networkidle", timeout=60000):
                file_input.set_input_files(str(image_path))
            print("\n✅ Upload successful! The browser will stay open.")
            input("Press Enter in this terminal to close the browser and exit.")
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred during upload: {e}", file=sys.stderr)
            input("Press Enter to exit.")
        finally:
            if browser: browser.close()

# --- Main Application Logic ---
def main():
    # Check for required dependencies
    if not which("tesseract"):
        print("ERROR: 'tesseract' is required for OCR", file=sys.stderr)
        print("Install it with: sudo apt install tesseract-ocr", file=sys.stderr)
        return
        
    image_path = capture_freeform_screenshot() if USE_FREEFORM_SELECTION else capture_screenshot_fallback()
    if not image_path:
        print("Screenshot capture cancelled or failed. Exiting.")
        return
        
    try:
        processed_path, processed_inv_path = preprocess_image_for_ocr(image_path)
        text, avg_conf = extract_text_with_confidence_multi([processed_path, processed_inv_path])
        if text and avg_conf >= 55 and is_valid_text(text):
            print("\n--- Text Recognized ---")
            print(f'"{text}" (Confidence: {avg_conf:.2f}%)')
            print("-----------------------")
            prompt = "\nChoose an action:\n [1] Search with Google\n [2] Copy to Clipboard\n [3] Translate (to English)\n\nEnter your choice (Default is 1): "
            choice = input(prompt).strip()
            if choice == '2':
                pyperclip.copy(text)
                print("✅ Text copied to clipboard!")
            elif choice == '3':
                print("Opening Google Translate...")
                translate_url = f"https://translate.google.com/?sl=auto&tl=en&text={quote_plus(text)}"
                webbrowser.open(translate_url)
            else:
                print("Searching on Google...")
                search_url = f"https://www.google.com/search?q={quote_plus(text)}"
                webbrowser.open(search_url)
            sys.exit(0)
        else:
            print("\n❌ No high-confidence text found. Uploading image to Google Lens.")
            upload_to_google_lens(image_path)
    except Exception as e:
        print(f"\n[ERROR] An unexpected processing error occurred: {e}", file=sys.stderr)
        print("Defaulting to Google Lens upload.")
        upload_to_google_lens(image_path)

if __name__ == "__main__":
    main()