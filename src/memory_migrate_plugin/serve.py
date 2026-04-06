from __future__ import annotations

import cgi
import json
import tempfile
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template
from typing import Any
from urllib.parse import parse_qs, urlparse

from memory_migrate_plugin.bundle import run_bundle
from memory_migrate_plugin.core import export_canonical_json, normalize
from memory_migrate_plugin.doctor import build_doctor_report
from memory_migrate_plugin.recommend import recommend_migration_targets
from memory_migrate_plugin.profiles import list_profiles
from memory_migrate_plugin.registry import build_registry, detect_format
from memory_migrate_plugin.report import build_package_report
from memory_migrate_plugin.schema import build_canonical_package_schema
from memory_migrate_plugin.suggest import build_package_suggestions
from memory_migrate_plugin.validate import validate_package_file

UI_WORKSPACE_ROOT = Path(tempfile.gettempdir()) / "agent-memory-bridge-ui"
DOWNLOAD_REGISTRY: dict[str, Path] = {}
ACTION_HISTORY: list[dict[str, Any]] = []
MAX_ACTION_HISTORY = 12
MAX_RECENT_DOWNLOADS = 10

HTML_PAGE = Template("""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent Memory Bridge</title>
  <style>
    :root {
      --bg: #f5efe4;
      --panel: #fffaf2;
      --panel-strong: #fffdf8;
      --ink: #1e1d1a;
      --muted: #6f675c;
      --line: #d8c9b1;
      --accent: #0f766e;
      --accent-2: #b45309;
      --shadow: 0 20px 50px rgba(38, 31, 21, 0.10);
      --radius: 18px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(180, 83, 9, 0.16), transparent 30%),
        radial-gradient(circle at top right, rgba(15, 118, 110, 0.15), transparent 28%),
        linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
    }
    .shell {
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.25fr 0.75fr;
      gap: 20px;
      margin-bottom: 24px;
    }
    .card {
      background: rgba(255, 250, 242, 0.92);
      border: 1px solid rgba(216, 201, 177, 0.9);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
    }
    .hero-copy { padding: 28px; }
    .hero-copy h1 {
      margin: 0 0 10px;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
    }
    .eyebrow {
      color: var(--accent-2);
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 0.76rem;
      margin-bottom: 10px;
      font-weight: 700;
    }
    .hero-copy p {
      color: var(--muted);
      font-size: 1.02rem;
      line-height: 1.7;
      max-width: 58ch;
    }
    .hero-stats {
      padding: 24px;
      display: grid;
      gap: 12px;
      align-content: start;
    }
    .stat {
      padding: 14px 16px;
      border-radius: 14px;
      background: var(--panel-strong);
      border: 1px solid var(--line);
    }
    .stat strong {
      display: block;
      font-size: 1.2rem;
      margin-bottom: 4px;
    }
    .layout {
      display: grid;
      grid-template-columns: 420px 1fr;
      gap: 20px;
    }
    form { padding: 24px; }
    label {
      display: block;
      margin: 0 0 6px;
      font-weight: 700;
      font-size: 0.92rem;
    }
    input, select, textarea, button {
      width: 100%;
      font: inherit;
      border-radius: 12px;
      border: 1px solid var(--line);
      padding: 12px 14px;
      background: #fffdf9;
      color: var(--ink);
    }
    textarea { min-height: 120px; resize: vertical; }
    .grid { display: grid; gap: 14px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .stack { display: grid; gap: 16px; }
    button {
      background: linear-gradient(135deg, var(--accent) 0%, #155e75 100%);
      color: white;
      border: none;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease;
      box-shadow: 0 14px 28px rgba(15, 118, 110, 0.24);
    }
    button:hover { transform: translateY(-1px); }
    .secondary {
      background: linear-gradient(135deg, #9a3412 0%, #b45309 100%);
      box-shadow: 0 14px 28px rgba(180, 83, 9, 0.24);
    }
    .output {
      padding: 24px;
      min-height: 700px;
      display: grid;
      gap: 16px;
    }
    .banner {
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fffcf7;
      color: var(--muted);
    }
    .banner.ok { border-color: rgba(15, 118, 110, 0.35); background: rgba(15, 118, 110, 0.08); color: #0f4d48; }
    .banner.error { border-color: rgba(185, 28, 28, 0.3); background: rgba(185, 28, 28, 0.08); color: #7f1d1d; }
    .downloads {
      display: grid;
      gap: 10px;
      padding: 14px;
      border-radius: 14px;
      background: #fffdf8;
      border: 1px solid var(--line);
    }
    .panel-title {
      font-weight: 700;
      letter-spacing: 0.02em;
    }
    .history {
      display: grid;
      gap: 10px;
      padding: 14px;
      border-radius: 14px;
      background: #fffdf8;
      border: 1px solid var(--line);
    }
    .history-item {
      border-top: 1px solid rgba(216, 201, 177, 0.7);
      padding-top: 10px;
      display: grid;
      gap: 4px;
      color: var(--muted);
      font-size: 0.92rem;
    }
    .history-item:first-of-type {
      border-top: none;
      padding-top: 0;
    }
    .history-item strong { color: var(--ink); }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
    }
    .summary-card {
      padding: 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: #fffdf8;
      display: grid;
      gap: 6px;
    }
    .summary-card.ok {
      border-color: rgba(15, 118, 110, 0.28);
      background: rgba(15, 118, 110, 0.07);
    }
    .summary-card.warn {
      border-color: rgba(180, 83, 9, 0.32);
      background: rgba(180, 83, 9, 0.08);
    }
    .summary-card.error {
      border-color: rgba(185, 28, 28, 0.28);
      background: rgba(185, 28, 28, 0.08);
    }
    .summary-label {
      color: var(--muted);
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .summary-value {
      color: var(--ink);
      font-size: 1.1rem;
      font-weight: 700;
      line-height: 1.2;
      word-break: break-word;
    }
    .downloads a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }
    .downloads a:hover { text-decoration: underline; }
    .comparison {
      display: grid;
      gap: 12px;
      padding: 14px;
      border-radius: 14px;
      background: #fffdf8;
      border: 1px solid var(--line);
    }
    .comparison-item {
      display: grid;
      gap: 6px;
      padding-top: 10px;
      border-top: 1px solid rgba(216, 201, 177, 0.7);
      color: var(--muted);
      font-size: 0.92rem;
    }
    .comparison-item:first-of-type {
      border-top: none;
      padding-top: 0;
    }
    .comparison-item strong { color: var(--ink); }
    .comparison-chip {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      background: rgba(15, 118, 110, 0.10);
      color: #0f4d48;
      margin-right: 6px;
      margin-bottom: 6px;
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      background: #201a14;
      color: #f8f1e6;
      padding: 18px;
      border-radius: 16px;
      overflow: auto;
      line-height: 1.55;
      font-family: Consolas, "Courier New", monospace;
    }
    .tips {
      display: grid;
      gap: 10px;
      color: var(--muted);
      font-size: 0.95rem;
    }
    .tips code { color: var(--ink); }
    @media (max-width: 980px) {
      .hero, .layout, .row { grid-template-columns: 1fr; }
      .output { min-height: auto; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="card hero-copy">
        <div class="eyebrow">Agent Memory Bridge</div>
        <h1>Move memory between agents without rewriting context.</h1>
        <p>Use this local console to inspect, normalize, validate, and bundle memory across agent systems. Everything runs on your machine through the same deterministic pipeline as the CLI.</p>
      </div>
      <div class="card hero-stats">
        <div class="stat"><strong>$adapter_count</strong> registered adapters</div>
        <div class="stat"><strong>$profile_count</strong> export profiles</div>
        <div class="stat"><strong>Local only</strong> no external service required</div>
      </div>
    </section>
    <section class="layout">
      <div class="stack">
        <div class="card">
          <form method="post" action="/upload" enctype="multipart/form-data" class="grid">
            <div>
              <label for="upload_zip">Upload zip package</label>
              <input id="upload_zip" name="upload_zip" type="file" accept=".zip" required>
            </div>
            <button type="submit" class="secondary">Upload and Extract</button>
          </form>
        </div>
        <div class="card">
          <form method="post" action="/run" class="grid">
            <div>
              <label for="action">Action</label>
              <select id="action" name="action">$action_options</select>
            </div>
            <div>
              <label for="input_path">Input path</label>
              <input id="input_path" name="input_path" value="$input_path" placeholder="D:\path	o\memory" required>
            </div>
            <div class="row">
              <div>
                <label for="source_format">Source format</label>
                <select id="source_format" name="source_format">$source_options</select>
              </div>
              <div>
                <label for="target_format">Target format</label>
                <select id="target_format" name="target_format">$target_options</select>
              </div>
            </div>
            <div class="row">
              <div>
                <label for="profile">Profile</label>
                <select id="profile" name="profile">$profile_options</select>
              </div>
              <div>
                <label for="output_path">Output path</label>
                <input id="output_path" name="output_path" value="$output_path" placeholder="Optional file or output directory">
              </div>
            </div>
            <div>
              <label for="notes">Notes</label>
              <textarea id="notes" name="notes" placeholder="Optional operator notes shown only in the UI">$notes</textarea>
            </div>
            <button type="submit">Run Workflow</button>
          </form>
        </div>
      </div>
      <div class="card output">
        <div class="banner $status_class">$message</div>
        $summary_cards
        $comparison_panel
        $download_links
        $history_panel
        <pre>$output</pre>
        <div class="tips">
          <div>Suggested first try: <code>detect</code> or <code>inspect</code> before <code>bundle</code>.</div>
          <div>You can upload a zip, then reuse the extracted path in the workflow form.</div>
          <div><code>bundle</code> now generates downloadable artifacts directly from the UI.</div>
        </div>
      </div>
    </section>
  </div>
</body>
</html>
""")


