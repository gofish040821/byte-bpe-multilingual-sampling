"""Build the tokenization analysis report as editable, native LaTeX.

The checked report JSON remains the content source.  This program changes only
the presentation: mathematical notation, tables, code, and native TikZ figures.
Run with --check-only to validate and render in memory without writing main.tex.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from string import Template
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTENT_FILES = (
    ("research_overview.json", False),
    ("execution_evidence.json", False),
    ("multilingual_sampling.json", False),
    ("bpe_analysis.json", True),
)

PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=18mm,top=19mm,bottom=19mm,headheight=15pt,headsep=6mm]{geometry}
\usepackage{fontspec}
\usepackage{xeCJK}
\IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{TeX Gyre Termes}}
\IfFontExistsTF{Arial}{\setsansfont{Arial}}{\setsansfont{TeX Gyre Heros}}
\IfFontExistsTF{Consolas}{\setmonofont[Scale=0.94]{Consolas}}{\setmonofont[Scale=0.94]{Latin Modern Mono}}
\IfFontExistsTF{SimSun}{\setCJKmainfont[AutoFakeBold=1.8]{SimSun}}{\setCJKmainfont{FandolSong-Regular}}
\IfFontExistsTF{Microsoft YaHei}{\setCJKsansfont{Microsoft YaHei}}{\setCJKsansfont{FandolHei-Regular}}
\IfFontExistsTF{SimSun}{\setCJKmonofont{SimSun}}{\setCJKmonofont{FandolSong-Regular}}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,array,longtable}
\usepackage{fvextra}
\usepackage{graphicx}
\usepackage{tikz,pgfplots}
\usetikzlibrary{arrows.meta,positioning,calc,fit,backgrounds,patterns,decorations.pathreplacing,matrix}
\pgfplotsset{compat=1.18}
\usepackage{caption}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{needspace}
\usepackage{placeins}
\usepackage{setspace}
\usepackage{fancyhdr}
\usepackage{xurl}
\usepackage[unicode,hidelinks,bookmarksnumbered=true,hypertexnames=false,pdfencoding=auto]{hyperref}
\usepackage{bookmark}
\hypersetup{pdftitle={字节级 BPE 分析与多语言抽样设计},pdfsubject={BPE 与多语言分词器训练语料比例},pdfauthor={}}
\urlstyle{same}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.48em}
\setstretch{1.20}
\setlength{\emergencystretch}{2em}
\raggedbottom
\setcounter{secnumdepth}{3}
\setcounter{tocdepth}{2}
\renewcommand{\contentsname}{目录}
\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}
\titleformat{\section}{\sffamily\large\bfseries}{\thesection}{0.65em}{}
\titleformat{\subsection}{\sffamily\normalsize\bfseries}{\thesubsection}{0.65em}{}
\titleformat{\subsubsection}{\sffamily\normalsize\bfseries}{\thesubsubsection}{0.65em}{}
\titlespacing*{\section}{0pt}{1.5em}{0.7em}
\titlespacing*{\subsection}{0pt}{1.1em}{0.45em}
\titlespacing*{\subsubsection}{0pt}{0.9em}{0.35em}
\setlist[itemize]{leftmargin=1.7em,itemsep=0.3em,topsep=0.4em,parsep=0pt}
\captionsetup{font=small,labelfont=bf,labelsep=quad,skip=7pt,justification=justified,singlelinecheck=false}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small Tokenization Analysis}
\fancyhead[R]{\small 原理、源码与实验记录}
\fancyfoot[C]{\small\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\renewcommand{\footrulewidth}{0pt}
\setlength{\tabcolsep}{4pt}
\setlength{\LTpre}{0.45em}
\setlength{\LTpost}{0.65em}
\newlength{\BpeDocTableWidth}
\newcommand{\BpeDocCodeCell}[1]{{\ttfamily\fontsize{7.8}{10.3}\selectfont #1}}
\newcommand{\SourceLineNumber}[1]{{\ttfamily\fontsize{8.2}{10.3}\selectfont #1}}
\newcommand{\BpeDocCodeInline}[1]{{\ttfamily #1}}
\newcommand{\BpeDocSection}[2]{\section{\texorpdfstring{#1}{#2}}}
\newcommand{\BpeDocSubsection}[2]{\subsection{\texorpdfstring{#1}{#2}}}
\newcommand{\BpeDocSubsubsection}[2]{\subsubsection{\texorpdfstring{#1}{#2}}}
\begin{document}
"""

