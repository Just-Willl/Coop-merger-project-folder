"""Identify opposite-party stores inside five-minute catchments."""
import argparse
from competition_screen.preparation import drive_time_overlaps


def main():
    parser=argparse.ArgumentParser(description=__doc__)

    args=parser.parse_args()
    drive_time_overlaps()


if __name__=='__main__':
    main()
