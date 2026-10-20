"""Standardise party fields and apply documented coordinate corrections."""
import argparse
from competition_screen.preparation import clean_party_stores


def main():
    parser=argparse.ArgumentParser(description=__doc__)

    args=parser.parse_args()
    clean_party_stores()


if __name__=='__main__':
    main()
