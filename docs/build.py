"""Build the Assignment 2 submission from its only source, docs/assignment2_submission.md.

  .venv/bin/python docs/build.py

Writes (all generated; never edit them, edit the .md):
  docs/assignment2_submission.html   Markdown -> HTML with print CSS
  docs/assignment2_submission.pdf    headless Google Chrome
  docs/assignment2_submission.docx   Microsoft Word converts the HTML (keeps links and tables); without Word, macOS
                                     textutil is used and the .docx loses links and tables (a warning is printed)
  <tmp>/homestretch_preview/*.png    example.png (the <example> block) and appendix.png, for a visual check

Repo links in the .md are written as gh:<path> (a file) or ghtree:<path> (a folder) and are expanded here against
TAG, so the PDF keeps pointing at the submitted version while work continues on other branches.
Checks: the embedded prompts match prompts/*.md exactly, key strings survive in the PDF text, and every link
annotation in the PDF is listed (URLs are not fetched; they 404 until the repo is public and the tag is pushed).
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from pypdf import PdfReader

TAG = "a2-submission"
REPO = "https://github.com/anmolshetty02/homestretch"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
SRC = DOCS / "assignment2_submission.md"
OUT = DOCS / "assignment2_submission"
EMBEDDED = ["prompts/agent_v4.md", "prompts/extract_v2.md"]
MUST_SURVIVE = ['"tier_checked":true', "It may not be filled yet.", "found 3 things, most urgent first"]

CSS = """
@page { size: Letter; margin: 0.5in; }
body { font-family: -apple-system, Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.25; color: #111;
       max-width: 7.5in; margin: auto; }
h1 { font-size: 15pt; margin: 0 0 4px; }
h2 { font-size: 11.5pt; margin: 9px 0 3px; border-bottom: 1px solid #ccc; }
h2.appendix { page-break-before: always; }
p, li { margin: 3px 0; }
a { color: #0645ad; }
table { border-collapse: collapse; width: 100%; margin: 3px 0 6px; font-size: 9pt; }
th, td { border: 1px solid #bbb; padding: 2px 4px; vertical-align: top; text-align: left; }
th { background: #f0f0f0; }
pre { font-size: 7.6pt; line-height: 1.15; background: #f7f7f7; border: 1px solid #ddd; padding: 6px;
      white-space: pre-wrap; overflow-wrap: anywhere; }
pre .id { white-space: nowrap; }  /* keep flag-1, cab-2, med-2 whole across line breaks */
blockquote { margin: 3px 0 3px 10px; padding-left: 8px; border-left: 3px solid #ccc; color: #333; font-size: 9pt; }
code { font-size: 8.5pt; }
h2.appendix ~ pre { font-size: 7.4pt; line-height: 1.12; column-count: 2; column-gap: 14px; }  /* keep the appendix to one page */
h2.appendix ~ table { font-size: 8.5pt; }
h2.appendix ~ p { font-size: 9pt; }
"""


def expand_links(md):
    md = re.sub(r"\(gh:([^)\s]*)\)", lambda m: f"({REPO}/blob/{TAG}/{m.group(1)})", md)
    return re.sub(r"\(ghtree:([^)\s]*)\)", lambda m: f"({REPO}/tree/{TAG}/{m.group(1)})".replace("/)", ")"), md)


def keep_ids_whole(html):
    def fix(block):
        return re.sub(r"\b([a-z]+-\d+)\b", r'<span class="id">\1</span>', block.group(0))
    return re.sub(r"<pre>.*?</pre>", fix, html, flags=re.S)


def make_docx(html, docx):
    if Path("/Applications/Microsoft Word.app").exists():
        script = (f'tell application "Microsoft Word"\n open POSIX file "{html}"\n delay 2\n'
                  f' save as active document file name "{docx}" file format format document\n'
                  f' close active document saving no\nend tell')
        if subprocess.run(["osascript", "-e", script], capture_output=True).returncode == 0:
            return
    print("WARNING: Microsoft Word unavailable; .docx made with textutil has no links or tables")
    subprocess.run(["textutil", "-convert", "docx", str(html), "-output", str(docx)], check=True)


def main():
    md = SRC.read_text()
    for f in EMBEDDED:
        assert (ROOT / f).read_text().rstrip() in md, f"{f} in the .md does not match the file"
    html = markdown.markdown(expand_links(md), extensions=["tables", "fenced_code"])
    html = keep_ids_whole(html).replace("<h2>Appendix", '<h2 class="appendix">Appendix')
    page = f"<!doctype html><html><head><meta charset='utf-8'><title>HomeStretch Assignment 2</title><style>{CSS}</style></head><body>{html}</body></html>"
    OUT.with_suffix(".html").write_text(page)

    pdf = OUT.with_suffix(".pdf")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", OUT.with_suffix(".html").as_uri()], check=True, capture_output=True)
    make_docx(OUT.with_suffix(".html"), OUT.with_suffix(".docx"))

    reader = PdfReader(pdf)
    texts = [p.extract_text() or "" for p in reader.pages]
    flat = re.sub(r"\s+", "", "".join(texts))
    missing = [s for s in MUST_SURVIVE if re.sub(r"\s+", "", s) not in flat]
    urls = []
    for p in reader.pages:
        for a in p.get("/Annots") or []:
            uri = (a.get_object().get("/A") or {}).get("/URI")
            if uri:
                urls.append(str(uri))
    preview = Path(tempfile.gettempdir()) / "homestretch_preview"
    preview.mkdir(exist_ok=True)
    wanted = {"example": next(i for i, t in enumerate(texts, 1) if '"tier_checked":true' in re.sub(r"\s+", "", t)),
              "appendix": next(i for i, t in enumerate(texts, 1) if t.lstrip().startswith("Appendix"))}
    for name, i in wanted.items():
        subprocess.run(["pdftoppm", "-png", "-r", "80", "-f", str(i), "-l", str(i), "-singlefile", str(pdf), str(preview / name)], check=True)

    print(f"PDF: {len(reader.pages)} pages | link annotations (/URI): {len(urls)} | previews in {preview}: {wanted}")
    print("Strings intact in PDF text:", "all" if not missing else f"MISSING {missing}")
    for u in dict.fromkeys(urls):
        print("  ", u)
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
