"""Build the Assignment 2 submission from its only source, docs/assignment2_submission.md.

  .venv/bin/python docs/build.py

Writes (all generated; never edit them, edit the .md):
  docs/assignment2_submission.html   styled HTML (print layout), the input for the PDF
  docs/assignment2_submission.pdf    headless Google Chrome
  docs/assignment2_submission.docx   made by Microsoft Word from a plain version of the same HTML (same words and links,
                                     simple tables) so it stays easy to edit; without Word, macOS textutil is used and
                                     the .docx loses links and tables (a warning is printed)
  <tmp>/homestretch_preview/page-N.png   every page, for a visual check

Styling is applied here, after Markdown -> HTML, by small steps that key off headings, tables, and paragraph openings.
None of them change the words of the .md; they only add wrappers, classes, and a few labels (eyebrow, KPI tiles,
code captions, "HomeStretch" reply labels, page footer).

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

EYEBROW = "Building AI Applications · Assignment 2"
FOOTER = "HomeStretch · Assignment 2 · Group 5"
KPIS = [
    ("91/91", "planted discrepancies caught across 33 cabinets"),
    ("98%", "held-out pass on 20 Synthea patients we never tuned on (49/50)"),
    ("393/401", "problems caught in the messy-data stress test"),
    ("$2.43", "per 1,000 sessions, with a 724-word prompt"),
]
CAPTIONS = {  # first line of the code block -> (caption, file it comes from)
    "<role>\nYou are HomeStretch": ("Prompt B · cabinet diff and chat (final, v4)", "prompts/agent_v4.md"),
    "<role>\nYou read OCR text": ("Prompt A · label reading (final, v2)", "prompts/extract_v2.md"),
}
ID = r"(?:cab|flag|med|stopped|contact|warn|tier|avoid|missed|appt|weigh)-\d+"
PHONE = r"\d{3}-\d{3}-\d{4}"

CSS = """
:root { --teal:#0F5257; --teal2:#1B7A80; --teal-bg:#EDF6F5; --line:#CFE3E1; --ink:#1E2B2F; --muted:#5C6C71;
        --amber:#C9821E; --amber-bg:#FFF6E6; --gray-bg:#F2F4F5; --code-bg:#F6F8F8; --gap:7pt; }
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; box-sizing: border-box; }
@page { size: Letter; margin: 0.6in 0.7in 0.65in 0.7in;
  @bottom-left { content: "FOOTER"; font: 7pt "Avenir Next", "Helvetica Neue", sans-serif; color: #5C6C71; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 7pt "Avenir Next", "Helvetica Neue", sans-serif; color: #5C6C71; } }
body { font: 9.3pt/1.42 Palatino, Georgia, serif; color: var(--ink); margin: 0; }
h1, h2, th, .eyebrow, .kpi, .panel-title, .pill, .cap, .card-title, .who, .refs-title { font-family: "Avenir Next", "Helvetica Neue", sans-serif; }
p, li { margin: 0 0 calc(var(--gap) * 0.55); }
ul { margin: 0 0 var(--gap); padding-left: 16pt; }
a { color: var(--teal2); text-decoration: none; }
code { font: 8pt Menlo, monospace; color: var(--teal); }
.nw { white-space: nowrap; }

/* title block */
.title { margin-bottom: calc(var(--gap) * 1.2); }
.eyebrow { font-size: 7.4pt; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--teal2); }
h1 { font-size: 19.5pt; font-weight: 700; line-height: 1.2; color: #0B3B3F; margin: 3pt 0 6pt; }
.bar { width: 56pt; height: 3pt; border-radius: 2pt; background: linear-gradient(90deg, var(--teal), var(--teal2)); margin-bottom: 6pt; }
.meta { color: var(--muted); font-size: 8.8pt; }
.repo { font-size: 8.8pt; }

/* section headings */
h2.sec { display: flex; align-items: center; gap: 7pt; font-size: 12pt; font-weight: 700; color: #0B3B3F;
         border-bottom: 1px solid var(--line); padding-bottom: 3pt; margin: calc(var(--gap) * 2) 0 var(--gap); break-after: avoid; }
h2.sec .num { flex: none; width: 17pt; height: 17pt; border-radius: 4pt; background: var(--teal); color: #fff;
              font-size: 9pt; display: inline-flex; align-items: center; justify-content: center; }
h2.appendix { break-before: page; }

/* KPI tiles and results panel */
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 7pt; margin: var(--gap) 0; break-inside: avoid; }
.kpi { background: var(--teal-bg); border-radius: 7pt; padding: 7pt 8pt; }
.kpi .n { font-size: 16pt; font-weight: 700; color: var(--teal); line-height: 1.1; }
.kpi .l { font-size: 7.6pt; color: var(--muted); line-height: 1.3; margin-top: 2pt; }
.panel { background: var(--teal-bg); border-radius: 8pt; padding: 7pt 10pt 5pt; margin: var(--gap) 0; break-inside: avoid; }
.panel-title { font-size: 8.6pt; font-weight: 700; color: var(--teal); margin-bottom: 3pt; }
.panel-title code { font-size: 7.8pt; }
.panel table { border: none; border-radius: 0; margin: 0; background: transparent; }
.panel td { background: transparent !important; border-top: 1px solid var(--line); }
.panel tr:first-child td { border-top: none; }

/* tables */
table { width: 100%; border-collapse: separate; border-spacing: 0; border: 1px solid var(--line); border-radius: 6pt;
        overflow: hidden; font-size: 8.3pt; line-height: 1.35; margin: calc(var(--gap) * 0.6) 0 var(--gap); }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { background: var(--teal); color: #fff; font-size: 7.6pt; font-weight: 600; text-align: left; padding: 4pt 5pt; }
td { padding: 3.5pt 5pt; border-top: 1px solid var(--line); vertical-align: top; }
tbody tr:nth-child(even) td { background: #F6FAF9; }
tr.hl td { background: var(--teal-bg) !important; }
table.boldfirst td:first-child { font-weight: 700; }
td code { font-size: 7.4pt; }
.pill { display: inline-block; font-size: 7.4pt; font-weight: 600; padding: 0.5pt 6pt; border-radius: 8pt;
        border: 1px solid var(--teal2); color: var(--teal); background: #fff; }
.pill.solid { background: var(--teal); border-color: var(--teal); color: #fff; }
.pill.gray { background: #E3E7E9; border-color: #C9D0D3; color: var(--muted); }

/* code blocks */
pre { background: var(--code-bg); border-left: 3px solid var(--teal); border-radius: 0 6pt 6pt 0;
      font: 6.95pt/1.36 Menlo, monospace; color: var(--ink); white-space: pre-wrap; overflow-wrap: anywhere;
      padding: 0 9pt 7pt 9pt; margin: var(--gap) 0; orphans: 10; widows: 3; }
pre code { font: inherit; color: inherit; }
pre .cap { display: flex; justify-content: space-between; gap: 10pt; background: var(--teal); color: #fff;
           font-size: 7.4pt; font-weight: 600; white-space: normal; margin: 0 -9pt 6pt -9pt; padding: 3pt 9pt;
           border-radius: 0 6pt 0 0; }
pre .cap a { color: #fff; font-weight: 500; text-decoration: underline; }
pre .tag { color: var(--teal); font-weight: 700; }
pre.two-col { column-count: 2; column-gap: 14pt; font-size: 6.6pt; }
pre.two-col .cap { column-span: all; }
pre.newpage { break-before: page; }

/* example cards */
.card { border: 1px solid var(--line); border-radius: 8pt; padding: 7pt 10pt 4pt; margin: var(--gap) 0; break-inside: avoid; }
.card-title { font-size: 9pt; font-weight: 700; color: #0B3B3F; }
.card .quote { font-style: italic; }
.reply { background: var(--teal-bg); border-left: 3px solid var(--teal2); border-radius: 0 6pt 6pt 0; padding: 4pt 9pt 5pt; margin: 5pt 0 6pt; }
.reply .who { font-size: 6.3pt; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--teal2); margin-bottom: 1pt; }
.reply p { white-space: pre-line; margin: 0; }
.idp { font: 6.7pt Menlo, monospace; background: #fff; border: 1px solid var(--line); border-radius: 3pt;
       padding: 0 2pt; white-space: nowrap; color: var(--teal); }

/* callouts */
.callout { padding: 5pt 9pt; border-radius: 0 6pt 6pt 0; margin: calc(var(--gap) * 0.8) 0; break-inside: avoid; }
.callout.amber { background: var(--amber-bg); border-left: 3px solid var(--amber); }
.callout.gray { background: var(--gray-bg); border-left: 3px solid #AEB8BC; }
.callout.teal { background: var(--teal-bg); border-left: 3px solid var(--teal); }
.card .callout { margin: 4pt 0 5pt; }
b.amb { color: #8A5510; }

/* references */
.refs { font-size: 8.2pt; line-height: 1.35; margin: var(--gap) 0; }
.refs-title { font-weight: 700; color: #0B3B3F; margin-bottom: 2pt; }
.ref { padding-left: 1.7em; text-indent: -1.7em; margin: 0 0 1.5pt; }
.ref a { white-space: nowrap; }
""".replace("FOOTER", FOOTER)


def expand_links(md):
    md = re.sub(r"\(gh:([^)\s]*)\)", lambda m: f"({REPO}/blob/{TAG}/{m.group(1)})", md)
    return re.sub(r"\(ghtree:([^)\s]*)\)", lambda m: f"({REPO}/tree/{TAG}/{m.group(1)})".replace("/)", ")"), md)


def title_block(h):
    m = re.search(r"<h1>(.*?)</h1>\s*<p>(.*?)\n(.*?)</p>", h, re.S)
    block = (f'<header class="title"><div class="eyebrow">{EYEBROW}</div><h1>{m.group(1)}</h1><div class="bar"></div>'
             f'<div class="meta">{m.group(2)}</div><div class="repo">{m.group(3)}</div></header>')
    return h[:m.start()] + block + h[m.end():]


def headings(h):
    h = re.sub(r"<h2>(\d+)\. (.*?)</h2>", r'<h2 class="sec"><span class="num">\1</span><span>\2</span></h2>', h)
    return re.sub(r"<h2>(Appendix.*?)</h2>", r'<h2 class="sec appendix"><span class="num">A</span><span>\1</span></h2>', h)


def kpis_and_panel(h):
    start = h.index('<span class="num">1</span>')
    p_end = h.index("</p>", start) + len("</p>")
    tiles = "".join(f'<div class="kpi"><div class="n">{n}</div><div class="l">{lbl}</div></div>' for n, lbl in KPIS)
    h = h[:p_end] + f'<div class="kpis">{tiles}</div>' + h[p_end:]
    t = re.compile(r"<table>\s*<thead>\s*<tr>\s*<th>(.*?)</th>\s*<th></th>\s*</tr>\s*</thead>(.*?)</table>", re.S)
    m = t.search(h, p_end)
    panel = f'<div class="panel"><div class="panel-title">{m.group(1)}</div><table>{m.group(2)}</table></div>'
    return h[:m.start()] + panel + h[m.end():]


def tables(h):
    def version_table(m):
        in_section_4 = "How we got" in h[max(0, m.start() - 600):m.start()]

        def row(r):
            v = r.group(1)
            cls = " solid" if v == "v4" else " gray" if v == "v5" else ""
            tr = '<tr class="hl">' if v == "v4" and in_section_4 else "<tr>"
            return f'{tr}\n<td><span class="pill{cls}">{v}</span></td>'
        return re.sub(r"<tr>\s*<td>(v\d)</td>", row, m.group(0))
    h = re.sub(r"<table>\s*<thead>\s*<tr>\s*<th>Version</th>.*?</table>", version_table, h, flags=re.S)
    return re.sub(r"<table>(\s*<thead>\s*<tr>\s*<th>Test</th>)", r'<table class="boldfirst">\1', h)


def code_blocks(h):
    def fix(m):
        body = m.group(2)
        cap = next(((c, f) for start, (c, f) in CAPTIONS.items()
                    if body.startswith(start.replace("<", "&lt;").replace(">", "&gt;"))), None)
        assert cap, "unknown code block"
        body = re.sub(rf"\b({ID}|{PHONE})\b", r'<span class="nw">\1</span>', body)
        body = re.sub(r"(&lt;/?[a-z_]+&gt;)", r'<span class="tag">\1</span>', body)
        body = body.replace(",", ",<wbr>")
        cls = "prompt-a two-col" if "Prompt A" in cap[0] else "prompt-b"
        caption = f'<div class="cap"><span>{cap[0]}</span><a href="{REPO}/blob/{TAG}/{cap[1]}">{cap[1]}</a></div>'
        return f'<pre class="{cls}">{caption}<code{m.group(1)}>{body}</code></pre>'
    return re.sub(r"<pre><code([^>]*)>(.*?)</code></pre>", fix, h, flags=re.S)


def pill_ids(text):
    text = re.sub(rf"\[({ID})\]", r'<span class="idp">[\1]</span>', text)
    return re.sub(rf"(?<![\w-])({PHONE})\b", r'<span class="nw">\1</span>', text)


def examples(h):
    s = h.index('<span class="num">6</span>')
    s = h.index("</h2>", s) + len("</h2>")
    e = h.index('<h2 class="sec">', s)
    cards = []
    for part in re.split(r"(?=<p><strong>)", h[s:e].strip()):
        if not part.strip():
            continue
        m = re.match(r"<p><strong>(.*?)</strong>(.*?)</p>(.*)", part, re.S)
        rest = re.sub(r"<blockquote>\s*(.*?)\s*</blockquote>",
                      lambda b: f'<div class="reply"><div class="who">HomeStretch</div>{pill_ids(b.group(1))}</div>',
                      m.group(3), flags=re.S)
        rest = re.sub(r"<p>(Correct tier and action\..*?)</p>", r'<div class="callout amber">\1</div>', rest, flags=re.S)
        rest = re.sub(r"<p>Known limit:(.*?)</p>", r'<div class="callout amber"><b class="amb">Known limit:</b>\1</div>', rest, flags=re.S)
        rest = re.sub(r"<p>(All three expected problems caught.*?)</p>", r'<div class="callout gray">\1</div>', rest, flags=re.S)
        quote = re.sub(r"<em>(.*?)</em>", r'<span class="quote">\1</span>', m.group(2))
        cards.append(f'<div class="card"><p><span class="card-title">{m.group(1)}</span>{quote}</p>{rest}</div>')
    return h[:s] + "".join(cards) + h[e:]


def callouts(h):
    h = re.sub(r'<p>("Critical miss".*?)</p>', r'<div class="callout gray">\1</div>', h, flags=re.S)
    h = re.sub(r"<p>(Two findings along the way.*?)</p>", r'<div class="callout teal">\1</div>', h, flags=re.S)
    return re.sub(r"<p>(<strong>AI use\.</strong>.*?)</p>", r'<div class="callout teal">\1</div>', h, flags=re.S)


def references(h):
    m = re.search(r"<p><strong>References\.</strong>(.*?)</p>", h, re.S)
    lines = [ln.strip() for ln in m.group(1).strip().split("\n") if ln.strip()]
    refs = "".join(f'<div class="ref">{ln}</div>' for ln in lines)
    return h[:m.start()] + f'<div class="refs"><div class="refs-title">References.</div>{refs}</div>' + h[m.end():]


def make_docx(html, docx):
    if Path("/Applications/Microsoft Word.app").exists():
        script = (f'tell application "Microsoft Word"\n open POSIX file "{html}"\n delay 2\n'
                  f' save as active document file name "{docx}" file format format document\n'
                  f' close active document saving no\nend tell')
        if subprocess.run(["osascript", "-e", script], capture_output=True).returncode == 0:
            return
    print("WARNING: Microsoft Word unavailable; .docx made with textutil has no links or tables")
    subprocess.run(["textutil", "-convert", "docx", str(html), "-output", str(docx)], check=True)


def render(styled, pdf):
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>HomeStretch Assignment 2</title>"
            f"<style>{CSS}</style></head><body>{styled}</body></html>")
    OUT.with_suffix(".html").write_text(page)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", OUT.with_suffix(".html").as_uri()], check=True, capture_output=True)


def main():
    md = SRC.read_text()
    for f in EMBEDDED:
        assert (ROOT / f).read_text().rstrip() in md, f"{f} in the .md does not match the file"
    plain = markdown.markdown(expand_links(md), extensions=["tables", "fenced_code"])
    styled = plain
    for step in (title_block, headings, kpis_and_panel, tables, code_blocks, examples, callouts, references):
        styled = step(styled)
    pdf = OUT.with_suffix(".pdf")
    render(styled, pdf)
    # A code block must not start in the last lines of a page (caption on one page, code on the next). CSS orphans
    # does not move the caption, so check the rendered PDF and, if needed, start that block on a new page.
    pages = [p.extract_text() or "" for p in PdfReader(pdf).pages]
    for caption, first_line in (("Prompt B · cabinet diff", "You are HomeStretch"), ("Prompt A · label reading", "You read OCR text")):
        at = next(i for i, t in enumerate(pages) if caption in t)
        if first_line not in pages[at]:
            cls = "prompt-b" if "Prompt B" in caption else "prompt-a two-col"
            styled = styled.replace(f'<pre class="{cls}">', f'<pre class="{cls} newpage">', 1)
            print(f"moved the {caption.split(' ·')[0]} block to a new page (it started at the bottom of page {at + 1})")
            render(styled, pdf)

    # the .docx comes from the plain HTML: same words and links, simple tables, easy to edit
    tmp = Path(tempfile.gettempdir()) / "homestretch_docx_source.html"
    tmp.write_text("<!doctype html><html><head><meta charset='utf-8'><style>body{font-family:Georgia,serif;font-size:10.5pt}"
                   "table{border-collapse:collapse}th,td{border:1px solid #999;padding:3px}pre{font-size:8pt;white-space:pre-wrap}"
                   f"</style></head><body>{plain}</body></html>")
    make_docx(tmp, OUT.with_suffix(".docx"))

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
    for old in preview.glob("page-*.png"):  # previews this script wrote on an earlier run
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", "80", str(pdf), str(preview / "page")], check=True)

    print(f"PDF: {len(reader.pages)} pages | link annotations (/URI): {len(urls)} ({len(set(urls))} unique) | previews: {preview}")
    print("Strings intact in PDF text:", "all" if not missing else f"MISSING {missing}")
    for u in dict.fromkeys(urls):
        print("  ", u)
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
