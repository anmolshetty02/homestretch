"""Build the Assignment 3 PDF from docs/rag-memory/draft.md, reusing the Assignment 2 styling in docs/build.py
(imported, not edited, so the A2 build is unchanged).

  .venv/bin/python docs/rag-memory/build_a3.py

Writes docs/rag-memory/draft.html and draft.pdf (generated; edit the .md), and page previews in <tmp>/homestretch_a3_preview.
"""
import importlib.util
import re
import subprocess
import tempfile
from pathlib import Path

import markdown
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("a2build", HERE.parent / "build.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

b.EYEBROW = "Building AI Applications · Assignment 3"
b.TAG = "main"  # links open the latest pushed version of each cited file
b.CSS = b.CSS.replace("Assignment 2", "Assignment 3")
b.CSS += (".refs { font-size: 7.4pt; line-height: 1.28; } h2.sec { margin-top: 10pt; }"
          "a { text-decoration: underline; text-decoration-color: var(--line); } table { break-inside: avoid; } .fig { margin: 4pt 0 8pt; break-inside: avoid; } .figcap { font-size: 7.6pt; color: var(--muted); margin-top: 2pt; }")
SRC, OUT = HERE / "draft.md", HERE / "draft"
MUST_SURVIVE = ["The class build uses synthetic data only", "[ref-3]"]


def references(h):
    """Each [n] line after the References heading becomes its own line (the A2 step expects a bold paragraph)."""
    m = re.search(r"(<h2>References</h2>\s*<p>)(.*?)(</p>)", h, re.S)
    refs = "".join(f'<div class="ref">{ln.strip()}</div>' for ln in m.group(2).split("\n") if ln.strip())
    return h[:m.start()] + f'<div class="refs"><div class="refs-title">References (all checked 2026-11-01)</div>{refs}</div>' + h[m.end():]


def main():
    plain = markdown.markdown(b.expand_links(SRC.read_text()), extensions=["tables"])
    styled = references(b.headings(b.title_block(plain)))
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>HomeStretch Assignment 3</title>"
            f"<style>{b.CSS}</style></head><body>{styled}</body></html>")
    OUT.with_suffix(".html").write_text(page)
    pdf = OUT.with_suffix(".pdf")
    subprocess.run([b.CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                    OUT.with_suffix(".html").as_uri()], check=True, capture_output=True)
    reader = PdfReader(pdf)
    flat = re.sub(r"\s+", "", "".join(p.extract_text() or "" for p in reader.pages))
    missing = [s for s in MUST_SURVIVE if re.sub(r"\s+", "", s) not in flat]
    preview = Path(tempfile.gettempdir()) / "homestretch_a3_preview"
    preview.mkdir(exist_ok=True)
    for old in preview.glob("page-*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", "80", str(pdf), str(preview / "page")], check=True)
    print(f"PDF: {len(reader.pages)} pages | previews: {preview} | strings intact: {missing or 'all'}")


if __name__ == "__main__":
    main()
