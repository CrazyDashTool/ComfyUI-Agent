#!/usr/bin/env python3
"""Small, dependency-free client for ComfyUI's public HTTP API."""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class ClientError(Exception):
    pass


class Client:
    def __init__(self, base, timeout=30):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def request(self, method, path, data=None):
        body = None if data is None else json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            self.base + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                detail = json.loads(raw)
            except ValueError:
                detail = raw
            raise ClientError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ClientError(f"Cannot reach {self.base}: {exc.reason}") from exc

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, data):
        return self.request("POST", path, data)


def load_workflow(path):
    try:
        with open(path, "r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ClientError(f"Cannot read workflow: {exc}") from exc
    # Accept exported API wrappers while keeping raw API JSON the canonical format.
    workflow = value.get("prompt") if isinstance(value, dict) and "prompt" in value else value
    if not isinstance(workflow, dict) or not workflow:
        raise ClientError("Workflow must be a non-empty JSON object")
    return workflow


def local_errors(workflow):
    errors = []
    ids = set(str(key) for key in workflow)
    for node_id, node in workflow.items():
        where = f"node {node_id}"
        if not isinstance(node, dict):
            errors.append(f"{where}: must be an object")
            continue
        if not isinstance(node.get("class_type"), str) or not node["class_type"]:
            errors.append(f"{where}: missing class_type")
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            errors.append(f"{where}: inputs must be an object")
            continue
        for name, value in inputs.items():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[1], int):
                if str(value[0]) not in ids:
                    errors.append(f"{where}.{name}: link references missing node {value[0]}")
    return errors


def output_files(history):
    rows = []
    for node_id, output in (history.get("outputs") or {}).items():
        for kind in ("images", "gifs", "audio"):
            for item in output.get(kind) or []:
                if isinstance(item, dict) and item.get("filename"):
                    rows.append({"node": node_id, "kind": kind, **item})
    return rows


def print_value(value, as_json=False):
    if as_json or not isinstance(value, str):
        print(json.dumps(value, ensure_ascii=False, indent=2))
    else:
        print(value)


def wait_for(client, prompt_id, timeout, interval):
    deadline = time.monotonic() + timeout
    encoded = urllib.parse.quote(prompt_id, safe="")
    while time.monotonic() < deadline:
        history = client.get(f"/history/{encoded}")
        record = history.get(prompt_id)
        if record:
            status = record.get("status") or {}
            if status.get("completed") or record.get("outputs"):
                messages = status.get("messages") or []
                failed = [m for m in messages if isinstance(m, list) and m and m[0] == "execution_error"]
                return {"prompt_id": prompt_id, "status": "error" if failed else "completed", "files": output_files(record), "history": record}
        time.sleep(interval)
    raise ClientError(f"Timed out waiting for prompt {prompt_id} after {timeout}s")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Standalone ComfyUI workflow client")
    parser.add_argument("--url", default=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188"))
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health")
    nodes = sub.add_parser("nodes")
    nodes.add_argument("--search")
    nodes.add_argument("--type")
    validate = sub.add_parser("validate")
    validate.add_argument("workflow")
    queue = sub.add_parser("queue")
    queue.add_argument("workflow")
    queue.add_argument("--wait", action="store_true")
    queue.add_argument("--timeout", type=float, default=600)
    wait = sub.add_parser("wait")
    wait.add_argument("prompt_id")
    wait.add_argument("--timeout", type=float, default=600)
    wait.add_argument("--interval", type=float, default=1)
    cancel = sub.add_parser("cancel")
    cancel.add_argument("prompt_id")
    args = parser.parse_args(argv)
    client = Client(args.url)

    if args.command == "health":
        stats = client.get("/system_stats")
        result = {"ok": True, "url": args.url, "system": stats.get("system", stats)}
    elif args.command == "nodes":
        definitions = client.get("/object_info")
        if args.type:
            if args.type not in definitions:
                raise ClientError(f"Unknown node type: {args.type}")
            result = {args.type: definitions[args.type]}
        elif args.search:
            needle = args.search.lower()
            result = {key: value for key, value in definitions.items() if needle in key.lower() or needle in str(value.get("display_name", "")).lower() or needle in str(value.get("category", "")).lower()}
        else:
            result = {"count": len(definitions), "types": sorted(definitions)}
    elif args.command == "validate":
        workflow = load_workflow(args.workflow)
        errors = local_errors(workflow)
        definitions = client.get("/object_info")
        for node_id, node in workflow.items():
            if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
                continue
            node_type = node.get("class_type")
            definition = definitions.get(node_type)
            if not definition:
                errors.append(f"node {node_id}: unknown class_type {node_type}")
                continue
            required = ((definition.get("input") or {}).get("required") or {})
            for name, schema in required.items():
                if name not in node["inputs"]:
                    errors.append(f"node {node_id}: missing required input {name}")
                    continue
                value = node["inputs"][name]
                choices = schema[0] if isinstance(schema, list) and schema and isinstance(schema[0], list) else None
                if choices is not None and not (isinstance(value, list) and len(value) == 2) and value not in choices:
                    errors.append(f"node {node_id}.{name}: unavailable value {value!r}")
        result = {"valid": not errors, "errors": errors, "note": "Validated against the server's current node definitions. ComfyUI performs final validation when queued."}
    elif args.command == "queue":
        workflow = load_workflow(args.workflow)
        errors = local_errors(workflow)
        if errors:
            raise ClientError("Invalid workflow: " + "; ".join(errors))
        result = client.post("/prompt", {"prompt": workflow, "client_id": uuid.uuid4().hex})
        if args.wait and result.get("prompt_id"):
            result = wait_for(client, result["prompt_id"], args.timeout, 1)
    elif args.command == "wait":
        result = wait_for(client, args.prompt_id, args.timeout, args.interval)
    else:
        # Interrupt only when this id is running; never stop an unrelated prompt.
        state = client.get("/queue")
        running = state.get("queue_running") or []
        pending = state.get("queue_pending") or []
        row_id = lambda row: str(row[1]) if isinstance(row, list) and len(row) > 1 else ""
        is_running = any(row_id(row) == args.prompt_id for row in running)
        is_pending = any(row_id(row) == args.prompt_id for row in pending)
        if is_pending:
            client.post("/queue", {"delete": [args.prompt_id]})
        if is_running:
            client.post("/interrupt", {})
        result = {"cancel_requested": is_running or is_pending, "prompt_id": args.prompt_id, "was_running": is_running, "was_pending": is_pending}

    print_value(result, args.json)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
