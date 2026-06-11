#!/usr/bin/env python3

import argparse
import csv
import html
import os
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEFAULT_DBC_PATH = "/home/demokit/MKpilot/opendbc/dbc/radar_CAN2.dbc"


def load_rows(csv_path):
    with open(csv_path, newline="") as f:
        return list(csv.DictReader(f))


def resolve_route_context(route_ref):
    route_path = Path(route_ref).expanduser()

    if route_path.exists():
        if route_path.name.endswith("--0") and len(route_path.parents) >= 2:
            return route_path.parent.name, str(route_path.parent)
        if route_path.is_dir() and len(route_path.parents) >= 1:
            return route_path.name, str(route_path)

    route_name = route_path.name if route_path.name else route_ref
    return route_name, str(Path.home() / "Recs" / route_name)


def cabana_command(route_ref, seek_seconds, extra_args):
    route_name, data_dir = resolve_route_context(route_ref)
    cmd = ["./tools/cabana/cabana", "--data_dir", data_dir, "--dbc", DEFAULT_DBC_PATH, route_name]
    cmd.extend(extra_args)
    cmd.extend(["--seek", f"{seek_seconds}", "--dcam"])
    return cmd


def cabana_command_display(route_ref, seek_seconds, extra_args):
    route_name, data_dir = resolve_route_context(route_ref)
    parts = ["./tools/cabana/cabana", "--data_dir", data_dir, "--dbc", DEFAULT_DBC_PATH, f'"{route_name}"']
    parts.extend(extra_args)
    parts.extend(["--seek", f"{seek_seconds}", "--dcam"])
    return " ".join(parts)


def make_html(csv_path, route, rows):
    title = f"CPD Events - {html.escape(os.path.basename(csv_path))}"
    rows_html = []
    for row in rows:
        seek = row.get("seconds_elapsed", "")
        seek_display = html.escape(row.get("timestamp", seek))
        event_id = html.escape(row.get("event_id", ""))
        segment_index = html.escape(row.get("segment_index", ""))
        signal = html.escape(row.get("signal", ""))
        event = html.escape(row.get("event", ""))
        file_name = html.escape(row.get("file", ""))
        from_label = html.escape(row.get("from_label", ""))
        to_label = html.escape(row.get("to_label", ""))
        duration = html.escape(row.get("child_duration_seconds", ""))
        rows_html.append(
            f"""
            <tr>
              <td>{event_id}</td>
              <td>{seek_display}</td>
              <td>{html.escape(seek)}</td>
              <td>{segment_index}</td>
              <td>{signal}</td>
              <td>{event}</td>
              <td>{from_label} → {to_label}</td>
              <td>{duration}</td>
              <td>{file_name}</td>
              <td><a class=\"launch\" href=\"/launch?seek={html.escape(seek)}\">Open in Cabana</a></td>
            </tr>
            """
        )

    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; background: #111827; color: #e5e7eb; }}
    h1 {{ margin: 0 0 8px 0; font-size: 28px; }}
    .meta {{ color: #9ca3af; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; background: #0f172a; border: 1px solid #334155; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #334155; text-align: left; }}
    th {{ position: sticky; top: 0; background: #111827; }}
    tr:hover {{ background: #1f2937; }}
    a.launch {{ color: #93c5fd; text-decoration: none; font-weight: 600; }}
    a.launch:hover {{ text-decoration: underline; }}
    code {{ background: #1f2937; padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>CPD Event List</h1>
  <div class=\"meta\">Route: <code>{html.escape(route)}</code> | CSV: <code>{html.escape(csv_path)}</code></div>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Timestamp</th><th>Seconds</th><th>Segment</th><th>Signal</th><th>Event</th><th>Transition</th><th>Duration</th><th>File</th><th>Action</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows_html)}
    </tbody>
  </table>
</body>
</html>
"""


class ViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/launch":
            query = parse_qs(parsed.query)
            seek = query.get("seek", [None])[0]
            if seek is None:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"missing seek")
                return

            try:
                float(seek)
            except ValueError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"invalid seek")
                return

            cmd = cabana_command(self.server.route, seek, self.server.cabana_args)
            display_cmd = cabana_command_display(self.server.route, seek, self.server.cabana_args)
            print(display_cmd)
            subprocess.Popen(cmd, cwd=self.server.workspace_root, env=self.server.launch_env)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            command_html = "".join([
                "<pre style='white-space:pre-wrap;background:#0f172a;padding:12px;",
                "border:1px solid #334155;border-radius:6px'>",
                html.escape(display_cmd),
                "</pre>",
            ])
            response = "".join([
                "<html><body style='font-family:sans-serif;background:#111827;color:#e5e7eb;padding:24px'>",
                f"Launched Cabana at <code>{html.escape(seek)}</code> seconds.<br/>",
                command_html,
                "<a href='/'>Back</a></body></html>",
            ])
            self.wfile.write(response.encode())
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.server.html_page.encode())

    def log_message(self, fmt, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="Render CPD CSV rows as clickable Cabana launches.")
    parser.add_argument("csv", help="Path to the CPD CSV file")
    parser.add_argument("route", nargs="?", help="Route path or name to open in Cabana (defaults to the CSV stem)")
    parser.add_argument("--cabana-arg", action="append", default=[], help="Additional argument to pass to Cabana (repeatable)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (use 0 for auto-select)")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    csv_path = os.path.abspath(args.csv)
    route = args.route or Path(csv_path).stem
    rows = load_rows(csv_path)
    html_page = make_html(csv_path, route, rows)

    server = ThreadingHTTPServer((args.host, args.port), ViewerHandler)
    server.html_page = html_page
    server.route = route
    server.cabana_args = args.cabana_arg
    server.workspace_root = str(Path(__file__).resolve().parents[2])
    server.launch_env = os.environ.copy()
    server.launch_env.setdefault("QT_QPA_PLATFORM", "xcb")

    bound_port = server.server_address[1]
    url = f"http://{args.host}:{bound_port}/"
    print(f"Serving {csv_path} at {url}")
    print(f"Route: {route}")
    print("Ctrl-C to stop.")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
