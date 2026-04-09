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
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[project_root],
    )
