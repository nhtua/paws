
import sys
import os

# Add the project root directory to sys.path to allow imports from 'paws'
# This mimics setting PYTHONPATH=. when running from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
