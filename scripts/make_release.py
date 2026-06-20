from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "v1.0.0"
PACKAGE_DIR = ROOT / "packages"
PACKAGE_PATH = PACKAGE_DIR / f"may-sheep-market-{VERSION}.zip"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "packages",
    "staticfiles",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".sqlite3"}
EXCLUDED_NAMES = {".env", "db.sqlite3"}


def should_include(path):
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def main():
    PACKAGE_DIR.mkdir(exist_ok=True)
    if PACKAGE_PATH.exists():
        PACKAGE_PATH.unlink()

    with zipfile.ZipFile(PACKAGE_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            if should_include(path):
                archive.write(path, path.relative_to(ROOT))

    print(f"Created {PACKAGE_PATH}")


if __name__ == "__main__":
    main()
