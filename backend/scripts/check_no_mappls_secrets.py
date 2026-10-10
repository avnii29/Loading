#!/usr/bin/env python3
"""Fail if Mappls server credentials leak into tracked frontend files."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
FORBIDDEN = (
    "MAPPLS_CLIENT_SECRET",
    "MAPPLS_CLIENT_ID",
    "outpost.mappls.com/api/security/oauth/token",
)

SCAN_DIRS = [
    FRONTEND / "src",
    FRONTEND / "public",
    FRONTEND / "index.html",
]


def iter_files():
    for target in SCAN_DIRS:
        if target.is_file():
            yield target
        elif target.is_dir():
            for path in target.rglob("*"):
                if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".jsx", ".html", ".css", ".env", ".json"}:
                    yield path


def main() -> int:
    leaked = []
    for path in iter_files():
        if "node_modules" in path.parts or "dist" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in FORBIDDEN:
            if token in text:
                leaked.append(f"{path}: {token}")
    if leaked:
        print("Mappls server credentials must not appear in frontend files:")
        print("\n".join(leaked))
        return 1
    print("Secret exposure check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
