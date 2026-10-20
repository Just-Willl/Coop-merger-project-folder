"""Render the explorer and reconcile rival totals to scores."""
import argparse
from competition_screen.map_renderer import render_map


def main():
    parser=argparse.ArgumentParser(description=__doc__)

    args=parser.parse_args()
    render_map()


if __name__=='__main__':
    main()
