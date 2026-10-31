"""Build the native LaTeX report, compile it with Tectonic, and export figures.

This helper uses only the Python standard library.  Tectonic is an external
executable; optional SVG/PNG exports use Poppler's pdftocairo/pdftoppm.  No shell
escape, ReportLab, Matplotlib, or paid API is used by this report build.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
LATEX = REPORTS / "latex"


def expanded_path(value: str | Path) -> Path:
    return Path(os.path.expandvars(os.fspath(value))).expanduser().resolve()


def package_version(path: Path) -> tuple[int, ...]:
    for part in path.parts:
        match = re.match(r"OpenAI\.Codex(?:PrimaryRuntime)?[._v-]+([0-9][0-9.\-]*)", part)
        if match:
            return tuple(int(x) for x in re.findall(r"\d+", match[1]))
    return ()


def windows_apps_roots() -> list[Path]:
    roots = []
    for value in (os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432"), "C:/Program Files"):
        if value:
            path = Path(value) / "WindowsApps"
            if path not in roots:
                roots.append(path)
    return roots


def safe_glob(directory: Path, pattern: str) -> list[Path]:
    try:
        return [path for path in directory.glob(pattern) if path.is_file()]
    except OSError:
        return []


def appx_install_locations(package: str) -> list[Path]:
    """Read package locations when WindowsApps enumeration is restricted."""
    if os.name != "nt" or not re.fullmatch(r"[A-Za-z0-9.*_-]+", package):
        return []
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if not powershell:
        return []
    command = [powershell, "-NoProfile", "-NonInteractive", "-Command",
               f"Get-AppxPackage -Name '{package}' | Select-Object -ExpandProperty InstallLocation"]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=15,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode:
        return []
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def executable_from_argument(value: str, label: str) -> Path:
    candidate = expanded_path(value)
    if candidate.is_file():
        return candidate
    found = shutil.which(value)
    if found:
        return Path(found).resolve()
    raise FileNotFoundError(f"{label} 指定的程序不存在：{value}")


def find_tectonic(explicit: str | None) -> tuple[Path, str]:
    if explicit:
        return executable_from_argument(explicit, "--tectonic"), "--tectonic"
    if os.environ.get("CODEX_TECTONIC_PATH"):
        return executable_from_argument(os.environ["CODEX_TECTONIC_PATH"], "CODEX_TECTONIC_PATH"), "CODEX_TECTONIC_PATH"
    found = shutil.which("tectonic")
    if found:
        return Path(found).resolve(), "PATH"
    candidates = []
    if os.name == "nt":
        for base in windows_apps_roots():
            candidates.extend(safe_glob(base, "OpenAI.Codex_*/app/resources/tectonic/tectonic.exe"))
        if not candidates:
            for package in appx_install_locations("OpenAI.Codex"):
                candidate = package / "app/resources/tectonic/tectonic.exe"
                if candidate.is_file():
                    candidates.append(candidate)
    candidates.sort(key=lambda p: (package_version(p), str(p)), reverse=True)
    if candidates:
        return candidates[0].resolve(), "Codex WindowsApps package"
    raise FileNotFoundError(
        "未找到 Tectonic。请安装 Tectonic 后加入 PATH，或使用 --tectonic 指定程序，"
        "也可设置 CODEX_TECTONIC_PATH。"
    )


def find_poppler(name: str) -> Path | None:
    found = shutil.which(name)
    if found:
        return Path(found).resolve()
    if os.name != "nt":
        return None
    executable = name + ".exe"
    candidates = []
    for base in windows_apps_roots():
        candidates.extend(safe_glob(base, f"OpenAI.CodexPrimaryRuntime*/dependencies/native/poppler/Library/bin/{executable}"))
    if not candidates:
        for package in appx_install_locations("OpenAI.CodexPrimaryRuntime*"):
            candidate = package / f"dependencies/native/poppler/Library/bin/{executable}"
            if candidate.is_file():
                candidates.append(candidate)
    runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"
    for suffix in (f"native/poppler/Library/bin/{executable}", f"bin/override/{executable}", f"bin/fallback/{executable}"):
        candidate = runtime / suffix
        if candidate.is_file():
            candidates.append(candidate)
    candidates.sort(key=lambda p: (package_version(p), str(p)), reverse=True)
    return candidates[0].resolve() if candidates else None


def compile_environment(explicit_cache: str | None) -> tuple[dict[str, str], str]:
    # Respect caller-provided settings without guessing a machine-specific
    # cache directory. Tectonic manages its own default cache otherwise.
    env = dict(os.environ)
    env["TECTONIC_UNTRUSTED_MODE"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if explicit_cache:
        env["TECTONIC_CACHE_DIR"] = str(expanded_path(explicit_cache))
        return env, "--cache-dir"
    if env.get("TECTONIC_CACHE_DIR"):
        return env, "TECTONIC_CACHE_DIR"
    return env, "Tectonic default cache"


def run(command: list[str], *, cwd: Path, env: dict[str, str], log: Path | None = None) -> None:
    print("运行：" + subprocess.list2cmdline(command), flush=True)
    completed = subprocess.run(
        command, cwd=str(cwd), env=env, shell=False, check=False,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(completed.stdout, encoding="utf-8")
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.returncode:
        suffix = f"；日志：{log}" if log else ""
        raise RuntimeError(f"命令失败，退出码 {completed.returncode}{suffix}")


def compile_tex(source: Path, executable: Path, output: Path, env: dict[str, str]) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    command = [
        str(executable), "-X", "compile", "--outdir", str(output),
        "--outfmt", "pdf", "--print", "--untrusted", source.name,
    ]
    run(command, cwd=source.parent, env=env, log=output / (source.stem + ".compile.log"))
    result = output / (source.stem + ".pdf")
    if not result.is_file():
        raise RuntimeError(f"编译器返回成功，但未生成预期 PDF：{result}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tectonic", help="Tectonic executable path; otherwise use CODEX_TECTONIC_PATH, PATH, or the installed Codex package")
    parser.add_argument("--cache-dir", help="Explicit Tectonic cache; otherwise honor TECTONIC_CACHE_DIR or use Tectonic's default")
    parser.add_argument("--svg", action="store_true", help="Also export standalone figures as SVG when pdftocairo is available")
    parser.add_argument("--png", action="store_true", help="Also export standalone figures as PNG when pdftoppm is available")
    parser.add_argument("--dpi", type=int, default=300, help="PNG resolution, default 300 dpi")
    parser.add_argument("--skip-figures", action="store_true", help="Build only the main report, without standalone figure exports")
    parser.add_argument("--check-tools", action="store_true", help="Show detected paths only; do not run the builder or compiler")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    if args.dpi <= 0:
        raise ValueError("--dpi 必须大于 0")
    executable, origin = find_tectonic(args.tectonic)
    env, cache_origin = compile_environment(args.cache_dir)
    svg_tool = find_poppler("pdftocairo") if args.svg else None
    png_tool = find_poppler("pdftoppm") if args.png else None
    settings = {
        "tectonic": str(executable), "tectonic_source": origin,
        "cache": env.get("TECTONIC_CACHE_DIR", "Tectonic default"), "cache_source": cache_origin,
        "pdftocairo": str(svg_tool) if svg_tool else None,
        "pdftoppm": str(png_tool) if png_tool else None,
    }
    print(json.dumps(settings, ensure_ascii=False, indent=2))
    if args.check_tools:
        return 0
    if env.get("TECTONIC_CACHE_DIR"):
        Path(env["TECTONIC_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    run([sys.executable, str(ROOT / "code/export_figure_data.py")], cwd=ROOT, env=env)
    run([sys.executable, str(ROOT / "code/build_latex_report.py")], cwd=ROOT, env=env)
    built = compile_tex(LATEX / "main.tex", executable, LATEX / "build", env)
    destination = REPORTS / "tokenizer_analysis_report.pdf"
    shutil.copy2(built, destination)
    outputs = [str(destination)]

    if not args.skip_figures:
        wrappers = sorted((LATEX / "figures").glob("*_standalone.tex"))
        figures = ROOT / "figures"
        figures.mkdir(parents=True, exist_ok=True)
        if not wrappers:
            print("未找到 *_standalone.tex；主报告已生成，没有独立图需要编译。")
        for wrapper in wrappers:
            name = wrapper.stem.removesuffix("_standalone")
            pdf = compile_tex(wrapper, executable, LATEX / "build/figures", env)
            exported = figures / (name + ".pdf")
            shutil.copy2(pdf, exported)
            outputs.append(str(exported))
            if args.svg and svg_tool:
                svg = figures / (name + ".svg")
                run([str(svg_tool), "-svg", "-f", "1", "-l", "1", str(exported), str(svg)], cwd=ROOT, env=env)
                outputs.append(str(svg))
            if args.png and png_tool:
                prefix = figures / name
                run([str(png_tool), "-png", "-r", str(args.dpi), "-f", "1", "-singlefile", str(exported), str(prefix)], cwd=ROOT, env=env)
                outputs.append(str(prefix.with_suffix(".png")))
        if args.svg and not svg_tool:
            print("未找到 pdftocairo，跳过 SVG 导出；PDF 不受影响。")
        if args.png and not png_tool:
            print("未找到 pdftoppm，跳过 PNG 导出；PDF 不受影响。")
    print("已生成：\n" + "\n".join(outputs))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"构建失败：{error}", file=sys.stderr)
        raise SystemExit(1)
