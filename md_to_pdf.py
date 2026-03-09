"""
Convert clutch_hypothesis_research_report.md to PDF.
Uses markdown -> HTML -> weasyprint (or fallback to fpdf2 for text-only).
"""

import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MD_PATH = BASE / "outputs" / "clutch_hypothesis_research_report.md"
PDF_PATH = BASE / "outputs" / "clutch_hypothesis_research_report.pdf"
CHARTS_DIR = BASE / "outputs" / "charts"


def try_weasyprint():
    """Try markdown + weasyprint for full HTML/PDF conversion."""
    try:
        import markdown
        from weasyprint import HTML, CSS
    except ImportError:
        return False

    with open(MD_PATH, encoding="utf-8") as f:
        md_text = f.read()

    # Fix image paths to be absolute for weasyprint
    def fix_img(m):
        src = m.group(1)
        if src.startswith("charts/"):
            abs_path = (BASE / "outputs" / src).resolve().as_uri()
            return f'![{m.group(2)}]({abs_path})'
        return m.group(0)

    md_text = re.sub(r'!\[([^\]]*)\]\((charts/[^)]+)\)', fix_img, md_text)

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc"],
        extension_configs={"toc": {"permalink": False}},
    )

    html_doc = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Georgia, serif; margin: 2cm; line-height: 1.5; }}
h1 {{ font-size: 22pt; margin-top: 0; }}
h2 {{ font-size: 16pt; margin-top: 1.5em; border-bottom: 1px solid #ccc; }}
h3 {{ font-size: 14pt; margin-top: 1em; }}
img {{ max-width: 100%; height: auto; }}
table {{ border-collapse: collapse; margin: 1em 0; }}
th, td {{ border: 1px solid #333; padding: 6px 10px; text-align: left; }}
th {{ background: #eee; }}
code {{ background: #f5f5f5; padding: 2px 4px; }}
pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""

    tmp_html = BASE / "outputs" / "_report_temp.html"
    tmp_html.write_text(html_doc, encoding="utf-8")

    html_for_pdf = HTML(string=html_doc, base_url=str(BASE / "outputs"))
    html_for_pdf.write_pdf(PDF_PATH)
    tmp_html.unlink(missing_ok=True)
    return True


def try_fpdf2():
    """Fallback: use fpdf2 for text-only PDF (no images)."""
    try:
        from fpdf import FPDF
    except ImportError:
        return False

    with open(MD_PATH, encoding="utf-8") as f:
        content = f.read()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    def safe_text(s, max_len=200):
        """Truncate/simplify text to avoid fpdf layout issues."""
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        s = re.sub(r"\*([^*]+)\*", r"\1", s)
        s = s.replace("—", "-").replace("–", "-")
        if len(s) > max_len:
            s = s[:max_len] + "..."
        return s

    lines = content.split("\n")
    for line in lines:
        if line.strip().startswith("![") and "](" in line:
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = safe_text(line.lstrip("#").strip(), 100)
            pdf.set_font("Helvetica", "B", size=min(14 - level, 12))
            pdf.multi_cell(0, 8, text)
            pdf.set_font("Helvetica", size=11)
            pdf.ln(2)
        elif line.strip().startswith("|") and "---" not in line:
            pdf.set_font("Helvetica", size=8)
            cells = [c.strip()[:25] for c in line.split("|")[1:-1]]
            pdf.multi_cell(0, 5, " | ".join(cells) if cells else "")
            pdf.set_font("Helvetica", size=11)
        elif line.strip() and not line.strip().startswith("$$"):
            clean = safe_text(line)
            if clean:
                pdf.multi_cell(0, 6, clean)
        else:
            pdf.ln(4)

    pdf.output(PDF_PATH)
    return True


def main():
    print("Converting markdown to PDF...")
    if try_weasyprint():
        print(f"Done. PDF saved to {PDF_PATH}")
        return 0
    print("Weasyprint not available. Trying fpdf2 (text only)...")
    if try_fpdf2():
        print(f"Done. PDF saved to {PDF_PATH} (text only, no images)")
        return 0
    print("ERROR: Install weasyprint for full PDF with images:")
    print("  pip install markdown weasyprint")
    print("Or install fpdf2 for text-only PDF:")
    print("  pip install fpdf2")
    return 1


if __name__ == "__main__":
    sys.exit(main())
