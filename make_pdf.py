"""
Convert clutch_hypothesis_research_report.md to PDF.
Uses: pandoc (md -> docx) + docx2pdf (docx -> pdf via Microsoft Word).
Requires: pandoc, Microsoft Word, docx2pdf (pip install docx2pdf)
"""

from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
MD = BASE / "outputs" / "clutch_hypothesis_research_report.md"
DOCX = BASE / "outputs" / "clutch_hypothesis_research_report.docx"
PDF = BASE / "outputs" / "clutch_hypothesis_research_report.pdf"

def find_pandoc():
    for p in ["pandoc", r"C:\Users\yuvi2\AppData\Local\Pandoc\pandoc.exe"]:
        r = subprocess.run([p, "--version"], capture_output=True, shell=True)
        if r.returncode == 0:
            return p
    return None


def main():
    if not MD.exists():
        print(f"Error: {MD} not found")
        return 1

    pandoc = find_pandoc()
    if not pandoc:
        print("Error: pandoc not found. Install from https://pandoc.org")
        return 1

    print("Step 1: Converting markdown to DOCX...")
    r = subprocess.run(
        [pandoc, str(MD), "-o", str(DOCX), "--resource-path=outputs"],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )
    if r.returncode != 0:
        print(f"Pandoc error: {r.stderr}")
        return 1

    print("Step 2: Converting DOCX to PDF (via Word)...")
    try:
        from docx2pdf import convert
        convert(str(DOCX), str(PDF))
    except ImportError:
        print("Install docx2pdf: pip install docx2pdf")
        print("(Requires Microsoft Word)")
        return 1

    print(f"Done. PDF saved to {PDF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