def _html_escape(value: Any) -> str:
    text = str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _option_list(options: list[str], selected: str | None, placeholder: str) -> str:
    rows = [f'<option value="">{_html_escape(placeholder)}</option>']
    for option in options:
        is_selected = " selected" if option == (selected or "") else ""
        rows.append(f'<option value="{_html_escape(option)}"{is_selected}>{_html_escape(option)}</option>')
    return "".join(rows)


def _safe_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in name.strip())
    return cleaned.strip(".-") or "upload.zip"


def _resolve_ui_path(path: Path) -> Path:
    return path.resolve()


def extract_zip_to_workspace(zip_path: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            member_path = destination_dir / member.filename
            resolved_path = member_path.resolve()
            if destination_dir.resolve() not in resolved_path.parents and resolved_path != destination_dir.resolve():
                raise ValueError(f"Unsafe zip entry: {member.filename}")
        archive.extractall(destination_dir)

    children = [item for item in destination_dir.iterdir() if item.name != zip_path.name]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return destination_dir


def save_uploaded_zip(filename: str, payload: bytes, workspace_root: Path = UI_WORKSPACE_ROOT) -> dict[str, str]:
    workspace_id = uuid.uuid4().hex[:10]
    session_root = workspace_root / workspace_id
    session_root.mkdir(parents=True, exist_ok=True)
    zip_name = _safe_name(filename or "upload.zip")
    zip_path = session_root / zip_name
    zip_path.write_bytes(payload)
    extract_root = session_root / "extracted"
    input_root = extract_zip_to_workspace(zip_path, extract_root)
    return {
        "workspace_id": workspace_id,
        "zip_path": str(zip_path),
        "input_path": str(input_root),
    }


def register_download(path: Path) -> dict[str, str]:
    resolved = _resolve_ui_path(path)
    token = uuid.uuid4().hex
    DOWNLOAD_REGISTRY[token] = resolved
    return {
        "token": token,
        "path": str(resolved),
        "filename": resolved.name,
        "url": f"/download?token={token}",
    }


def _recent_downloads() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for token, path in list(DOWNLOAD_REGISTRY.items())[-MAX_RECENT_DOWNLOADS:][::-1]:
        if path.exists() and path.is_file():
            items.append({
                "token": token,
                "path": str(path),
                "filename": path.name,
                "url": f"/download?token={token}",
            })
    return items


def record_action_history(
    action: str,
    ok: bool,
    input_path: str,
    source_format: str | None,
    target_format: str | None,
    output_path: str | None,
    message: str,
    downloads: list[dict[str, str]] | None = None,
) -> None:
    entry = {
        "id": uuid.uuid4().hex[:8],
        "action": action,
        "ok": ok,
        "input_path": input_path,
        "source_format": source_format or "auto",
        "target_format": target_format or "-",
        "output_path": output_path or "-",
        "message": message,
        "downloads": list(downloads or []),
    }
    ACTION_HISTORY.append(entry)
    if len(ACTION_HISTORY) > MAX_ACTION_HISTORY:
        del ACTION_HISTORY[:-MAX_ACTION_HISTORY]


def render_history_panel(history: list[dict[str, Any]] | None = None, recent_downloads: list[dict[str, str]] | None = None) -> str:
    history = history if history is not None else ACTION_HISTORY
    recent_downloads = recent_downloads if recent_downloads is not None else _recent_downloads()
    sections = ['<div class="history"><div class="panel-title">Recent Activity</div>']
    if not history:
        sections.append('<div class="history-item"><strong>No runs yet.</strong><div>Run a workflow to populate local session history.</div></div>')
    else:
        for item in history[::-1]:
            state = "ok" if item["ok"] else "error"
            sections.append(
                f'<div class="history-item"><strong>{_html_escape(item["action"])} ? {state}</strong>'
                f'<div>{_html_escape(item["message"])}</div>'
                f'<div>input: {_html_escape(item["input_path"])}</div>'
                f'<div>target: {_html_escape(item["target_format"])} ? output: {_html_escape(item["output_path"])}</div></div>'
            )
    if recent_downloads:
        sections.append('<div class="panel-title">Recent Downloads</div>')
        for item in recent_downloads:
            sections.append(
                f'<div class="history-item"><a href="{_html_escape(item["url"])}">{_html_escape(item["filename"])}</a>'
                f'<div>{_html_escape(item["path"])}</div></div>'
            )
    sections.append('</div>')
    return ''.join(sections)


def summarize_action_result(action: str, result: dict[str, Any] | None) -> list[dict[str, str]]:
    if not result:
        return []
    payload = result.get("result", {})
    cards: list[dict[str, str]] = []

    def add(label: str, value: Any, tone: str = "") -> None:
        if value is None:
            return
        rendered = str(value)
        if not rendered.strip():
            return
        cards.append({"label": label, "value": rendered, "tone": tone})

    if action == "detect":
        matches = payload.get("matches", [])
        add("Matches", len(matches), "ok")
        if matches:
            add("Top Format", matches[0][0], "ok")
            add("Confidence", f"{matches[0][1]}%")
        return cards

    if action == "inspect":
        add("Package", payload.get("package_id"), "ok")
        add("Entries", payload.get("entry_count"), "ok")
        add("Kinds", len(payload.get("kinds", [])))
        return cards

    if action == "normalize":
        add("Package", payload.get("package_id"), "ok")
        add("Entries", payload.get("entry_count"), "ok")
        add("Output", Path(payload.get("output_path", "")).name if payload.get("output_path") else None)
        return cards

    if action == "validate":
        summary = payload.get("summary", {})
        is_ok = bool(payload.get("ok"))
        add("Status", "Valid" if is_ok else "Invalid", "ok" if is_ok else "error")
        add("Errors", summary.get("error_count", 0), "error" if summary.get("error_count", 0) else "ok")
        add("Warnings", summary.get("warning_count", 0), "warn" if summary.get("warning_count", 0) else "ok")
        add("Entries", summary.get("entry_count", 0))
        return cards

    if action == "report":
        audit = payload.get("audit", {})
        add("Package", payload.get("package_id"), "ok")
        add("Entries", payload.get("entry_count", 0), "ok")
        add("Issues", audit.get("issues_found", 0), "warn" if audit.get("issues_found", 0) else "ok")
        add("Formats", len(payload.get("source_formats", [])))
        return cards

    if action == "doctor":
        summary = payload.get("doctor_summary", {})
        add("Health", summary.get("health_score", 0), "ok" if summary.get("health_score", 0) >= 80 else "warn")
        add("Issues", summary.get("issue_count", 0), "warn" if summary.get("issue_count", 0) else "ok")
        add("Suggestions", summary.get("suggestion_count", 0), "warn" if summary.get("suggestion_count", 0) else "ok")
        add("Repairable", summary.get("repairable_entry_count", 0))
        return cards

    if action == "suggest":
        add("Suggestions", payload.get("suggestion_count", 0), "warn" if payload.get("suggestion_count", 0) else "ok")
        if payload.get("suggestions"):
            add("Top Severity", payload["suggestions"][0].get("severity", "unknown"))
        return cards

    if action == "bundle":
        add("Entries", payload.get("export_entry_count") or payload.get("entry_count"), "ok")
        add("Target", payload.get("output", {}).get("target_format") if isinstance(payload.get("output"), dict) else payload.get("target_format"), "ok")
        doctor_summary = payload.get("doctor_summary", {})
        add("Health", doctor_summary.get("health_score"), "warn" if doctor_summary.get("health_score", 100) < 80 else "ok")
        add("Downloads", len(result.get("downloads", [])), "ok")
        return cards

    if action == "recommend":
        source = payload.get("source", {})
        recommendations = payload.get("recommendations", [])
        add("Detected", source.get("detected_format"), "ok")
        add("Candidates", len(source.get("candidate_formats", [])))
        add("Recommended", recommendations[0].get("target_format") if recommendations else None, "ok")
        add("Profile", recommendations[0].get("recommended_profile") if recommendations else None)
        return cards

    if action == "schema":
        add("Schema", payload.get("title"), "ok")
        add("Version", payload.get("properties", {}).get("schema_version", {}).get("default", "1.0"))
        add("Entry Fields", len(payload.get("$defs", {}).get("memoryEntry", {}).get("required", [])))
        return cards

    return cards


def render_recommendation_comparison(result: dict[str, Any] | None) -> str:
    if not result or result.get("action") != "recommend":
        return ""
    comparison = result.get("result", {}).get("comparison", [])
    if not comparison:
        return ""
    rows = ['<div class="comparison"><div class="panel-title">Recommendation Comparison</div>']
    for item in comparison:
        rows.append(
            f'<div class="comparison-item"><strong>{_html_escape(item["target_format"])} ? {_html_escape(item["recommended_profile"])} ? score {item["score"]}</strong>'
            f'<div>{_html_escape(item["top_reason"])}</div>'
        )
        strengths = item.get("strengths", [])
        if strengths:
            chips = ''.join(f'<span class="comparison-chip">{_html_escape(strength)}</span>' for strength in strengths)
            rows.append(f'<div>{chips}</div>')
        why_not_top = item.get("why_not_top", [])
        if why_not_top:
            rows.append(f'<div>Why not top: {_html_escape(why_not_top[0])}</div>')
        rows.append('</div>')
    rows.append('</div>')
    return ''.join(rows)


def render_summary_cards(cards: list[dict[str, str]] | None) -> str:
    if not cards:
        return ""
    rows = ['<div class="summary-grid">']
    for item in cards:
        tone = str(item.get("tone", "")).strip()
        tone_class = f" {tone}" if tone else ""
        rows.append(
            f'<div class="summary-card{tone_class}">'
            f'<div class="summary-label">{_html_escape(item["label"])}</div>'
            f'<div class="summary-value">{_html_escape(item["value"])}</div>'
            '</div>'
        )
    rows.append('</div>')
    return ''.join(rows)


def render_download_links(downloads: list[dict[str, str]] | None) -> str:
    if not downloads:
        return ""
    rows = ['<div class="downloads"><strong>Downloads</strong>']
    for item in downloads:
        rows.append(
            f'<a href="{_html_escape(item["url"])}">{_html_escape(item["filename"])}</a><div>{_html_escape(item["path"])}</div>'
        )
    rows.append("</div>")
    return "".join(rows)


def execute_web_action(
    action: str,
    input_path: str,
    source_format: str | None = None,
    target_format: str | None = None,
    output_path: str | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    source = Path(input_path)
    source_format = source_format or None
    target_format = target_format or None
    output_path = output_path or None
    profile = profile or None

    if action == "detect":
        return {"ok": True, "action": action, "result": {"matches": detect_format(source)}, "downloads": []}
    if action == "inspect":
        package = normalize(source_format, source)
        return {
            "ok": True,
            "action": action,
            "result": {
                "package_id": package.package_id,
                "entry_count": len(package.entries),
                "source_formats": package.source_formats,
                "kinds": sorted({entry.kind for entry in package.entries}),
            },
            "downloads": [],
        }
    if action == "normalize":
        if not output_path:
            raise ValueError("normalize requires an output path")
        package = normalize(source_format, source)
        output_file = Path(output_path)
        export_canonical_json(package, output_file)
        return {
            "ok": True,
            "action": action,
            "result": {"output_path": str(output_file), "entry_count": len(package.entries), "package_id": package.package_id},
            "downloads": [register_download(output_file)],
        }
    if action == "validate":
        report = validate_package_file(source, Path(output_path) if output_path else None)
        downloads = [register_download(Path(output_path))] if output_path else []
        return {"ok": True, "action": action, "result": report, "downloads": downloads}
    if action == "report":
        package = normalize(source_format, source)
        return {"ok": True, "action": action, "result": build_package_report(package), "downloads": []}
    if action == "doctor":
        package = normalize(source_format, source)
        return {"ok": True, "action": action, "result": build_doctor_report(package), "downloads": []}
    if action == "suggest":
        package = normalize(source_format, source)
        return {"ok": True, "action": action, "result": build_package_suggestions(package), "downloads": []}
    if action == "recommend":
        return {"ok": True, "action": action, "result": recommend_migration_targets(source, source_format), "downloads": []}
    if action == "bundle":
        if not target_format:
            raise ValueError("bundle requires a target format")
        if not output_path:
            raise ValueError("bundle requires an output directory")
        output_dir = Path(output_path)
        zip_output = output_dir.parent / f"{output_dir.name}.zip"
        summary = run_bundle(source, source_format, target_format, output_dir, profile=profile, apply_repair=True, zip_output=zip_output)
        downloads = [register_download(zip_output), register_download(output_dir / "bundle-summary.json")]
        return {"ok": True, "action": action, "result": summary, "downloads": downloads}
    if action == "schema":
        return {"ok": True, "action": action, "result": build_canonical_package_schema(), "downloads": []}
    raise ValueError(f"Unsupported action: {action}")


class MemoryBridgeRequestHandler(BaseHTTPRequestHandler):
    server_version = "AgentMemoryBridge/0.25"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            query = parse_qs(parsed.query)
            self._send_html(render_page(input_path=(query.get("input_path") or [""])[0]))
            return
        if parsed.path == "/download":
            token = (parse_qs(parsed.query).get("token") or [""])[0]
            self._send_download(token)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/run":
            self._handle_run()
            return
        if parsed.path == "/upload":
            self._handle_upload()
            return
        self.send_error(404)

    def _handle_run(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length).decode("utf-8")
        form = {key: values[0] for key, values in parse_qs(payload, keep_blank_values=True).items()}
        action = form.get("action", "detect")
        input_path = form.get("input_path", "")
        source_format = form.get("source_format") or None
        target_format = form.get("target_format") or None
        output_path = form.get("output_path") or None
        profile = form.get("profile") or None
        notes = form.get("notes", "")
        downloads: list[dict[str, str]] = []
        try:
            result = execute_web_action(action, input_path, source_format, target_format, output_path, profile)
            message = f"Action '{action}' completed successfully."
            status_class = "ok"
            downloads = result.get("downloads", [])
            summary_cards = summarize_action_result(action, result)
            comparison_panel = render_recommendation_comparison(result)
            output = json.dumps(result, indent=2, ensure_ascii=False)
            record_action_history(action, True, input_path, source_format, target_format, output_path, message, downloads)
        except Exception as exc:
            message = f"Action '{action}' failed: {exc}"
            status_class = "error"
            summary_cards = []
            comparison_panel = ""
            output = json.dumps({"ok": False, "action": action, "error": str(exc)}, indent=2, ensure_ascii=False)
            record_action_history(action, False, input_path, source_format, target_format, output_path, message, [])
        self._send_html(
            render_page(
                action=action,
                input_path=input_path,
                source_format=source_format,
                target_format=target_format,
                output_path=output_path or "",
                profile=profile,
                notes=notes,
                message=message,
                status_class=status_class,
                output=output,
                downloads=downloads,
                summary_cards=summary_cards,
                comparison_panel=comparison_panel,
            )
        )

    def _handle_upload(self) -> None:
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )
        upload = form["upload_zip"] if "upload_zip" in form else None
        if upload is None or not getattr(upload, "file", None):
            self._send_html(render_page(message="Upload failed: missing zip file.", status_class="error"))
            return
        try:
            payload = upload.file.read()
            saved = save_uploaded_zip(getattr(upload, "filename", "upload.zip"), payload)
            message = f"Uploaded and extracted zip into {saved['input_path']}"
            record_action_history("upload", True, saved["input_path"], None, None, saved["zip_path"], message, [])
            self._send_html(
                render_page(
                    input_path=saved["input_path"],
                    message=message,
                    status_class="ok",
                    output=json.dumps(saved, indent=2, ensure_ascii=False),
                    summary_cards=[
                        {"label": "Upload", "value": Path(saved["zip_path"]).name, "tone": "ok"},
                        {"label": "Workspace", "value": saved["workspace_id"]},
                        {"label": "Extracted", "value": Path(saved["input_path"]).name or saved["input_path"]},
                    ],
                )
            )
        except Exception as exc:
            message = f"Upload failed: {exc}"
            record_action_history("upload", False, "", None, None, None, message, [])
            self._send_html(render_page(message=message, status_class="error"))

    def _send_download(self, token: str) -> None:
        path = DOWNLOAD_REGISTRY.get(token)
        if path is None or not path.exists() or not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def render_page(
    action: str = "detect",
    input_path: str = "",
    source_format: str | None = None,
    target_format: str | None = None,
    output_path: str = "",
    profile: str | None = None,
    notes: str = "",
    message: str = "Local dashboard ready. Choose an action and run a workflow.",
    status_class: str = "",
    output: str = '{\n  "status": "idle"\n}',
    downloads: list[dict[str, str]] | None = None,
    history: list[dict[str, Any]] | None = None,
    summary_cards: list[dict[str, str]] | None = None,
    comparison_panel: str = "",
) -> str:
    adapters = sorted(build_registry())
    profiles = sorted(list_profiles())
    actions = ["detect", "inspect", "normalize", "validate", "report", "doctor", "suggest", "recommend", "bundle", "schema"]
    return HTML_PAGE.substitute(
        adapter_count=len(adapters),
        profile_count=len(profiles),
        action_options=_option_list(actions, action, "Choose an action"),
        source_options=_option_list(adapters, source_format, "Auto detect"),
        target_options=_option_list(adapters, target_format, "No target"),
        profile_options=_option_list(profiles, profile, "No profile"),
        input_path=_html_escape(input_path),
        output_path=_html_escape(output_path),
        notes=_html_escape(notes),
        message=_html_escape(message),
        status_class=_html_escape(status_class),
        output=_html_escape(output),
        summary_cards=render_summary_cards(summary_cards),
        comparison_panel=comparison_panel,
        download_links=render_download_links(downloads),
        history_panel=render_history_panel(history, _recent_downloads()),
    )


def serve_web_ui(host: str = "127.0.0.1", port: int = 8765) -> None:
    UI_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), MemoryBridgeRequestHandler)
    print(f"Agent Memory Bridge UI listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down Agent Memory Bridge UI")
    finally:
        server.server_close()