TITLE_ZH = "字节级 BPE 分析与多语言抽样设计"
TITLE_EN = "Byte-Level BPE Analysis and Multilingual Sampling Design"
ABSTRACT = (
    "本文通过源码与运行记录，跟踪 MinBPE 如何学习和应用合并规则。训练 abababab 时，第一轮得到四个连续的 ab 词元。"
    "第二轮统计到三个相邻位置对，从左往右合并时每个词元只能用一次，因此执行两次替换。"
    "另一个例子说明，编码新文本时按训练得到的规则优先级合并。"
    "在选定的八个普通文本输入上，MinBPE 包装器与 cl100k_base 逐个编号一致，解码均还原原文。验证程序的十七组行为检查全部通过。"
    "另在真实德语和西语语料上比较三种配额、三个种子。将分词器训练份额从 90:10 改为 75:25 后，二元语言模型在留出集上的双语等权字节困惑度从 8.4111 降至 8.2738（下降 1.63%），其中西语改善，德语略有退步。50:50 的均衡基线为 8.2709。"
)
KEYWORDS = "字节级 BPE；编码一致性；UTF-8；多语言抽样；可复现性。"

COVER_TEMPLATE = Template(r"""\begin{center}
{\sffamily\fontsize{19}{26}\selectfont\bfseries $title\par}
\vspace{3mm}
{\large $subtitle\par}
\vspace{2mm}
{\small Technical Research Report\par}
\end{center}
\renewcommand{\abstractname}{摘要}
\begin{abstract}
$abstract
\end{abstract}
\noindent\textbf{关键词：}$keywords
\par\vspace{2mm}
\pagenumbering{arabic}
""")

SPECIAL_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "%": r"\%",
    "_": r"\_",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
}

MATH_IDENTIFIERS = {
    "alpha": r"\alpha", "α": r"\alpha",
    "q_l": r"q_l", "p_i": r"p_i", "n_l": r"n_l",
    "n_i": r"n_i", "n_j": r"n_j", "T_l": r"T_l", "R_l": r"R_l",
    "w_de": r"w_{\mathrm{de}}", "w_es": r"w_{\mathrm{es}}",
    "R_de": r"R_{\mathrm{de}}", "R_es": r"R_{\mathrm{es}}",
}

CODE_WORDS = {
    "self", "super", "class", "Tokenizer", "BasicTokenizer", "RegexTokenizer",
    "GPT4Tokenizer", "bytes", "dict", "list", "set", "zip", "max", "min",
    "lambda", "append", "extend", "return", "break", "continue", "assert",
    "ValueError", "KeyError", "NotImplementedError", "None", "True", "False",
    "get_stats", "merge", "train", "encode", "decode", "merges", "vocab",
    "pair", "idx", "ids", "stats", "rank", "pattern", "verbose", "count",
    "counts", "bpe", "parts", "token", "text_bytes", "get", "findall",
    "enumerate", "UTF8", "GPT4_SPECIAL_TOKENS", "GPT4_SPLIT_PATTERN",
    "none_raise", "all", "none", "float32", "get_encoding",
}

# Ordered alternatives keep complete mathematical expressions together.  ASCII
# boundaries are used intentionally: adjacent Chinese letters are not a barrier.
INLINE_PATTERN = re.compile(
    r"(?:T_l|R_l|R_de|R_es|J)\((?:q|0\.5|50:50)\)"
    r"|(?<![A-Za-z0-9_])(?:w_de|w_es|R_de|R_es|q_l|p_i|n_l|n_i|n_j|T_l|R_l|alpha)(?![A-Za-z0-9_])"
    r"|[αΣ≤≥→−]"
    r"|√\d+(?:\.\d+)?"
    r"|<\|[^\n]*?\|>"
    r"|[A-Za-z_][A-Za-z0-9_]*(?:[./][A-Za-z_][A-Za-z0-9_]*)*"
    r"|(?<![A-Za-z0-9])[a-f0-9]{24,}(?![A-Za-z0-9])"
)


