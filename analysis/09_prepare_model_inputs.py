"""Prepare observations, party-format proxies and catchments."""
import argparse
from competition_screen.preparation import prepare_model_inputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-mode',choices=['reviewed','fresh'],default='reviewed')
    args=parser.parse_args()
    prepare_model_inputs(source_mode=args.source_mode)


if __name__=='__main__':
    main()
