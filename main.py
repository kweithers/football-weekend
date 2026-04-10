import os
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    from pipeline import run_pipeline
    from display import print_rankings

    print("Fetching weekend fixtures and standings...")
    ranked = run_pipeline()
    print_rankings(ranked)


if __name__ == "__main__":
    main()
