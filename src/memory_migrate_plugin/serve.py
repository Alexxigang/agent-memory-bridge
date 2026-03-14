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
from memory_migrate_plugin.profiles import list_profiles
from memory_migrate_plugin.registry import build_registry, detect_format
from memory_migrate_plugin.report import build_package_report
from memory_migrate_plugin.schema import build_canonical_package_schema
from memory_migrate_plugin.suggest import build_package_suggestions
from memory_migrate_plugin.validate import validate_package_file

UI_WORKSPACE_ROOT = Path(tempfile.gettempdir()) / "agent-memory-bridge-ui"
DOWNLOAD_REGISTRY: dict[str, Path] = {}

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
    .downloads a {
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }
    .downloads a:hover { text-decoration: underline; }
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
        $download_links
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
            output = json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as exc:
            message = f"Action '{action}' failed: {exc}"
            status_class = "error"
            output = json.dumps({"ok": False, "action": action, "error": str(exc)}, indent=2, ensure_ascii=False)
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
            self._send_html(
                render_page(
                    input_path=saved["input_path"],
                    message=f"Uploaded and extracted zip into {saved['input_path']}",
                    status_class="ok",
                    output=json.dumps(saved, indent=2, ensure_ascii=False),
                )
            )
        except Exception as exc:
            self._send_html(render_page(message=f"Upload failed: {exc}", status_class="error"))

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
) -> str:
    adapters = sorted(build_registry())
    profiles = sorted(list_profiles())
    actions = ["detect", "inspect", "normalize", "validate", "report", "doctor", "suggest", "bundle", "schema"]
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
        download_links=render_download_links(downloads),
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
