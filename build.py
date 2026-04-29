#!/usr/bin/env python3
"""
Script di build multipiattaforma per parser-bollette.
Produce i binari nella cartella dist/.

Uso:
    python3 build.py           # compila GUI + CLI
    python3 build.py --gui     # solo GUI
    python3 build.py --cli     # solo CLI
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"


def run(cmd: list[str]) -> None:
    print(f"\n>>> {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def check_pyinstaller() -> None:
    if shutil.which("pyinstaller") is None:
        print("PyInstaller non trovato. Installo...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build_gui() -> None:
    print("=== Build GUI (EstrattoreBollette) ===")
    run(["pyinstaller", "--clean", str(ROOT / "gui_bollette.spec")])
    if sys.platform == "darwin":
        print(f"App bundle: {DIST / 'EstrattoreBollette.app'}")
    else:
        print(f"Eseguibile: {DIST / 'EstrattoreBollette'}")


def build_cli() -> None:
    print("=== Build CLI (bollette-cli) ===")
    run(["pyinstaller", "--clean", str(ROOT / "bill_extractor.spec")])
    suffix = ".exe" if sys.platform == "win32" else ""
    print(f"Eseguibile: {DIST / f'bollette-cli{suffix}'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build parser-bollette con PyInstaller")
    parser.add_argument("--gui", action="store_true", help="Compila solo la GUI")
    parser.add_argument("--cli", action="store_true", help="Compila solo il CLI")
    args = parser.parse_args()

    check_pyinstaller()

    build_both = not args.gui and not args.cli
    if args.gui or build_both:
        build_gui()
    if args.cli or build_both:
        build_cli()

    print(f"\nBuild completato. Binari in: {DIST}")


if __name__ == "__main__":
    main()
