#!/usr/bin/env python3
"""
Download ollama binaries for distribution

This script downloads the appropriate ollama binary for the current platform
and places it in services/ollama/
"""

import os
import platform
import sys
import urllib.request
from pathlib import Path

# Ollama download URLs (official releases)
OLLAMA_URLS = {
    "Windows": "https://github.com/ollama/ollama/releases/download/v0.5.4/ollama-windows-amd64.zip",
    "Linux": "https://github.com/ollama/ollama/releases/download/v0.5.4/ollama-linux-amd64",
    "Darwin": "https://github.com/ollama/ollama/releases/download/v0.5.4/ollama-darwin",
}


def download_file(url: str, dest: Path):
    """Download a file with progress"""
    print(f"Downloading from {url}...")

    def reporthook(blocknum, blocksize, totalsize):
        readsofar = blocknum * blocksize
        if totalsize > 0:
            percent = readsofar * 100 / totalsize
            s = f"\r{percent:5.1f}% {readsofar:,} / {totalsize:,}"
            sys.stderr.write(s)
            if readsofar >= totalsize:
                sys.stderr.write("\n")
        else:
            sys.stderr.write(f"\rRead {readsofar:,}\n")

    urllib.request.urlretrieve(url, dest, reporthook)
    print(f"Downloaded to {dest}")


def main():
    # Get current platform
    system = platform.system()
    if system not in OLLAMA_URLS:
        print(f"Error: Unsupported platform: {system}")
        sys.exit(1)

    # Create destination directory
    base_dir = Path(__file__).parent.parent
    ollama_dir = base_dir / "services" / "ollama"
    ollama_dir.mkdir(parents=True, exist_ok=True)

    # Determine filename
    if system == "Windows":
        filename = "ollama.exe"
    else:
        filename = "ollama"

    dest_path = ollama_dir / filename

    # Check if already exists
    if dest_path.exists():
        response = input(f"Ollama already exists at {dest_path}. Overwrite? (y/n): ")
        if response.lower() != "y":
            print("Skipping download.")
            return

    # Download
    url = OLLAMA_URLS[system]

    if system == "Windows":
        # Windows version is a zip file
        import zipfile
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "ollama.zip"
            download_file(url, zip_path)

            print("Extracting...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(ollama_dir)

            print(f"Extracted to {ollama_dir}")
    else:
        # Linux/Mac are single binaries
        download_file(url, dest_path)

        # Make executable
        os.chmod(dest_path, 0o755)
        print(f"Made executable: {dest_path}")

    print("\n✓ Ollama binary downloaded successfully!")
    print(f"  Location: {dest_path}")
    print(f"  Size: {dest_path.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
