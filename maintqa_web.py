# -*- coding: utf-8 -*-
"""
maintqa_web.py
Application Layer: Python HTTP Server for Marine Vessel MaintQA Architecture
Port: 127.0.0.1:8760 (Offline, In-process, 100% Local)

Follows the architecture diagram:
- Presentation Layer: maintqa_web.html
- Follow-up Query Interpretation: Rewrites query using last 3 turns if <= 8 chars or has demonstratives
- Rule Router: router.py (Regex-based, no LLM call)
- Aggregate Path: text_to_sql.py (DuckDB SQL, Abstention check, Model bypass for numbers)
- Procedure Path: rag_engine.py (Term mapping, BM25 Top 4, Context assembly, Verified quotes, DuckDB citation)
- Dual Translation: Korean dual-text translation if enabled
"""

import json
import os
import sys
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure pythonw safe stdout/stderr
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "server.log")
try:
    if sys.stdout is None or not hasattr(sys.stdout, "write"):
        sys.stdout = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
    if sys.stderr is None or not hasattr(sys.stderr, "write"):
        sys.stderr = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
except Exception:
    pass

# Import local architecture modules
from router import route_query, needs_followup_rewrite
from local_llm_client import rewrite_followup_query
from text_to_sql import process_text_to_sql_pipeline
from rag_engine import process_rag_pipeline, init_bm25_index
from db_manager import init_database, get_connection

HOST = "0.0.0.0"
PORT = int(os.environ.get("MAINTQA_PORT", 8080))
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maintqa_web.html")
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chat_history.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "server.log")
PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "server.pid")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history_data):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

class MaintQAHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            if os.path.exists(HTML_PATH):
                with open(HTML_PATH, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "maintqa_web.html not found")
        elif path == "/api/stats":
            con = get_connection(read_only=True)
            stats = {
                "vessels": con.execute("SELECT COUNT(*) FROM vessels").fetchone()[0],
                "master": con.execute("SELECT COUNT(*) FROM master").fetchone()[0],
                "pms": con.execute("SELECT COUNT(*) FROM pms").fetchone()[0],
                "approval": con.execute("SELECT COUNT(*) FROM approval").fetchone()[0],
                "attachments": con.execute("SELECT COUNT(*) FROM attachments").fetchone()[0],
                "consumption": con.execute("SELECT COUNT(*) FROM consumption").fetchone()[0],
                "narrative_records": con.execute("SELECT COUNT(*) FROM pms WHERE length(WORK_PROCEDURE_TEXT) >= 300").fetchone()[0]
            }
            con.close()
            self._send_json({"status": "ok", "stats": stats})
        elif path == "/api/history":
            history = load_history()
            self._send_json({"status": "ok", "sessions": history})
        elif path == "/api/health":
            self._send_json({"status": "ok", "service": "Aegis-Navi AI MaintQA Server", "port": PORT})
        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(post_body) if post_body else {}

            user_query = data.get("query", "").strip()
            history = data.get("history", [])
            dual_language = data.get("dual_language", False)

            if not user_query:
                self._send_json({"error": "Empty query"}, status_code=400)
                return

            t_start = time.time()

            # 1. Follow-up Query Interpretation (후속 질문 해석)
            rewritten_query = user_query
            was_rewritten = False
            rewrite_time_ms = 0.0

            if needs_followup_rewrite(user_query) and history:
                t_rw = time.time()
                rewritten_query = rewrite_followup_query(user_query, history)
                rewrite_time_ms = (time.time() - t_rw) * 1000.0
                was_rewritten = True

            # 2. Rule Router (규칙 라우터 - router.py, no LLM call)
            route = route_query(rewritten_query)

            # 3. Path Execution
            if route == "AGGREGATE":
                result = process_text_to_sql_pipeline(rewritten_query)
            else:
                result = process_rag_pipeline(rewritten_query, dual_language=dual_language)

            total_elapsed_ms = (time.time() - t_start) * 1000.0

            response_payload = {
                "original_query": user_query,
                "rewritten_query": rewritten_query if was_rewritten else None,
                "was_rewritten": was_rewritten,
                "rewrite_time_ms": rewrite_time_ms,
                "route": route,
                "result": result,
                "total_elapsed_ms": total_elapsed_ms
            }
            self._send_json(response_payload)

        elif path == "/api/history":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length).decode("utf-8")
            session_data = json.loads(post_body) if post_body else {}

            sessions = load_history()
            session_id = session_data.get("id")

            # Update existing or append new
            updated = False
            for idx, s in enumerate(sessions):
                if s.get("id") == session_id:
                    sessions[idx] = session_data
                    updated = True
                    break
            if not updated:
                sessions.insert(0, session_data)

            save_history(sessions)
            self._send_json({"status": "ok", "saved_id": session_id})
        else:
            self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        if path == "/api/history":
            session_id = query_params.get("id", [None])[0]
            if session_id:
                sessions = load_history()
                sessions = [s for s in sessions if s.get("id") != session_id]
                save_history(sessions)
                self._send_json({"status": "ok", "deleted_id": session_id})
            else:
                # Clear all
                save_history([])
                self._send_json({"status": "ok", "cleared": True})
        else:
            self.send_error(404, "Endpoint not found")

    def log_message(self, format, *args):
        try:
            msg = f"[{self.log_date_time_string()}] {format % args}\n"
            if sys.stdout and hasattr(sys.stdout, "write"):
                sys.stdout.write(msg)
                sys.stdout.flush()
        except Exception:
            pass

def run_server():
    global PORT
    print("="*70, flush=True)
    print("🚀 [AegisNavi-Pro Web Server] Starting Marine Engineering AI...", flush=True)
    print("="*70, flush=True)

    # Initialize DB & BM25 index on startup
    init_database()
    init_bm25_index()

    server = None
    candidate_ports = [PORT, 8080, 8000, 8760, 9090]
    for p in candidate_ports:
        try:
            server = HTTPServer((HOST, p), MaintQAHandler)
            PORT = p
            break
        except OSError:
            continue

    if server is None:
        print("[Error] Could not bind to any candidate port!", flush=True)
        return

    # Record PID
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

    print(f"\n✅ Server ready! Access via Web Browser:\n", flush=True)
    print(f"   👉 http://localhost:{PORT}", flush=True)
    print(f"   👉 http://127.0.0.1:{PORT}\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...", flush=True)
        server.server_close()
    finally:
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass

if __name__ == "__main__":
    run_server()

