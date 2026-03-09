"""
Convert clutch_analysis_substack.md to HTML for Substack paste.
Substack doesn't parse Markdown on paste—it treats it as plain text.
Pasting HTML preserves headings, bold, italic, and images.
"""

import markdown
from pathlib import Path

BASE = Path(__file__).resolve().parent
MD_FILE = BASE / "outputs" / "clutch_analysis_substack.md"
OUT_FILE = BASE / "outputs" / "clutch_analysis_substack.html"

def main():
    md_text = MD_FILE.read_text(encoding="utf-8")
    html = markdown.markdown(
        md_text,
        extensions=["extra", "nl2br"],
        extension_configs={"extra": {"enable_attributes": False}},
    )
    # Wrap in minimal structure for easy copy-paste of body
    full_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
{html}
</body>
</html>"""
    OUT_FILE.write_text(full_html, encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print("\nTo use on Substack (Substack does NOT parse Markdown paste):")
    print("1. Open clutch_analysis_substack.html in a BROWSER (Chrome, Edge)")
    print("   (Right-click file -> Open with -> your browser)")
    print("2. In the browser: Ctrl+A (select all), then Ctrl+C (copy)")
    print("3. In Substack: click in the post body, Ctrl+V (paste)")
    print("   The browser puts HTML in the clipboard, so Substack gets formatted content.")

if __name__ == "__main__":
    main()
