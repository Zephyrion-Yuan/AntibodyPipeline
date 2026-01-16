from __future__ import annotations

import json
import mimetypes
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from core.action_registry import list_actions, run_action


WEB_ROOT = Path(__file__).resolve().parent / "webui"


def _json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = HTTPStatus.OK) -> None:
    """返回JSON响应。"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _serve_file(handler: BaseHTTPRequestHandler, file_path: Path) -> None:
    """按静态文件方式输出前端资源。"""
    if not file_path.exists() or not file_path.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
        return

    content_type, _ = mimetypes.guess_type(file_path.as_posix())
    content_type = content_type or "application/octet-stream"
    data = file_path.read_bytes()

    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class AntibodyRequestHandler(BaseHTTPRequestHandler):
    """简单的API + 静态资源服务。"""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/actions":
            actions_payload = [
                {
                    "id": action.action_id,
                    "label": action.label,
                    "description": action.description,
                }
                for action in list_actions()
            ]
            _json_response(self, {"actions": actions_payload})
            return

        if parsed.path == "/":
            _serve_file(self, WEB_ROOT / "index.html")
            return

        static_path = (WEB_ROOT / parsed.path.lstrip("/")).resolve()
        if WEB_ROOT in static_path.parents or static_path == WEB_ROOT:
            _serve_file(self, static_path)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/actions/") and parsed.path.endswith("/run"):
            action_id = parsed.path.split("/")[3]

            def _runner() -> None:
                run_action(action_id)

            thread = threading.Thread(target=_runner, daemon=True)
            thread.start()
            _json_response(self, {"status": "started", "action_id": action_id})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def main(host: str = "127.0.0.1", port: int = 8000) -> None:
    """启动本地Web服务。"""
    server = HTTPServer((host, port), AntibodyRequestHandler)
    print(f"Serving AntibodyPipeline UI at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
