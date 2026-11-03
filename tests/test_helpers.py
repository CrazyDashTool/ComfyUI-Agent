import asyncio
import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if "server" not in sys.modules:
    stub = types.ModuleType("server")

    class PromptServer:
        instance = None

    stub.PromptServer = PromptServer
    sys.modules["server"] = stub

import agent_server as ag


class TempFolderPaths:
    def __init__(self, root):
        self.root = root
        self.base = os.path.join(root, "models")
        self.input = os.path.join(root, "input")
        self.output = os.path.join(root, "output")
        self.temp = os.path.join(root, "temp")
        for path in (self.base, self.input, self.output, self.temp):
            os.makedirs(path, exist_ok=True)

    def install(self):
        module = types.ModuleType("folder_paths")
        module.folder_names_and_paths = {"checkpoints": ([self.base], {".safetensors"})}
        module.get_folder_paths = lambda name: [self.base] if name == "checkpoints" else []
        module.get_input_directory = lambda: self.input
        module.get_output_directory = lambda: self.output
        module.get_temp_directory = lambda: self.temp
        sys.modules["folder_paths"] = module
        return module

    @staticmethod
    def remove():
        sys.modules.pop("folder_paths", None)


def safetensors_bytes(tensors, metadata=None):
    header = {k: {"dtype": "F16", "shape": [2, 2], "data_offsets": [i * 8, i * 8 + 8]} for i, k in enumerate(tensors)}
    if metadata:
        header["__metadata__"] = metadata
    raw = json.dumps(header).encode("utf-8")
    return len(raw).to_bytes(8, "little") + raw + b"\0" * (8 * len(tensors))


class TextHelpers(unittest.TestCase):
    def test_text_of_content_shapes(self):
        self.assertEqual(ag.text_of(None), "")
        self.assertEqual(ag.text_of("hi"), "hi")
        self.assertEqual(ag.text_of([{"type": "text", "text": "a"}, {"type": "image"}, {"type": "text", "text": "b"}]), "a\nb")

    def test_repair_fills_missing_tool_results(self):
        messages = [
            {"role": "user", "content": "x"},
            {"role": "assistant", "tool_calls": [{"id": "a", "name": "t", "arguments": {}}, {"id": "b", "name": "t", "arguments": {}}]},
            {"role": "tool", "tool_call_id": "a", "content": "ok"},
        ]
        fixed = ag.repair(messages)
        self.assertEqual([m["role"] for m in fixed], ["user", "assistant", "tool", "tool"])
        self.assertEqual(fixed[-1]["content"], "Cancelled")

    def test_safe_args_accepts_python_literals_and_code_fences(self):
        self.assertEqual(ag.safe_args('```json\n{"a": 1,}\n```'), {"a": 1})
        self.assertEqual(ag.safe_args("{'a': True, 'b': None}"), {"a": True, "b": None})
        self.assertTrue(ag.safe_args("not json")["_parse_error"])

    def test_extract_json(self):
        self.assertEqual(ag.extract_json('x [1, 2] y', "["), [1, 2])
        with self.assertRaises(ag.LLMError):
            ag.extract_json("nothing", "{")
        with self.assertRaises(ag.LLMError):
            ag.extract_json("{broken", "{")


