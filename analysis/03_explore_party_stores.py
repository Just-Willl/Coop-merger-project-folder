"""Summarise the party estate and write a static plot."""
import argparse
from competition_screen.preparation import explore_party_stores


def main():
    parser=argparse.ArgumentParser(description=__doc__)

    args=parser.parse_args()
    explore_party_stores()


if __name__=='__main__':
    main()
