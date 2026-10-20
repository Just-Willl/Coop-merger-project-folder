"""Validate reviewed routing; --refresh requests missing or changed polygons."""
import argparse
from competition_screen.preparation import drive_time_catchments


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true',help='Explicitly permit network collection')
    args=parser.parse_args()
    drive_time_catchments(refresh=args.refresh)


if __name__=='__main__':
    main()
