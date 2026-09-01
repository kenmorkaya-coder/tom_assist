#!/usr/bin/env python3
"""Lifecycle/readonly evidence helper for the real packaged-app UI journey.

Never controls the UI. Computer Use drives the actual app separately. This
helper owns only the three child PIDs it launches and disposable local stores.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import socket
import sqlite3
import socketserver
import subprocess
import time
from threading import Thread

FIXTURE_RESPONSE = 'The connected beam transfers force to both columns. ' * 32 + 'END-WP21-永久-🙂'


class FixtureBroker(BaseHTTPRequestHandler):
    """Only this helper substitutes broker output. Production adapter is unchanged."""
    calls = []

    def log_message(self, *_): pass

    def do_GET(self):
        if self.path != '/status': self.send_error(404); return
        value = {'connected':True,'code':'OAUTH_READY','credential_owner':'tom-assist-keychain',
                 'model':'fixture-model','streaming':False,
                 'capabilities':{'provider_surface':'tom-assist/openai-oauth','visible_prompt_injection':True,
                                 'response_capture':True,'hidden_context_visibility':False,
                                 'model_internal_bias':'none','supports_system_field':False}}
        self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(value).encode())

    def do_POST(self):
        if self.path != '/complete': self.send_error(404); return
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        assert set(payload) == {'explicit_send','prompt'} and payload['explicit_send'] is True and '[TOM_ASSIST_STATE' in payload['prompt']
        self.calls.append(payload)
        time.sleep(2)  # Exercise live waiting/polling, not token streaming.
        self.send_response(200); self.end_headers(); self.wfile.write(json.dumps({'text':FIXTURE_RESPONSE,'model':'fixture-model','complete':True}).encode())


class FixtureBrokerServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def write_json(path, value):
    temporary = path.with_suffix(".pending")
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def rpc(path, envelope):
    with socket.socket(socket.AF_UNIX) as stream:
        stream.settimeout(45)
        stream.connect(str(path))
        stream.sendall(json.dumps(envelope).encode() + b"\n")
        return json.loads(stream.makefile("r").readline())


def readonly(path):
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def snapshot(data):
    with readonly(data / "tom-assist.sqlite3") as db:
        row = db.execute("SELECT id,state_version,state_digest FROM projects WHERE name='New Project'").fetchall()
        assert len(row) == 1, "expected exactly one UI-created New Project"
        project, version, state_digest = row[0]
        counts = {table:db.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id=?", (project,)).fetchone()[0] for table in ("state_events", "state_objects", "turns", "context_runs", "response_evaluations", "provider_sessions", "chat_conversations", "provider_exchanges")}
        receipts = db.execute("SELECT result_json FROM runtime_commit_receipts WHERE sent_turn_id IN (SELECT id FROM turns WHERE project_id=?) ORDER BY sent_turn_id", (project,)).fetchall()
        sessions = db.execute("SELECT * FROM provider_sessions WHERE project_id=? ORDER BY id", (project,)).fetchall()
        exchanges = db.execute("SELECT * FROM provider_exchanges WHERE project_id=? ORDER BY id", (project,)).fetchall()
    library = data / "projects" / project / "tom/library.sqlite3"
    with readonly(library) as db:
        tree, rgm, keys, settings = db.execute("SELECT tree,rgm,idempotency,settings FROM runtime_head").fetchone()
        originals = db.execute("SELECT record_id,content_hash,content FROM library_records ORDER BY record_id").fetchall()
        for _, digest, content in originals:
            assert hashlib.sha256(content.encode()).hexdigest() == digest
        demotions = db.execute("SELECT * FROM demotions ORDER BY event_id").fetchall()
    return {"project_id":project,"state_version":version,"state_digest":state_digest,"counts":counts,
            "tree_sha256":hashlib.sha256(tree).hexdigest(),"rgm_sha256":hashlib.sha256(rgm).hexdigest(),
            "engine_tick":json.loads(tree)["tick"],"rgm_tick":json.loads(rgm)["current_tick"],
            "idempotency":json.loads(keys),"settings":json.loads(settings),"receipts":[json.loads(x[0]) for x in receipts],
            "originals":originals,"demotions":demotions,"sessions":sessions,"exchanges":exchanges,
            "provider_calls":len(FixtureBroker.calls)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    root = args.run_root.resolve()
    root.mkdir(mode=0o700, exist_ok=False)
    app = args.app.resolve()
    assert app.is_dir() and (app / "Contents/MacOS/Tom Assist").is_file()
    children, logs = [], []
    data = root / "source"
    # Always offline. The product gateway still uses its production UDS adapter.
    fixture_socket = root / "oauth-fixture.sock"
    fixture = FixtureBrokerServer(str(fixture_socket), FixtureBroker)
    fixture_worker = Thread(target=fixture.serve_forever, daemon=True)
    fixture_worker.start()

    def stop():
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait(timeout=10)
        children.clear()
        for log in logs: log.close()
        logs.clear()

    def launch():
        data.mkdir(mode=0o700, exist_ok=True)
        env = {**os.environ,"PYTHONDONTWRITEBYTECODE":"1","TOM_ASSIST_APP_SUPPORT":str(data),
               "TOM_ASSIST_GATEWAY_SOCKET":str(root / "gateway.sock"),"TOM_ASSISTD_SOCKET":str(root / "assistd.sock"),
               "TOM_ASSIST_OAUTH_BROKER_SOCKET":str(fixture_socket)}
        commands = [
            [str(repo / ".venv-gateway/bin/python"), str(repo / "gateway/tom_gateway.py"), "--socket", env["TOM_ASSIST_GATEWAY_SOCKET"], "--data-dir", str(data)],
            [str(repo / "target/release/tom-assistd"), env["TOM_ASSISTD_SOCKET"], str(data / "tom-assist.sqlite3"), env["TOM_ASSIST_GATEWAY_SOCKET"]],
            [str(app / "Contents/MacOS/Tom Assist")],
        ]
        for name, command in zip(("gateway", "assistd", "desktop"), commands):
            log = (root / f"{name}.log").open("ab"); logs.append(log)
            children.append(subprocess.Popen(command, env=env, cwd=repo, stdout=log, stderr=subprocess.STDOUT))
        for _ in range(200):
            try:
                for name in ("gateway.sock", "assistd.sock"):
                    with socket.socket(socket.AF_UNIX) as check: check.connect(str(root / name))
                break
            except (FileNotFoundError, ConnectionRefusedError): pass
            assert all(p.poll() is None for p in children), "test child failed to start"
            time.sleep(0.05)
        else: raise RuntimeError("test sockets did not become ready")
        # Allow LaunchServices to observe the new GUI PID before Computer Use.
        time.sleep(1)
        assert all(p.poll() is None for p in children), "test child exited during startup"
        write_json(root / "ready.json", {"app":str(app),"data":str(data),"pids":[p.pid for p in children],"build_verification_only":True,"provider":"offline UDS broker fixture, never live OAuth"})

    try:
        launch()
        print(json.dumps({"ready":str(root / "ready.json")}), flush=True)
        while True:
            command_file = root / "command.json"
            if not command_file.exists(): time.sleep(0.1); continue
            command = json.loads(command_file.read_bytes()); command_file.unlink()
            try:
                kind = command["action"]
                if kind == "snapshot": result = snapshot(data)
                elif kind in ("restart", "fresh-recovery"):
                    stop()
                    if kind == "fresh-recovery": data = root / "recovered"
                    launch(); result = {"data":str(data),"pids":[p.pid for p in children]}
                elif kind == "replay":
                    current = snapshot(data)
                    with readonly(data / "tom-assist.sqlite3") as db:
                        response_id, packet, text, ordinal = db.execute("SELECT id,packet_digest,normalized_text,ordinal FROM turns WHERE project_id=? AND role='assistant'", (current["project_id"],)).fetchone()
                    result = rpc(root / "assistd.sock", {"protocol":"tom-assist/1.0","request_id":"wp20-replay","idempotency_key":"wp20-replay","method":"response.evaluate","actor":{"type":"desktop","instance_id":"wp20-test"},"project_id":current["project_id"],"sent_at":"2026-08-31T00:00:00Z","payload":{"project_id":current["project_id"],"packet_digest":packet,"response_turn_id":response_id,"response_text":text,"ordinal":ordinal,"complete":True,"created_at":"2026-08-31T00:00:00Z"}})
                    assert result["ok"], result
                    assert snapshot(data) == current, "replayed commit changed recovered state"
                elif kind == "stop":
                    stop(); write_json(root / "response.json", {"id":command["id"],"ok":True,"result":{"stopped":True}}); break
                else: raise ValueError("unknown journey lifecycle action")
                write_json(root / "response.json", {"id":command["id"],"ok":True,"result":result})
            except Exception as error:
                write_json(root / "response.json", {"id":command["id"],"ok":False,"error":repr(error)})
    finally:
        stop()
        fixture.shutdown(); fixture.server_close(); fixture_worker.join()


if __name__ == "__main__": main()
