"""Inspect rival snapshots; --refresh resumes live OSM collection."""
import argparse
from competition_screen.preparation import collect_rival_stores


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true',help='Explicitly permit network collection')
    parser.add_argument('--geolytix-file')
    args=parser.parse_args()
    collect_rival_stores(refresh=args.refresh,geolytix_file=args.geolytix_file)


if __name__=='__main__':
    main()