class ProviderHelpers(unittest.TestCase):
    def test_split_data_url(self):
        self.assertEqual(ag.split_data_url("data:image/png;base64,AAAA"), ("image/png", "AAAA"))
        self.assertEqual(ag.split_data_url("http://x"), (None, None))

    def test_media_part_respects_vision_and_provider(self):
        image = {"type": "image", "data_url": "data:image/png;base64,AAAA"}
        self.assertEqual(ag.media_part(image, False, False), {"type": "text", "text": "[image omitted]"})
        self.assertEqual(ag.media_part(image, True, False)["type"], "image_url")
        video = {"type": "video", "data_url": "data:video/mp4;base64,AAAA", "name": "v.mp4"}
        self.assertEqual(ag.media_part(video, True, True)["type"], "video_url")
        self.assertIn("cannot read video", ag.media_part(video, True, False)["text"])
        audio = {"type": "audio", "data_url": "data:audio/mpeg;base64,AAAA"}
        self.assertEqual(ag.media_part(audio, True, False)["input_audio"]["format"], "mp3")

    def test_gemini_schema_replaces_empty_object(self):
        schema = ag.gemini_params({"properties": {"free": {"type": "object", "description": "d"}}})
        self.assertEqual(schema["properties"]["free"]["type"], "string")

    def test_openai_conversion_keeps_tool_links(self):
        messages = [
            {"role": "assistant", "tool_calls": [{"id": "a", "name": "get_graph", "arguments": {"x": 1}}]},
            {"role": "tool", "tool_call_id": "a", "content": "ok"},
        ]
        out = ag.to_openai("sys", messages, vision=False, named_tools=True)
        self.assertEqual(out[0]["role"], "system")
        self.assertEqual(out[1]["tool_calls"][0]["function"]["name"], "get_graph")
        self.assertEqual(out[2]["name"], "get_graph")

    def test_anthropic_merges_tool_results_into_user_turns(self):
        out = ag.to_anthropic([
            {"role": "tool", "tool_call_id": "a", "content": "one"},
            {"role": "tool", "tool_call_id": "b", "content": "two"},
        ], vision=False)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["role"], "user")
        self.assertEqual(len(out[0]["content"]), 2)

    def test_retry_delay_is_bounded(self):
        self.assertGreaterEqual(ag.retry_delay(0), 0)
        self.assertLessEqual(ag.retry_delay(10), 8.5)


class ValidationHelpers(unittest.TestCase):
    def test_safe_rel_path(self):
        self.assertEqual(ag.safe_rel_path("sub\\file (1).png"), "sub/file (1).png")
        for bad in ("/etc/passwd", "../secret", "a/../../b", "C:\\x", "-rf", "", "a/b|c"):
            with self.subTest(bad=bad), self.assertRaises(ag.LLMError):
                ag.safe_rel_path(bad)

    def test_hf_and_github_urls(self):
        self.assertEqual(
            ag.hf_download_url("owner/name", "sub/model.safetensors"),
            "https://huggingface.co/owner/name/resolve/main/sub/model.safetensors",
        )
        with self.assertRaises(ag.LLMError):
            ag.hf_download_url("not-a-repo", "x")
        self.assertEqual(
            ag.public_model_url("https://huggingface.co/o/r/resolve/main/m.safetensors"),
            "https://huggingface.co/o/r/resolve/main/m.safetensors",
        )
        for bad in ("http://huggingface.co/o/r/resolve/main/m", "https://evil.example/o/r/resolve/main/m", "https://huggingface.co/o/r/blob/main/m"):
            with self.subTest(bad=bad), self.assertRaises(ag.LLMError):
                ag.public_model_url(bad)
        self.assertEqual(ag.normalize_github_repo("https://github.com/o/r.git"), ("o", "r"))
        with self.assertRaises(ag.LLMError):
            ag.normalize_github_repo("justa-name")

    def test_host_is_public_rejects_loopback_and_accepts_ip_literals(self):
        self.assertFalse(ag.host_is_public("127.0.0.1"))
        self.assertFalse(ag.host_is_public("localhost"))
        self.assertTrue(ag.host_is_public("8.8.8.8"))

    def test_asset_kind(self):
        self.assertEqual(ag.asset_kind("A.PNG"), "image")
        self.assertEqual(ag.asset_kind("clip.mp4"), "video")
        self.assertEqual(ag.asset_kind("model.safetensors"), "model")
        self.assertEqual(ag.asset_kind("notes.txt"), "")

    def test_clean_skill_name(self):
        self.assertEqual(ag.clean_skill_name("My Skill!"), "my-skill")
        self.assertLessEqual(len(ag.clean_skill_name("x" * 200)), 48)