def normalize_unicode(text: str) -> str:
    """Avoid relying on a colour emoji font in a scientific PDF."""
    return str(text).replace("🙂", "U+1F642").replace("🚀", "U+1F680")


def tex_escape(text: str) -> str:
    return "".join(SPECIAL_ESCAPES.get(ch, ch) for ch in normalize_unicode(text))


def breakable_code(text: str, *, anywhere: bool = True) -> str:
    """Preserve glyphs while allowing a break between any two code characters.

    The breaks add no visible hyphen or replacement glyph.  Literal character
    commands preserve spaces and TeX metacharacters instead of interpreting them.
    """
    pieces = []
    for char in normalize_unicode(text):
        if char == "\t":
            piece = r"\char32\relax" * 4
        elif ord(char) < 128 and (char.isspace() or char in SPECIAL_ESCAPES):
            piece = rf"\char{ord(char)}\relax"
        else:
            piece = tex_escape(char)
        pieces.append(piece)
    if anywhere:
        return r"\allowbreak{}".join(pieces)
    is_hash = bool(re.fullmatch(r"[a-f0-9]{24,}", text))
    result = []
    for index, piece in enumerate(pieces):
        result.append(piece)
        if index < len(pieces) - 1 and (text[index] in "_./\\,:;=-" or is_hash and (index + 1) % 8 == 0):
            result.append(r"\allowbreak{}")
    return "".join(result)


def math_inline(token: str) -> str | None:
    if token in MATH_IDENTIFIERS:
        return MATH_IDENTIFIERS[token]
    symbols = {"Σ": r"\sum", "≤": r"\leq", "≥": r"\geq", "→": r"\rightarrow", "−": "-"}
    if token in symbols:
        return symbols[token]
    if token.startswith("√"):
        return r"\sqrt{" + token[1:] + "}"
    match = re.fullmatch(r"(T_l|R_l|R_de|R_es|J)\((q|0\.5|50:50)\)", token)
    if match:
        name = MATH_IDENTIFIERS.get(match[1], match[1])
        arg = r"\tfrac{1}{2}" if match[2] == "50:50" else match[2]
        return name + "(" + arg + ")"
    return None


def rich_text(text: str) -> str:
    text = normalize_unicode(text)
    out, position = [], 0
    for match in INLINE_PATTERN.finditer(text):
        out.append(tex_escape(text[position:match.start()]))
        token = match.group()
        math = math_inline(token)
        if math is not None:
            out.append(r"\(" + math + r"\)")
        elif token in CODE_WORDS or any(c in token for c in "_./<|") or re.fullmatch(r"[a-f0-9]{24,}", token):
            out.append(r"\BpeDocCodeInline{" + breakable_code(token, anywhere=False) + "}")
        elif token in {"l", "q", "J", "T"} and (
            token in {"J", "T"} or text[max(0, match.start()-4):match.start()].endswith(("语言 ", "份额 ", "候选 "))
        ):
            out.append(r"\(" + token + r"\)")
        else:
            out.append(tex_escape(token))
        position = match.end()
    out.append(tex_escape(text[position:]))
    return "".join(out)


def heading_text(text: str) -> str:
    return re.sub(r"^\s*\d+[.、]\s*", "", text).strip()


def render_heading(text: str, level: int) -> str:
    text = heading_text(text)
    macro = {1: "BpeDocSection", 2: "BpeDocSubsection", 3: "BpeDocSubsubsection"}[level]
    return r"\Needspace{9\baselineskip}" + "\n" + rf"\{macro}" + "{" + rich_text(text) + "}{" + tex_escape(text) + "}\n"


def table_widths(block: dict[str, Any]) -> list[float]:
    count = len(block["headers"])
    explicit = block.get("widths")
    if explicit and len(explicit) == count and sum(explicit) > 0:
        return [float(x) / sum(explicit) for x in explicit]
    presets = {2: [0.29, 0.71], 3: [0.23, 0.385, 0.385], 4: [0.14, 0.29, 0.34, 0.23], 5: [0.10, 0.23, 0.13, 0.14, 0.40]}
    return presets.get(count, [1 / count] * count)


