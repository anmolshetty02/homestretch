"""Build the Assignment 4 document from docs/workflow/submission.md, reusing the A2 styling in docs/build.py and the
A3 references layout (both imported, not edited).

  .venv/bin/python docs/workflow/build_a4.py

Writes docs/workflow/submission.html and submission.pdf (generated; edit the .md) and page previews. Fails if the PDF
runs past MAX_PAGES or a key string is lost in rendering.
"""
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


b = load("a2build", DOCS / "build.py")
b.EYEBROW = "Building AI Applications · Assignment 4"
b.TAG = "main"
b.CSS = b.CSS.replace("Assignment 2", "Assignment 4")
b.CSS += (".refs { font-size: 7.4pt; line-height: 1.28; } h2.sec { margin-top: 10pt; }"
          "a { text-decoration: underline; text-decoration-color: var(--line); } table { break-inside: avoid; }"
          ".fig { margin: 4pt 0 8pt; break-inside: avoid; } .figcap { font-size: 7.6pt; color: var(--muted); margin-top: 2pt; }")
SRC, OUT = HERE / "submission.md", HERE / "submission"
MAX_PAGES = 3
MUST_SURVIVE = ["Call 911 now", "decided by data", "[ref-1]", "AI tools: Claude Code"]


def references(h):
    m = re.search(r"(<h2>References</h2>\s*<p>)(.*?)(</p>)", h, re.S)
    refs = "".join(f'<div class="ref">{ln.strip()}</div>' for ln in m.group(2).split("\n") if ln.strip())
    return h[:m.start()] + f'<div class="refs"><div class="refs-title">References (all checked 2026-11-14)</div>{refs}</div>' + h[m.end():]


def main():
    plain = markdown.markdown(b.expand_links(SRC.read_text()), extensions=["tables"])
    styled = references(b.headings(b.title_block(plain)))
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>HomeStretch Assignment 4</title>"
            f"<style>{b.CSS}</style></head><body>{styled}</body></html>")
    OUT.with_suffix(".html").write_text(page)
    pdf = OUT.with_suffix(".pdf")
    subprocess.run([b.CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                    OUT.with_suffix(".html").as_uri()], check=True, capture_output=True)
    reader = PdfReader(pdf)
    flat = re.sub(r"\s+", "", "".join(p.extract_text() or "" for p in reader.pages))
    missing = [s for s in MUST_SURVIVE if re.sub(r"\s+", "", s) not in flat]
    preview = Path(tempfile.gettempdir()) / "homestretch_a4_preview"
    preview.mkdir(exist_ok=True)
    for old in preview.glob("page-*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", "80", str(pdf), str(preview / "page")], check=True)
    print(f"PDF: {len(reader.pages)} pages (max {MAX_PAGES}) | previews: {preview} | strings intact: {missing or 'all'}")
    if len(reader.pages) > MAX_PAGES or missing:
        sys.exit("FAILED: over the page limit or text lost; fix submission.md before submitting")


if __name__ == "__main__":
    main()
