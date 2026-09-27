"""Allow `python -m zelinqa_mcp` in addition to the `zelinqa-mcp` console script."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
