"""CLI script to train the biological age blood clock."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from longevity.models.bioage.trainer import main

if __name__ == "__main__":
    main()
