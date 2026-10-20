"""Build both catchment methods for all cached candidates."""
import argparse
from competition_screen.preparation import build_analysis_areas


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-territory',action='store_true',help='Use updated candidate coverage for a refreshed study')
    args=parser.parse_args()
    build_analysis_areas(refresh_territory=args.refresh_territory)


if __name__=='__main__':
    main()
