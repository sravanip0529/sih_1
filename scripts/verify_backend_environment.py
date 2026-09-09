import importlib
import platform
import sys


MODULES = (
    "fastapi",
    "rasterio",
    "geopandas",
    "psycopg",
    "qdrant_client",
    "pystac_client",
    "numpy",
    "pandas",
    "shapely",
    "pyproj",
)


def main() -> int:
    print(f"Python: {platform.python_version()} ({sys.executable})")
    failures = 0
    for module_name in MODULES:
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "available")
            print(f"[ok] {module_name}: {version}")
        except Exception as error:
            failures += 1
            print(f"[error] {module_name}: {error}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())