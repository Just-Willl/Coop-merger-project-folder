"""One path convention for every numbered analysis step, independent of cwd."""
from pathlib import Path

ANALYSIS_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ANALYSIS_ROOT.parent
DATA_DIRECTORY = REPOSITORY_ROOT / 'data'
INPUT_DIRECTORY = DATA_DIRECTORY / 'prepared'
INTERMEDIATE_DIRECTORY = DATA_DIRECTORY / 'intermediate'
OUTPUT_DIRECTORY = ANALYSIS_ROOT / 'outputs'
APP_DIRECTORY = REPOSITORY_ROOT / 'streamlit_app'
