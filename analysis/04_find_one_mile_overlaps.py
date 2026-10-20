"""Identify cross-party overlaps within one mile."""
import argparse
from competition_screen.preparation import one_mile_overlaps


def main():
    parser=argparse.ArgumentParser(description=__doc__)

    args=parser.parse_args()
    one_mile_overlaps()


if __name__=='__main__':
    main()
