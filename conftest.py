"""Root conftest.py – adds project root to sys.path for test collection."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
