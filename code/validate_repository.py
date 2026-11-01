"""Validate public project files. Install requirements-dev.txt first.

Checks explicit identity fields, machine-specific paths, PDF Author metadata,
local Markdown links, and artifact/source hashes. Cannot infer unknown identities.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".cache", ".venv", "venv", "__pycache__", "build", "tmp"}
TEXT = {".py", ".json", ".md", ".tex", ".txt", ".ps1", ".yml", ".toml"}


def validate(forbidden: list[str]) -> dict:
    from pypdf import PdfReader
    issues = []
    files = sorted(p for p in ROOT.rglob("*") if p.is_file()
                   and not any(x in EXCLUDED for x in p.relative_to(ROOT).parts))
    local_path = re.compile(r"[A-Za-z]:[\\/]+(?:Users|Codex)[\\/]", re.I)
    identity = re.compile(r"""["']?(?:student[ _-]?(?:id|name)|owner[ _-]?name|学号|姓名)["']?\s*[:：]\s*["']?[A-Za-z0-9\u4e00-\u9fff]+""", re.I)
    text_count = pdf_count = 0
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        content = ""
        if path.suffix in TEXT:
            text_count += 1
            content = path.read_text(encoding="utf-8-sig")
            if path.suffix == ".md":
                for target in re.findall(r"!?\[[^\]]*\]\(([^)\s]+)\)", content):
                    if re.match(r"(?:[a-z]+:|#)", target, re.I):
                        continue
                    linked = unquote(target.split("#", 1)[0])
                    if linked and not (path.parent / linked).exists():
                        issues.append({"file": relative, "issue": "broken local Markdown link", "target": target})
        elif path.suffix == ".pdf":
            pdf_count += 1
            pdf = PdfReader(path)
            metadata = pdf.metadata or {}
            if str(metadata.get("/Author", "")).strip():
                issues.append({"file": relative, "issue": "nonempty PDF Author field"})
            content = "\n".join(str(v) for v in metadata.values()) + "\n" + "\n".join(p.extract_text() or "" for p in pdf.pages)
        if local_path.search(content) or identity.search(content):
            issues.append({"file": relative, "issue": "local identity path or populated identity field"})
        if any(x.casefold() in content.casefold() for x in forbidden if x):
            issues.append({"file": relative, "issue": "caller-specified forbidden text"})
    def check_hash(relative: str, expected: str) -> None:
        path = ROOT / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            issues.append({"file": relative, "issue": "missing file or stale hash"})
    provenance = json.loads((ROOT / "vendor/provenance.json").read_text("utf-8"))
    for name, expected in provenance["files"].items():
        check_hash("vendor/minbpe/" + name, expected["sha256"])
    pilot = json.loads((ROOT / "results/quota_pilot.json").read_text("utf-8"))
    document_scores = pilot["document_scores"]
    check_hash(document_scores["path"], document_scores["sha256"])
    uncertainty = json.loads((ROOT / "results/quota_uncertainty.json").read_text("utf-8"))
    check_hash(document_scores["path"], uncertainty["input_sha256"])
    manifest = json.loads((ROOT / "figures/manifest.json").read_text("utf-8"))
    for entry in manifest["data_audit"]:
        check_hash(entry["path"], entry["sha256"])
    for figure in manifest["figures"]:
        for key in ("latex_fragment", "standalone_wrapper"):
            if not (ROOT / figure[key]).is_file():
                issues.append({"file": figure[key], "issue": "figure source missing"})
        for kind, relative in figure["files"].items():
            check_hash(relative, figure["output_sha256"][kind])
    return {"all_passed": not issues, "public_files_checked": len(files),
            "text_files_checked": text_count, "pdf_files_checked": pdf_count,
            "upstream_files_verified": len(provenance["files"]),
            "figure_data_files_verified": len(manifest["data_audit"]),
            "privacy_scope": "Public text and PDF extracted text/Author metadata; ignored caches/builds excluded. Unknown identities cannot be inferred or guaranteed absent.",
            "issues": issues}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forbidden-text", action="append", default=[],
                        help="Additional exact text to reject; its value is never stored")
    args = parser.parse_args()
    result = validate(args.forbidden_text)
    output = ROOT / "results/repository_validation.json"
    prior = json.loads(output.read_text("utf-8")) if output.exists() else {}
    prior["repository_checks"] = result
    output.write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
