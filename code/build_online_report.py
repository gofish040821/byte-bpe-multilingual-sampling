"""Build the complete GitHub reading edition from the same sources as the PDF."""

import argparse
from html import escape
import json
import re
import sys

sys.dont_write_bytecode = True
from build_latex_report import (
    ABSTRACT, CONTENT_FILES, KEYWORDS, ROOT, TITLE_EN, TITLE_ZH, SourceReader,
    equation, heading_text,
)

OUTPUT = ROOT / "reports" / "online.md"
PDF_URL = "https://dolomitiaugust.github.io/byte-bpe-multilingual-sampling/reports/tokenizer_analysis_report.pdf"


def literal(text):
    """Keep identifiers, brackets, emphasis marks and regex fragments literal."""
    return re.sub(r"([\\`*_\[\]~$])", r"\\\1", escape(str(text), quote=False))


def table(headers, rows):
    def cell(value):
        raw = str(value)
        if raw.isascii() and any(ch in raw for ch in "[]|\\") and "`" not in raw and "\n" not in raw:
            # Code spans retain regex syntax and meaningful leading spaces.
            return "`" + raw.replace("|", r"\|") + "`"
        return literal(raw).replace("|", "&#124;").replace("\n", "<br>")

    def line(values):
        return "| " + " | ".join(map(cell, values)) + " |"

    return "\n".join([line(headers), line(["---"] * len(headers)), *(line(row) for row in rows)])


def fence(source, language):
    longest = max((len(s) for s in re.findall(r"`+", source)), default=0)
    delimiter = "`" * max(3, longest + 1)
    return f"{delimiter}{language}\n{source}\n{delimiter}"


def annotated(block, reader):
    rows = reader.rows(block)
    path, start, end = block["file"], block["start"], block["end"]
    link = f"[{path} · 第 {start}–{end} 行](../vendor/{path}#L{start}-L{end})"
    numbered = "\n".join(f"{n:>3}  {source}" for n, source, _ in rows)
    notes = table(["行号", "逐行解释"], [(n, note) for n, _, note in rows])
    return "\n\n".join([link, fence(numbered, "text"), notes])


def render_body(block, reader):
    kind = block["type"]
    if kind == "p":
        return literal(block["text"])
    if kind == "table":
        return table(block["headers"], block["rows"])
    if kind == "bullets":
        return "\n".join("- " + literal(item) for item in block["items"])
    if kind == "annotated":
        return annotated(block, reader)
    if kind == "code":
        source = block["text"]
        language = "python" if source.startswith("from ") else "sh" if source.startswith("python ") else "text"
        return fence(source, language)
    if kind == "figure":
        caption = literal(block["caption"])
        # The first sentence describes the graphic, the remainder explains the evidence.
        alt_text = caption.split("。", 1)[0]
        return f"![{alt_text}](../{block['path']})\n\n{caption}"
    if kind == "formula":
        formula, _ = equation(block)
        return fence(formula, "math")
    if kind == "source":
        return f"{literal(block['text'])} [原文]({block['url']})"
    raise ValueError(f"Unknown report block type: {kind}")


def render_document():
    reader = SourceReader()
    front = [f"# {TITLE_ZH}", f"*{TITLE_EN}* · Technical Research Report",
             f"[在线查看 PDF 排印版]({PDF_URL}) · [项目主页](../README.md)",
             "## 摘要", literal(ABSTRACT), "**关键词**　" + literal(KEYWORDS)]
    contents, body = [], []
    for number, (filename, deep) in enumerate(CONTENT_FILES, 1):
        blocks = json.loads((ROOT / "reports" / "content" / filename).read_text(encoding="utf-8"))
        appendix = filename == "bpe_analysis.json"
        name = ("附录 A　" if appendix else "") + heading_text(blocks[0]["text"])
        contents.append(f"[{name}](#part-{number})")
        body.extend([f'<a name="part-{number}"></a>', f"## {name}"])
        for block in blocks[1:]:
            kind = block["type"]
            if appendix and kind == "figure":
                continue  # These figures appear in the main results, as in the PDF.
            if kind in {"section", "subsection"}:
                level = "####" if deep and kind == "subsection" else "###"
                body.append(f"{level} {literal(heading_text(block['text']))}")
            else:
                body.append(render_body(block, reader))
    return "\n\n".join([*front, " · ".join(contents), *body]) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check the published edition against the sources.")
    args = parser.parse_args()
    document = render_document()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != document:
            raise SystemExit("Rebuild reports/online.md with code/build_online_report.py")
    else:
        OUTPUT.write_text(document, encoding="utf-8", newline="\n")
