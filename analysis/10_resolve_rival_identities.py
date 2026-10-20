"""Resolve GEOLYTIX-primary entities and supplementary OSM observations."""
import argparse
from competition_screen.pipeline import run_entity_resolution


def main():
    parser=argparse.ArgumentParser(description=__doc__)

    args=parser.parse_args()
    run_entity_resolution()


if __name__=='__main__':
    main()
