"""Check exact reference parity and export assets locally to streamlit_app."""
import argparse
from competition_screen.release import main as export_assets


def main():
    parser=argparse.ArgumentParser(description=__doc__)

    args=parser.parse_args()
    export_assets()


if __name__=='__main__':
    main()
