"""Launch uvicorn with correct sys.path for local development."""
import sys
import os

# Ensure both the project root (api/) and src/ (longevity/) are on the path
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")

for p in [project_root, src_path]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.chdir(project_root)

import uvicorn

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-reload", action="store_true")
    args, _ = parser.parse_known_args()

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=args.port,
        reload=not args.no_reload,
        reload_dirs=[project_root],
    )
