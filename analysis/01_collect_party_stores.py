"""Read supplied party snapshots; --refresh explicitly downloads locator data."""
import argparse
from competition_screen.preparation import collect_party_stores


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true',help='Explicitly permit network collection')
    args=parser.parse_args()
    collect_party_stores(refresh=args.refresh)


if __name__=='__main__':
    main()