def render_table(block: dict[str, Any]) -> str:
    headers = block["headers"]
    count = len(headers)
    if count < 1 or any(len(row) != count for row in block["rows"]):
        raise ValueError("A table has an invalid row width")
    widths = table_widths(block)
    spec = "".join(r">{\raggedright\arraybackslash}p{" + f"{width:.6f}" + r"\BpeDocTableWidth}" for width in widths)
    head = " & ".join(r"\textbf{" + rich_text(str(cell)) + "}" for cell in headers) + r" \\" + "\n"
    small_table = len(block["rows"]) <= 8
    out = [
        r"\begingroup\fontsize{9.3}{12.7}\selectfont\setstretch{1}",
        rf"\setlength{{\BpeDocTableWidth}}{{\dimexpr\linewidth-{2*count}\tabcolsep\relax}}",
        r"\renewcommand{\arraystretch}{1.15}",
    ]
    if small_table:
        out.extend([r"\par\addvspace{0.45em}", r"\noindent\begin{minipage}{\linewidth}", r"\begin{tabular}{" + spec + "}", r"\toprule", head, r"\midrule"])
    else:
        out.extend([r"\begin{longtable}{" + spec + "}", r"\toprule", head, r"\midrule\endfirsthead", r"\toprule", head,
                    r"\midrule\endhead", r"\midrule\endfoot", r"\bottomrule\endlastfoot"])
    for row in block["rows"]:
        out.append(" & ".join(rich_text(str(cell)) for cell in row) + r" \\[3pt]")
    if small_table:
        out.extend([r"\bottomrule", r"\end{tabular}", r"\end{minipage}\par\addvspace{0.65em}"])
    else:
        out.append(r"\end{longtable}")
    out.extend([r"\endgroup", ""])
    return "\n".join(out)


class SourceReader:
    def __init__(self) -> None:
        self.cache: dict[str, tuple[list[str], set[int]]] = {}
        self.annotated_blocks = 0
        self.execution_lines = 0

    def source(self, relative: str) -> tuple[list[str], set[int]]:
        if relative not in self.cache:
            path = (ROOT / "vendor" / relative).resolve()
            vendor = (ROOT / "vendor").resolve()
            if vendor not in path.parents:
                raise ValueError(f"Source path leaves vendor directory: {relative}")
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
            docstrings = set()
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                body = getattr(node, "body", None)
                if isinstance(body, list) and body:
                    first = body[0]
                    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                        docstrings.update(range(first.lineno, first.end_lineno + 1))
            self.cache[relative] = (text.splitlines(), docstrings)
        return self.cache[relative]

    def rows(self, block: dict[str, Any]) -> list[tuple[int, str, str]]:
        lines, docstrings = self.source(block["file"])
        start, end = int(block["start"]), int(block["end"])
        if not 1 <= start <= end <= len(lines):
            raise ValueError(f"Invalid source range: {block['file']}:{start}-{end}")
        rows = []
        for number in range(start, end + 1):
            original = lines[number - 1]
            if not original.strip() or original.lstrip().startswith("#") or number in docstrings:
                continue
            note = block["notes"].get(str(number))
            if not note:
                raise ValueError(f"Missing explanation for executable line {block['file']}:{number}")
            rows.append((number, original, note))
        self.annotated_blocks += 1
        self.execution_lines += len(rows)
        return rows


