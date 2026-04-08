"""CLI script to download NHANES data from CDC."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from longevity.data.nhanes.downloader import main

if __name__ == "__main__":
    main()
