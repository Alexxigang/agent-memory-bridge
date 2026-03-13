from __future__ import annotations

import json
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
      <div class="card">
        <form method="post" action="/run" class="grid">
          <div>
            <label for="action">Action</label>
            <select id="action" name="action">$action_options</select>
          </div>
          <div>
            <label for="input_path">Input path</label>
            <input id="input_path" name="input_path" value="$input_path" placeholder="D:\path\to\memory" required>
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
      <div class="card output">
        <div class="banner $status_class">$message</div>
        <pre>$output</pre>
        <div class="tips">
          <div>Suggested first try: <code>detect</code> or <code>inspect</code> before <code>bundle</code>.</div>
          <div><code>normalize</code> and <code>validate</code> pair well for CI handoff checks.</div>
          <div><code>bundle</code> expects a target format and an output directory.</div>
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
        return {"ok": True, "action": action, "result": {"matches": detect_format(source)}}
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
        }
    if action == "normalize":
        if not output_path:
            raise ValueError("normalize requires an output path")
        package = normalize(source_format, source)
        export_canonical_json(package, Path(output_path))
        return {
            "ok": True,
            "action": action,
            "result": {"output_path": output_path, "entry_count": len(package.entries), "package_id": package.package_id},
        }
    if action == "validate":
        return {"ok": True, "action": action, "result": validate_package_file(source, Path(output_path) if output_path else None)}
    if action == "report":
        package = normalize(source_format, source)
        return {"ok": True, "action": action, "result": build_package_report(package)}
    if action == "doctor":
        package = normalize(source_format, source)
        return {"ok": True, "action": action, "result": build_doctor_report(package)}
    if action == "suggest":
        package = normalize(source_format, source)
        return {"ok": True, "action": action, "result": build_package_suggestions(package)}
    if action == "bundle":
        if not target_format:
            raise ValueError("bundle requires a target format")
        if not output_path:
            raise ValueError("bundle requires an output directory")
        result = run_bundle(source_format, source, target_format, Path(output_path), profile=profile, include_repair=True, zip_path=None)
        return {
            "ok": True,
            "action": action,
            "result": {
                "output_dir": str(result["output_dir"]),
                "target_format": result["target_format"],
                "entry_count": result["entry_count"],
                "artifacts": result["artifacts"],
            },
        }
    if action == "schema":
        return {"ok": True, "action": action, "result": build_canonical_package_schema()}
    raise ValueError(f"Unsupported action: {action}")


class MemoryBridgeRequestHandler(BaseHTTPRequestHandler):
    server_version = "AgentMemoryBridge/0.24"

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/":
            self.send_error(404)
            return
        self._send_html(render_page())

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/run":
            self.send_error(404)
            return
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
        try:
            result = execute_web_action(action, input_path, source_format, target_format, output_path, profile)
            message = f"Action '{action}' completed successfully."
            status_class = "ok"
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
            )
        )

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
    )


def serve_web_ui(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), MemoryBridgeRequestHandler)
    print(f"Agent Memory Bridge UI listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down Agent Memory Bridge UI")
    finally:
        server.server_close()