def render_annotated(block: dict[str, Any], reader: SourceReader) -> str:
    rows = reader.rows(block)
    label = f"{block['file']}，第 {block['start']}–{block['end']} 行（仅列执行语句）"
    header = r"\textbf{行号} & \textbf{原代码} & \textbf{逐行解释} \\"
    small_table = len(rows) <= 6
    spec = r">{\raggedleft\arraybackslash}p{0.065\BpeDocTableWidth}>{\raggedright\arraybackslash}p{0.475\BpeDocTableWidth}>{\raggedright\arraybackslash}p{0.460\BpeDocTableWidth}"
    out = [
        r"\Needspace{4\baselineskip}",
        r"\begingroup\fontsize{8.9}{12.2}\selectfont\setstretch{1}",
        r"\setlength{\BpeDocTableWidth}{\dimexpr\linewidth-6\tabcolsep\relax}",
        r"\renewcommand{\arraystretch}{1.08}",
    ]
    if small_table:
        out.extend([r"\par\addvspace{0.45em}", r"\noindent\begin{minipage}{\linewidth}",
                    r"{\small " + rich_text(label) + r"}\par\vspace{0.35em}",
                    r"\begin{tabular}{" + spec + "}", r"\toprule", header, r"\midrule"])
    else:
        out.extend([r"{\small " + rich_text(label) + "}\n",
                    r"\begin{longtable}{" + spec + "}", r"\toprule", header,
                    r"\midrule\endfirsthead", r"\toprule", header,
                    r"\midrule\endhead", r"\midrule\endfoot", r"\bottomrule\endlastfoot"])
    for number, original, note in rows:
        out.append(
            rf"\SourceLineNumber{{{number}}} & \BpeDocCodeCell{{" + breakable_code(original)
            + "} & " + rich_text(note) + r" \\[3pt]"
        )
    if small_table:
        out.extend([r"\bottomrule", r"\end{tabular}", r"\end{minipage}\par\addvspace{0.65em}"])
    else:
        out.append(r"\end{longtable}")
    out.extend([r"\endgroup", ""])
    return "\n".join(out)


def equation(block: dict[str, Any]) -> tuple[str, str]:
    plain = block.get("text", "")
    if plain.startswith("q_l") or plain.startswith("p_i"):
        formula = r"q_l=\frac{n_l^{\alpha}}{\displaystyle\sum_j n_j^{\alpha}},\qquad 0\leq\alpha\leq1."
        label = "eq:language-sampling"
    elif plain.startswith("T_l"):
        formula = r"T_l=\frac{\#\,\mathrm{tokens}_l}{\#\,\mathrm{characters}_l}."
        label = "eq:tokens-per-character"
    elif plain.startswith("R_l"):
        formula = (
            r"\begin{aligned}" + "\n"
            + r"R_l(q)&=\frac{T_l(q)}{T_l(0.5)},\\[4pt]" + "\n"
            + r"J(q)&=w_{\mathrm{de}}R_{\mathrm{de}}(q)+w_{\mathrm{es}}R_{\mathrm{es}}(q),"
            + r"\qquad w_{\mathrm{de}}+w_{\mathrm{es}}=1."
            + "\n" + r"\end{aligned}"
        )
        label = "eq:comparison-objective"
    else:
        formula = block.get("latex", "").replace("\\\\", "\\")
        if not formula:
            raise ValueError(f"Formula has no LaTeX representation: {plain}")
        label = ""
    return formula, label


def render_formula(block: dict[str, Any]) -> str:
    formula, label = equation(block)
    return "\n".join([r"\begin{equation}" + (rf"\label{{{label}}}" if label else ""), formula, r"\end{equation}", ""])


def render_figure(block: dict[str, Any]) -> str:
    name = Path(block["path"]).stem
    if name not in {"bpe_merges", "overlap", "language_sampling"}:
        raise ValueError(f"No native LaTeX figure registered for {name}")
    caption = re.sub(r"^\s*图\s*\d+\s*[：:.]?\s*", "", block["caption"])
    return "\n".join([
        r"\begin{figure}[htbp]", r"\centering",
        rf"\input{{figures/{name}.tex}}",
        r"\caption{" + rich_text(caption) + "}",
        rf"\label{{fig:{name.replace('_', '-')}}}", r"\end{figure}", "",
    ])


def render_source(block: dict[str, Any]) -> str:
    url = block["url"]
    if any(char in url for char in "{}\n\r"):
        raise ValueError("Unsafe URL delimiter in source")
    return (
        r"\begin{quote}\footnotesize\setlength{\parskip}{0pt} " + rich_text(block["text"]) + "\n" + r"\par\nobreak" + "\n"
        + r"\url{" + url + "}\n" + r"\end{quote}" + "\n"
    )


