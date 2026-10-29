#!/usr/bin/env python3
"""Verify documentation structure, code-contract anchors, visualizations, glossary rules, and ASD-STE100 prose.

Checks performed:
1. Index hygiene: Every existing directory under --docs-dir contains an INDEX.md, and every sibling .md and .html file is linked.
2. Link integrity: Every relative Markdown link (to .md, .html, or assets) resolves to an existing file on disk.
3. Code-contract consistency (for .md frontmatter and .html `<!-- sane-docs-contract ... -->` headers):
   - `code_paths` exist under --repo-root.
   - `symbols` appear in the referenced `code_paths`.
   - `sync_commit` is checked against `git log` for drift on `code_paths`.
4. Visualization checks:
   - Mermaid blocks (` ```mermaid `) are checked for empty bodies, banned `_Avoid_` terms, and excessive arrow density (> 20 arrows, recommending an interactive `.html` visualization).
   - Standalone `.html` visualizations are checked for self-containment (no external `http://` or `https://` `<script src>` or `<link href>` dependencies) and contract headers.
5. Glossary enforcement (`GLOSSARY.md` at repo root or under `--docs-dir`):
   - Parses `GLOSSARY.md` entries for tight definitions (<= 2 sentences), banned generic terms, and `_Avoid_` lists.
   - Verifies that `GLOSSARY.md` is devoid of implementation details (no fenced code blocks, source file paths, or code anchors).
   - Scans all docs and diagrams for occurrences of banned `_Avoid_` terms.
6. ASD-STE100 prose checks:
   - Flags unapproved words (`utilize`, `facilitate`, `leverage`, `simply`, `easily`, `and/or`, etc.).
   - Flags sentences exceeding the word limit (default: 25 words).

Exit codes:
  0 - All checks passed (warnings permitted unless --strict is set).
  1 - One or more contract errors (or warnings under --strict) were found.
  2 - Invalid CLI arguments or neither --docs-dir nor GLOSSARY.md exists.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

UNAPPROVED_WORDS: Dict[str, str] = {
    "utilize": "use",
    "utilizes": "uses",
    "utilized": "used",
    "utilizing": "using",
    "leverage": "use",
    "leverages": "uses",
    "leveraged": "used",
    "leveraging": "using",
    "facilitate": "help (or state exact mechanism)",
    "facilitates": "helps (or state exact mechanism)",
    "facilitated": "helped",
    "facilitating": "helping",
    "prior to": "before",
    "in order to": "to",
    "due to the fact that": "because",
    "in the event that": "if",
    "subsequently": "then / after",
    "and/or": "A, B, or both",
    "simply": "(delete filler adverb)",
    "easily": "(delete filler adverb)",
    "seamless": "(state exact behavior instead)",
    "seamlessly": "(state exact behavior instead)",
}

GENERIC_PROGRAMMING_TERMS = {
    "timeout",
    "timeouts",
    "error",
    "errors",
    "exception",
    "exceptions",
    "callback",
    "boolean",
    "string",
    "integer",
    "array",
    "dictionary",
    "hashmap",
    "mutex",
    "thread",
    "process",
    "utility",
    "helper",
}

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
HTML_CONTRACT_RE = re.compile(r"<!--\s*sane-docs-contract\s*\n(.*?)-->", re.DOTALL)
MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCED_BLOCK_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
MERMAID_ARROW_RE = re.compile(r"(-->|-\.->|==>|-->>|->>|--x|--\)|<-->)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]+`")
EXTERNAL_ASSET_RE = re.compile(
    r"<(?:script|link)\b[^>]*(?:src|href)=['\"]https?://[^'\"]+['\"][^>]*>",
    re.IGNORECASE,
)
GLOSSARY_IMPL_PATH_RE = re.compile(
    r"(?:\b(?:src|lib|pkg|cmd|internal|app)/[A-Za-z0-9_./-]+|\b[A-Za-z0-9_-]+\.(?:py|ts|tsx|js|jsx|rs|go|java|cpp|c|h|sql|sh)\b)"
)


@dataclass
class Finding:
    severity: str  # "error" | "warning"
    rule: str
    file: str
    line: int
    message: str


def _parse_yaml_like_block(raw: str) -> Dict[str, object]:
    data: Dict[str, object] = {}
    current_list_key: Optional[str] = None
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and current_list_key:
            item = line[2:].strip().strip("'\"")
            existing = data.setdefault(current_list_key, [])
            if isinstance(existing, list):
                existing.append(item)
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if not val:
                data[key] = []
                current_list_key = key
            else:
                data[key] = val
                current_list_key = None
    return data


def parse_simple_frontmatter(text: str) -> Optional[Dict[str, object]]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    return _parse_yaml_like_block(match.group(1))


def parse_html_contract(text: str) -> Optional[Dict[str, object]]:
    match = HTML_CONTRACT_RE.search(text)
    if not match:
        return None
    return _parse_yaml_like_block(match.group(1))


def strip_non_prose(text: str) -> str:
    text = FRONTMATTER_RE.sub("", text)
    text = HTML_COMMENT_RE.sub("", text)
    text = FENCED_BLOCK_RE.sub("", text)
    return text


def check_index_coverage(docs_dir: Path, rel_base: Path) -> List[Finding]:
    findings: List[Finding] = []
    if not docs_dir.exists():
        return findings

    for directory in sorted([docs_dir, *[p for p in docs_dir.rglob("*") if p.is_dir()]]):
        doc_files = sorted([*directory.glob("*.md"), *directory.glob("*.html")])
        subdirs = sorted([d for d in directory.iterdir() if d.is_dir() and not d.name.startswith(".")])
        if not doc_files and not subdirs:
            continue

        # Allow a single standalone GLOSSARY.md before other docs exist (lazy creation).
        if directory == docs_dir and len(doc_files) == 1 and doc_files[0].name == "GLOSSARY.md" and not subdirs:
            continue

        index_file = directory / "INDEX.md"
        rel_dir = str(directory.relative_to(rel_base))
        if not index_file.exists():
            findings.append(
                Finding(
                    severity="error",
                    rule="index-missing",
                    file=rel_dir,
                    line=1,
                    message=f"Directory '{rel_dir}' is missing an INDEX.md routing file.",
                )
            )
            continue

        index_text = index_file.read_text(encoding="utf-8")
        rel_index = str(index_file.relative_to(rel_base))
        for sibling in doc_files:
            if sibling.name == "INDEX.md":
                continue
            if sibling.name not in index_text:
                findings.append(
                    Finding(
                        severity="error",
                        rule="index-unlinked-file",
                        file=rel_index,
                        line=1,
                        message=f"Sibling file '{sibling.name}' is not referenced in '{rel_index}'.",
                    )
                )
    return findings


def check_relative_links(md_file: Path, text: str, rel_base: Path) -> List[Finding]:
    findings: List[Finding] = []
    rel_file = str(md_file.relative_to(rel_base))
    prose_without_fences = FENCED_BLOCK_RE.sub("", HTML_COMMENT_RE.sub("", text))

    for line_no, line in enumerate(prose_without_fences.splitlines(), start=1):
        line_without_code = INLINE_CODE_RE.sub("", line)
        for match in MD_LINK_RE.finditer(line_without_code):
            target = match.group(1).strip()
            if (
                not target
                or target.startswith(("http://", "https://", "mailto:", "#"))
                or "<" in target
                or ">" in target
            ):
                continue
            path_part = target.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            resolved = (md_file.parent / path_part).resolve()
            if not resolved.exists():
                findings.append(
                    Finding(
                        severity="error",
                        rule="broken-link",
                        file=rel_file,
                        line=line_no,
                        message=f"Broken relative link '{target}' (resolved to '{resolved}').",
                    )
                )
    return findings


def check_code_contracts(
    doc_file: Path,
    contract: Optional[Dict[str, object]],
    repo_root: Path,
    rel_base: Path,
) -> List[Finding]:
    findings: List[Finding] = []
    if not contract:
        return findings

    rel_file = str(doc_file.relative_to(rel_base))
    code_paths_raw = contract.get("code_paths")
    code_paths: List[Path] = []

    if isinstance(code_paths_raw, list):
        for cp in code_paths_raw:
            cp_str = str(cp)
            if "<" in cp_str or ">" in cp_str:
                continue
            candidate = (repo_root / cp_str).resolve()
            if not candidate.exists():
                findings.append(
                    Finding(
                        severity="error",
                        rule="contract-missing-path",
                        file=rel_file,
                        line=1,
                        message=f"Contract code_path '{cp_str}' does not exist under repo root.",
                    )
                )
            else:
                code_paths.append(candidate)

    symbols_raw = contract.get("symbols")
    if isinstance(symbols_raw, list) and code_paths:
        searchable_files: List[Path] = []
        for cp in code_paths:
            if cp.is_file():
                searchable_files.append(cp)
            elif cp.is_dir():
                searchable_files.extend([p for p in cp.rglob("*") if p.is_file() and not p.name.startswith(".")])

        combined_source = ""
        for src_file in searchable_files:
            try:
                combined_source += "\n" + src_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

        for sym in symbols_raw:
            sym_str = str(sym)
            if "<" in sym_str or ">" in sym_str:
                continue
            if sym_str and sym_str not in combined_source:
                findings.append(
                    Finding(
                        severity="error",
                        rule="contract-missing-symbol",
                        file=rel_file,
                        line=1,
                        message=f"Symbol '{sym_str}' in contract was not found in declared code_paths.",
                    )
                )

    sync_commit = str(contract.get("sync_commit", "")).strip()
    if sync_commit and "<" not in sync_commit and code_paths:
        git_dir = repo_root / ".git"
        if git_dir.exists():
            rel_code_paths = [str(cp.relative_to(repo_root.resolve())) for cp in code_paths]
            try:
                proc = subprocess.run(
                    ["git", "log", "--oneline", f"{sync_commit}..HEAD", "--", *rel_code_paths],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    commits = proc.stdout.strip().splitlines()
                    findings.append(
                        Finding(
                            severity="warning",
                            rule="contract-stale-sync-commit",
                            file=rel_file,
                            line=1,
                            message=(
                                f"Code in code_paths changed in {len(commits)} commit(s) since "
                                f"sync_commit '{sync_commit}'. Verify behavior and update sync_commit."
                            ),
                        )
                    )
            except OSError:
                pass

    return findings


def check_mermaid_blocks(
    md_file: Path,
    text: str,
    avoid_map: Dict[str, str],
    rel_base: Path,
) -> List[Finding]:
    findings: List[Finding] = []
    rel_file = str(md_file.relative_to(rel_base))

    for match in MERMAID_BLOCK_RE.finditer(text):
        body = match.group(1).strip()
        start_line = text[: match.start()].count("\n") + 1
        if not body:
            findings.append(
                Finding(
                    severity="error",
                    rule="mermaid-empty-block",
                    file=rel_file,
                    line=start_line,
                    message="Empty ```mermaid block.",
                )
            )
            continue

        arrows = MERMAID_ARROW_RE.findall(body)
        if len(arrows) > 20:
            findings.append(
                Finding(
                    severity="warning",
                    rule="mermaid-too-dense",
                    file=rel_file,
                    line=start_line,
                    message=(
                        f"Mermaid diagram has {len(arrows)} arrows (recommended <= 20). "
                        "Split by subsystem or move to an interactive HTML visualization."
                    ),
                )
            )

        for avoid_term, canonical in avoid_map.items():
            pattern = rf"\b{re.escape(avoid_term)}\b"
            if re.search(pattern, body, flags=re.IGNORECASE):
                findings.append(
                    Finding(
                        severity="error",
                        rule="glossary-avoid-term-in-mermaid",
                        file=rel_file,
                        line=start_line,
                        message=(
                            f"Mermaid diagram uses banned _Avoid_ term '{avoid_term}'; "
                            f"use canonical term '{canonical}'."
                        ),
                    )
                )

    return findings


def check_html_visualization(
    html_file: Path,
    text: str,
    avoid_map: Dict[str, str],
    repo_root: Path,
    rel_base: Path,
) -> List[Finding]:
    findings: List[Finding] = []
    rel_file = str(html_file.relative_to(rel_base))

    contract = parse_html_contract(text)
    if not contract:
        findings.append(
            Finding(
                severity="warning",
                rule="html-missing-contract",
                file=rel_file,
                line=1,
                message=(
                    "HTML visualization is missing a <!-- sane-docs-contract ... --> header "
                    "with sync_commit, code_paths, and symbols."
                ),
            )
        )
    else:
        findings.extend(check_code_contracts(html_file, contract, repo_root, rel_base))

    for ext_match in EXTERNAL_ASSET_RE.finditer(text):
        line_no = text[: ext_match.start()].count("\n") + 1
        findings.append(
            Finding(
                severity="error",
                rule="html-external-dependency",
                file=rel_file,
                line=line_no,
                message=(
                    "HTML visualization loads an external HTTP(S) script or stylesheet. "
                    "Visualizations must be single-file and self-contained."
                ),
            )
        )

    text_no_comments = HTML_COMMENT_RE.sub("", text)
    for avoid_term, canonical in avoid_map.items():
        pattern = rf"\b{re.escape(avoid_term)}\b"
        if re.search(pattern, text_no_comments, flags=re.IGNORECASE):
            findings.append(
                Finding(
                    severity="error",
                    rule="glossary-avoid-term-in-html",
                    file=rel_file,
                    line=1,
                    message=(
                        f"HTML visualization uses banned _Avoid_ term '{avoid_term}'; "
                        f"use canonical term '{canonical}'."
                    ),
                )
            )

    return findings


def parse_glossary_and_check(glossary_path: Path, rel_base: Path) -> Tuple[Dict[str, str], List[Finding]]:
    """Return mapping of {avoid_term_lower: canonical_term} and glossary findings."""
    avoid_map: Dict[str, str] = {}
    findings: List[Finding] = []
    if not glossary_path.exists():
        return avoid_map, findings

    rel_file = str(glossary_path.relative_to(rel_base))
    raw_text = glossary_path.read_text(encoding="utf-8")
    no_comments = HTML_COMMENT_RE.sub("", FRONTMATTER_RE.sub("", raw_text))

    if FENCED_BLOCK_RE.search(no_comments):
        findings.append(
            Finding(
                severity="error",
                rule="glossary-implementation-detail",
                file=rel_file,
                line=1,
                message=(
                    "GLOSSARY.md contains a fenced code block. "
                    "GLOSSARY.md must be totally devoid of implementation details."
                ),
            )
        )

    clean_text = strip_non_prose(raw_text)

    current_term: Optional[str] = None
    current_term_line: int = 1
    definition_lines: List[str] = []

    def flush_term() -> None:
        if not current_term or not definition_lines:
            return
        joined = " ".join(definition_lines).strip()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", joined) if s.strip()]
        if len(sentences) > 2:
            findings.append(
                Finding(
                    severity="warning",
                    rule="glossary-definition-too-long",
                    file=rel_file,
                    line=current_term_line,
                    message=(
                        f"Glossary term '{current_term}' has {len(sentences)} sentences "
                        f"(max 2 sentences allowed; define what it IS, not what it does)."
                    ),
                )
            )

    for line_no, raw_line in enumerate(clean_text.splitlines(), start=1):
        line = raw_line.strip()

        if re.search(r"code\s+anchor", line, flags=re.IGNORECASE) or GLOSSARY_IMPL_PATH_RE.search(line):
            findings.append(
                Finding(
                    severity="error",
                    rule="glossary-implementation-detail",
                    file=rel_file,
                    line=line_no,
                    message=(
                        "GLOSSARY.md references a file path or code anchor. "
                        "GLOSSARY.md must be totally devoid of implementation details."
                    ),
                )
            )

        heading_match = re.match(r"^###\s+\*{0,2}([^*#]+?)\*{0,2}\s*$", line)
        if heading_match:
            flush_term()
            current_term = heading_match.group(1).strip()
            current_term_line = line_no
            definition_lines = []
            if current_term.lower() in GENERIC_PROGRAMMING_TERMS and "<" not in current_term:
                findings.append(
                    Finding(
                        severity="error",
                        rule="glossary-generic-term",
                        file=rel_file,
                        line=line_no,
                        message=(
                            f"Glossary term '{current_term}' is a general programming concept. "
                            "Only include terms specific to this project's domain."
                        ),
                    )
                )
            continue

        if current_term:
            avoid_match = re.match(r"^-\s*[*_]*Avoid:?[*_]*:?[*_]*\s*(.+)$", line, re.IGNORECASE)
            if avoid_match:
                raw_avoids = avoid_match.group(1)
                for token in raw_avoids.split(","):
                    cleaned = token.strip().strip("`_*'\" ")
                    if cleaned and "<" not in cleaned and cleaned.lower() != "none":
                        avoid_map[cleaned.lower()] = current_term
            elif line.startswith("- ") or line.startswith("## "):
                if line.startswith("## "):
                    flush_term()
                    current_term = None
                    definition_lines = []
            elif line:
                definition_lines.append(line)

    flush_term()
    return avoid_map, findings


def check_ste100_and_glossary(
    md_file: Path,
    text: str,
    avoid_map: Dict[str, str],
    max_words: int,
    rel_base: Path,
    is_glossary: bool = False,
) -> List[Finding]:
    findings: List[Finding] = []
    rel_file = str(md_file.relative_to(rel_base))
    clean = strip_non_prose(text)

    for line_no, raw_line in enumerate(clean.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("#", "|", "```", "---", ">")):
            continue

        line_no_code = INLINE_CODE_RE.sub(" CODE_TOKEN ", stripped)
        line_no_links = MD_LINK_RE.sub(" LINK_TOKEN ", line_no_code)

        for bad_word, replacement in UNAPPROVED_WORDS.items():
            pattern = rf"\b{re.escape(bad_word)}\b"
            if re.search(pattern, line_no_links, flags=re.IGNORECASE):
                findings.append(
                    Finding(
                        severity="warning",
                        rule="ste100-unapproved-word",
                        file=rel_file,
                        line=line_no,
                        message=f"STE-100: Avoid '{bad_word}'; use '{replacement}'.",
                    )
                )

        if not is_glossary and avoid_map:
            for avoid_term, canonical in avoid_map.items():
                pattern = rf"\b{re.escape(avoid_term)}\b"
                if re.search(pattern, line_no_links, flags=re.IGNORECASE):
                    findings.append(
                        Finding(
                            severity="error",
                            rule="glossary-avoid-term-used",
                            file=rel_file,
                            line=line_no,
                            message=f"Term '{avoid_term}' is listed under _Avoid_ in GLOSSARY.md; use '{canonical}'.",
                        )
                    )

        bullet_cleaned = re.sub(r"^[-*+]\s+|\d+\.\s+", "", line_no_links)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", bullet_cleaned) if s.strip()]
        for sentence in sentences:
            words = [w for w in re.findall(r"[A-Za-z0-9_'-]+", sentence) if w]
            if len(words) > max_words:
                findings.append(
                    Finding(
                        severity="warning",
                        rule="ste100-sentence-length",
                        file=rel_file,
                        line=line_no,
                        message=(
                            f"STE-100: Sentence has {len(words)} words (limit: {max_words}). "
                            "Split into shorter sentences with one thought each."
                        ),
                    )
                )

    return findings


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify documentation structure, code contracts, visualizations, glossary rules, and ASD-STE100 compliance."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to the repository root (default: current directory).",
    )
    parser.add_argument(
        "--docs-dir",
        default="docs",
        help="Path to the documentation directory relative to --repo-root (default: docs).",
    )
    parser.add_argument(
        "--max-sentence-words",
        type=int,
        default=25,
        help="Maximum words allowed per descriptive sentence under ASD-STE100 (default: 25).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (exit code 1).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report to stdout.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    docs_dir = (repo_root / args.docs_dir).resolve()
    root_glossary = repo_root / "GLOSSARY.md"
    docs_glossary = docs_dir / "GLOSSARY.md"

    glossary_path = docs_glossary if docs_glossary.exists() else root_glossary

    if not docs_dir.exists() and not glossary_path.exists():
        sys.stderr.write(
            f"Error: Neither documentation directory '{docs_dir}' nor 'GLOSSARY.md' exists.\n"
            f"Usage: {sys.argv[0]} --repo-root <path> --docs-dir <docs_subdir>\n"
        )
        return 2

    findings: List[Finding] = []
    if docs_dir.exists():
        findings.extend(check_index_coverage(docs_dir, repo_root))

    avoid_map, glossary_findings = parse_glossary_and_check(glossary_path, repo_root)
    findings.extend(glossary_findings)

    md_targets: List[Path] = []
    if docs_dir.exists():
        md_targets.extend(sorted(docs_dir.rglob("*.md")))
    if root_glossary.exists() and root_glossary.resolve() not in [p.resolve() for p in md_targets]:
        md_targets.append(root_glossary)

    for md_file in md_targets:
        text = md_file.read_text(encoding="utf-8")
        is_gloss = glossary_path.exists() and md_file.resolve() == glossary_path.resolve()
        frontmatter = parse_simple_frontmatter(text)
        findings.extend(check_relative_links(md_file, text, repo_root))
        if not is_gloss:
            findings.extend(check_code_contracts(md_file, frontmatter, repo_root, repo_root))
            findings.extend(check_mermaid_blocks(md_file, text, avoid_map, repo_root))
        findings.extend(
            check_ste100_and_glossary(
                md_file=md_file,
                text=text,
                avoid_map=avoid_map,
                max_words=args.max_sentence_words,
                rel_base=repo_root,
                is_glossary=is_gloss,
            )
        )

    if docs_dir.exists():
        for html_file in sorted(docs_dir.rglob("*.html")):
            text = html_file.read_text(encoding="utf-8")
            findings.extend(check_html_visualization(html_file, text, avoid_map, repo_root, repo_root))

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    if args.json:
        payload = {
            "status": "failed" if (errors or (args.strict and warnings)) else "passed",
            "error_count": len(errors),
            "warning_count": len(warnings),
            "findings": [asdict(f) for f in findings],
        }
        print(json.dumps(payload, indent=2))
    else:
        for f in findings:
            prefix = "ERROR" if f.severity == "error" else "WARN "
            print(f"[{prefix}] {f.file}:{f.line} ({f.rule}): {f.message}")
        print(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s).")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
