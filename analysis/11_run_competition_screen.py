"""Score the current model, then join CMA benchmark outcomes."""
import argparse
from competition_screen.pipeline import run_analysis


def main():
    parser=argparse.ArgumentParser(description=__doc__)

    args=parser.parse_args()
    run_analysis()


if __name__=='__main__':
    main()