class KnowledgeTests(unittest.TestCase):
    def test_knowledge_base_has_searchable_docs(self):
        docs = ag.knowledge_docs()
        self.assertTrue(docs, "knowledge base is empty")
        hits = ag.knowledge_search("flux cfg", 3)
        self.assertTrue(hits)
        self.assertLessEqual(len(hits), 3)
        for hit in hits:
            self.assertIn("source", hit)
            self.assertIn("text", hit)


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = bytes(range(256)) * 4096

        class Handler(http.server.BaseHTTPRequestHandler):
            payload = cls.payload
            ranges = []

            def do_GET(self):
                rng = self.headers.get("Range")
                Handler.ranges.append(rng)
                if rng and rng.startswith("bytes="):
                    start = int(rng.split("=", 1)[1].split("-", 1)[0])
                    body = self.payload[start:]
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{len(self.payload) - 1}/{len(self.payload)}")
                else:
                    body = self.payload
                    self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/file.bin"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_full_download_verifies_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "file.bin")
            digest = hashlib.sha256(self.payload).hexdigest()
            size = asyncio.run(ag.download_to_file(self.url, dest, digest))
            self.assertEqual(size, len(self.payload))
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), self.payload)

    def test_resume_appends_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "file.bin")
            with open(dest + ".part", "wb") as f:
                f.write(self.payload[:1000])
            size = asyncio.run(ag.download_to_file(self.url, dest))
            self.assertEqual(size, len(self.payload))
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), self.payload)

    def test_checksum_mismatch_removes_partial_and_keeps_destination_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "file.bin")
            with self.assertRaises(ag.LLMError):
                asyncio.run(ag.download_to_file(self.url, dest, "0" * 64))
            self.assertFalse(os.path.exists(dest))
            self.assertFalse(os.path.exists(dest + ".part"))


class FolderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.paths = TempFolderPaths(self.tmp.name)
        self.paths.install()

    def tearDown(self):
        TempFolderPaths.remove()
        self.tmp.cleanup()

    def test_model_file_info_reads_safetensors_header(self):
        target = os.path.join(self.paths.base, "nested", "model.safetensors")
        os.makedirs(os.path.dirname(target))
        with open(target, "wb") as f:
            f.write(safetensors_bytes(["a", "b"], {"architecture": "test"}))
        info = ag.model_file_info("checkpoints", "nested/model.safetensors")
        self.assertEqual(info["safetensors"]["tensors"], 2)
        self.assertEqual(info["safetensors"]["parameters"], 8)
        self.assertEqual(info["safetensors"]["metadata"]["architecture"], "test")
        with self.assertRaises(ag.LLMError):
            ag.model_file_info("checkpoints", "../escape.safetensors")

    def test_scan_assets_indexes_input_and_models(self):
        with open(os.path.join(self.paths.base, "model.safetensors"), "wb") as f:
            f.write(b"x")
        with open(os.path.join(self.paths.input, "photo.png"), "wb") as f:
            f.write(b"png")
        ag.ASSET_CACHE.update(at=0, rows=[])
        rows = ag.scan_assets()
        by_name = {r["name"]: r for r in rows}
        self.assertIn("photo.png", by_name)
        self.assertIn("model.safetensors", by_name)
        self.assertEqual(by_name["photo.png"]["root"], "input")
        self.assertEqual(by_name["model.safetensors"]["folder"], "checkpoints")

    def test_toggle_custom_node_renames_folder(self):
        import agent_server
        original = agent_server.custom_nodes_dirs
        base = os.path.join(self.tmp.name, "custom_nodes")
        os.makedirs(os.path.join(base, "Pack"))
        agent_server.custom_nodes_dirs = lambda: [base]
        try:
            out = ag.toggle_custom_node("Pack", False)
            self.assertTrue(out["restart_required"])
            self.assertTrue(os.path.isdir(os.path.join(base, "Pack.disabled")))
            again = ag.toggle_custom_node("Pack", False)
            self.assertTrue(again["ok"])
            self.assertTrue(os.path.isdir(os.path.join(base, "Pack.disabled")))
            ag.toggle_custom_node("Pack", True)
            self.assertTrue(os.path.isdir(os.path.join(base, "Pack")))
        finally:
            agent_server.custom_nodes_dirs = original


if __name__ == "__main__":
    unittest.main()
