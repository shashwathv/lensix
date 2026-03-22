#!/usr/bin/env python3
"""
KenXSearch — search.py
Thin entry point. All logic lives in src/.
"""

import sys
import os

# Force XWayland before Qt loads — must be set before any Qt imports
os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    main()