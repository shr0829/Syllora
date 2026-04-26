from __future__ import annotations

import json
import mimetypes
import queue
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .llm_client import LLMClient
from .project_store import ProjectStore


class LearningRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    store: ProjectStore

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _serve_frontend(self, request_path: str) -> bool:
        dist_root = self.store.root / "apps" / "frontend" / "dist"
        index_path = dist_root / "index.html"
        if not index_path.exists():
            return False

        normalized = unquote(request_path or "/")
        relative = normalized.lstrip("/")

        if not relative:
            self._send_file(index_path)
            return True

        candidate = (dist_root / relative).resolve()
        dist_root_resolved = dist_root.resolve()
        try:
            candidate.relative_to(dist_root_resolved)
        except ValueError:
            self._send_json({"error": "Invalid path."}, status=HTTPStatus.BAD_REQUEST)
            return True

        if candidate.is_dir():
            candidate = candidate / "index.html"

        if candidate.exists() and candidate.is_file():
            self._send_file(candidate)
            return True

        if "." in Path(relative).name:
            self._send_json({"error": "Asset not found."}, status=HTTPStatus.NOT_FOUND)
            return True

        self._send_file(index_path)
        return True

    def _stream_project_events(self, project_id: str) -> None:
        subscription = self.store.subscribe_project(project_id)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self._send_cors_headers()
        self.end_headers()

        try:
            self.wfile.write(b"retry: 1500\n\n")
            self.wfile.flush()
            while True:
                try:
                    payload = subscription.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                    continue

                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                message_id = (
                    str(payload.get("project", {}).get("generation", {}).get("updatedAt") or "")
                    or str(payload.get("project", {}).get("updatedAt") or "")
                )
                self.wfile.write(f"id: {message_id}\n".encode("utf-8"))
                self.wfile.write(b"data: ")
                self.wfile.write(body)
                self.wfile.write(b"\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
        finally:
            self.store.unsubscribe_project(project_id, subscription)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw)

    def do_OPTIONS(self) -> None:
        self._send_json({}, status=HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path_parts = [part for part in parsed.path.split("/") if part]

        try:
            if parsed.path == "/api/health":
                self._send_json({"ok": True, "llm": self.store.llm.describe()})
                return

            if parsed.path == "/api/library":
                self._send_json(self.store.list_libraries())
                return

            if parsed.path == "/api/projects":
                self._send_json(self.store.list_projects())
                return

            if len(path_parts) == 3 and path_parts[:2] == ["api", "library"]:
                self._send_json(self.store.get_library(path_parts[2]))
                return

            if len(path_parts) == 3 and path_parts[:2] == ["api", "projects"]:
                self._send_json(self.store.get_project(path_parts[2]))
                return

            if len(path_parts) == 4 and path_parts[:2] == ["api", "projects"] and path_parts[3] == "events":
                self._stream_project_events(path_parts[2])
                return

            if (
                len(path_parts) == 6
                and path_parts[:2] == ["api", "projects"]
                and path_parts[3] == "goals"
                and path_parts[5] == "image"
            ):
                self._send_file(self.store.get_goal_image_path(path_parts[2], path_parts[4]))
                return

            if (
                len(path_parts) == 7
                and path_parts[:2] == ["api", "projects"]
                and path_parts[3] == "goals"
                and path_parts[5] == "images"
            ):
                self._send_file(self.store.get_goal_image_path(path_parts[2], path_parts[4], int(path_parts[6])))
                return

            if self._serve_frontend(parsed.path):
                return
        except FileNotFoundError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.NOT_FOUND)
            return
        except Exception as error:  # noqa: BLE001 - HTTP boundary
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json({"error": "Route not found."}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path_parts = [part for part in parsed.path.split("/") if part]

        try:
            if parsed.path == "/api/projects":
                payload = self._read_json_body()
                topic = (payload.get("topic") or payload.get("message") or "").strip()
                if not topic:
                    self._send_json({"error": "topic is required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(self.store.create_project(topic, payload.get("message", topic)), status=HTTPStatus.CREATED)
                return

            if len(path_parts) == 4 and path_parts[:2] == ["api", "projects"] and path_parts[3] == "messages":
                payload = self._read_json_body()
                content = (payload.get("content") or "").strip()
                if not content:
                    self._send_json({"error": "content is required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(self.store.append_message(path_parts[2], content))
                return

            if len(path_parts) == 4 and path_parts[:2] == ["api", "projects"] and path_parts[3] == "research":
                self._send_json(self.store.generate_research(path_parts[2]))
                return

            if len(path_parts) == 4 and path_parts[:2] == ["api", "projects"] and path_parts[3] == "plan":
                self._send_json(self.store.generate_plan(path_parts[2]))
                return

            if len(path_parts) == 5 and path_parts[:2] == ["api", "projects"] and path_parts[3:5] == ["lessons", "batch"]:
                self._send_json(self.store.generate_all_lessons(path_parts[2]))
                return

            if (
                len(path_parts) == 6
                and path_parts[:2] == ["api", "projects"]
                and path_parts[3] == "goals"
                and path_parts[5] == "lesson"
            ):
                self._send_json(self.store.generate_lesson(path_parts[2], path_parts[4]))
                return
        except FileNotFoundError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.NOT_FOUND)
            return
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception as error:  # noqa: BLE001 - HTTP boundary
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json({"error": "Route not found."}, status=HTTPStatus.NOT_FOUND)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    project_root = Path(__file__).resolve().parents[3]
    llm = LLMClient(project_root)
    store = ProjectStore(project_root, llm)
    handler_class = LearningRequestHandler
    handler_class.store = store

    server = ThreadingHTTPServer((host, port), handler_class)
    print(f"Syllora API listening on http://{host}:{port}")
    if (project_root / "apps" / "frontend" / "dist" / "index.html").exists():
        print(f"Syllora web UI available on http://{host}:{port}")
    print(f"LLM configured: {llm.configured} | model: {llm.model} | image model: {llm.image_model}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
