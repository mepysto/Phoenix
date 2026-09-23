"""Write the API's OpenAPI document to a file (no running server needed).

Used to regenerate the web client's types so they always match this backend:
    cd apps/api && python -m scripts.export_openapi ../web/openapi.json
    cd apps/web && pnpm generate:types:local
"""

import json
import sys
from pathlib import Path

from src.main import app


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