def render_document() -> tuple[str, dict[str, Any]]:
    reader = SourceReader()
    cover = COVER_TEMPLATE.substitute(title=tex_escape(TITLE_ZH), subtitle=tex_escape(TITLE_EN),
                                      abstract=tex_escape(ABSTRACT), keywords=tex_escape(KEYWORDS))
    out = [PREAMBLE, cover]
    block_count = 0
    figures = []
    for file_index, (filename, deep_hierarchy) in enumerate(CONTENT_FILES):
        blocks = json.loads((ROOT / "reports" / "content" / filename).read_text(encoding="utf-8"))
        if not isinstance(blocks, list) or not blocks or blocks[0].get("type") != "section":
            raise ValueError(f"Expected a block list beginning with section: {filename}")
        if file_index:
            out.append(r"\clearpage" if filename == "bpe_analysis.json" else r"\FloatBarrier\par\bigskip")
        if filename == "bpe_analysis.json":
            out.append(r"\appendix")
        out.append(f"% Content source: reports/content/{filename}")
        for index, block in enumerate(blocks):
            block_count += 1
            kind = block["type"]
            # Main-text mechanism figures are not duplicated in the appendix.
            if filename == "bpe_analysis.json" and kind == "figure":
                continue
            if kind in {"section", "subsection"}:
                level = 1 if index == 0 else (3 if kind == "subsection" and deep_hierarchy else 2)
                heading = render_heading(block["text"], level)
                # An indivisible short source table must fit with its heading.
                # Reserve space before the heading, not only before the table.
                if index + 1 < len(blocks) and blocks[index + 1]["type"] == "annotated":
                    following = blocks[index + 1]
                    lines, docstrings = reader.source(following["file"])
                    count = sum(
                        bool(lines[n - 1].strip())
                        and not lines[n - 1].lstrip().startswith("#")
                        and n not in docstrings
                        for n in range(following["start"], following["end"] + 1)
                    )
                    if count <= 6:
                        heading = heading.replace(r"\Needspace{9\baselineskip}", r"\Needspace{18\baselineskip}")
                out.append(heading)
            elif kind == "p":
                out.append(rich_text(block["text"]) + "\n")
            elif kind == "bullets":
                out.extend([r"\begin{itemize}", *(r"\item " + rich_text(item) for item in block["items"]), r"\end{itemize}", ""])
            elif kind == "table":
                out.append(render_table(block))
            elif kind == "annotated":
                out.append(render_annotated(block, reader))
            elif kind == "code":
                code = normalize_unicode(block["text"])
                if r"\end{Verbatim}" in code:
                    raise ValueError("Code contains the verbatim environment terminator")
                out.append(
                    r"\begin{Verbatim}[fontsize=\small,breaklines=true,breakanywhere=true,breakautoindent=true,tabsize=4,breaksymbolleft={},breaksymbolright={}]"
                    + "\n" + code + "\n" + r"\end{Verbatim}" + "\n"
                )
            elif kind == "formula":
                out.append(render_formula(block))
            elif kind == "figure":
                out.append(render_figure(block))
                figures.append(str(Path("figures") / (Path(block["path"]).stem + ".tex")))
            elif kind == "source":
                out.append(render_source(block))
            else:
                raise ValueError(f"Unknown block type {kind} in {filename}")
    out.append(r"\end{document}")
    tex = "\n\n".join(out) + "\n"
    summary = {
        "content_blocks": block_count,
        "annotated_blocks": reader.annotated_blocks,
        "annotated_execution_lines": reader.execution_lines,
        "native_figures": figures,
        "latex_characters": len(tex),
        "content_files": [name for name, _ in CONTENT_FILES],
    }
    return tex, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "latex" / "main.tex")
    parser.add_argument("--check-only", action="store_true", help="Validate and generate in memory, without writing files")
    args = parser.parse_args()
    tex, summary = render_document()
    if args.check_only:
        summary["mode"] = "validated without writing main.tex"
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(tex, encoding="utf-8")
        summary["output"] = str(args.output.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
