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

    def test_llamacpp_detection_and_multimodal(self):
        self.assertTrue(ag.is_llamacpp({"provider": "llamacpp"}))
        self.assertTrue(ag.is_llamacpp({"provider": "openai", "base_url": "http://127.0.0.1:8080/v1"}))
        self.assertFalse(ag.is_llamacpp({"provider": "openai", "base_url": "https://api.openai.com/v1"}))

        # Model modality support
        self.assertTrue(ag.llamacpp_supports_video("Qwen2.5-VL-7B-Instruct.gguf"))
        self.assertTrue(ag.llamacpp_supports_video("MiniCPM-V-2_6-Q4_K_M.gguf"))
        self.assertTrue(ag.llamacpp_supports_video("gemma-3-4b-it"))
        self.assertFalse(ag.llamacpp_supports_video("Llama-3.1-8B-Instruct.gguf"))

        self.assertTrue(ag.llamacpp_supports_audio("Qwen2-Audio-7B.gguf"))
        self.assertTrue(ag.llamacpp_supports_audio("whisper-large-v3.gguf"))
        self.assertTrue(ag.llamacpp_supports_audio("mini-omni.gguf"))
        self.assertFalse(ag.llamacpp_supports_audio("Llama-3.1-8B-Instruct.gguf"))

        # media_part with llamacpp provider
        video = {"type": "video", "data_url": "data:video/mp4;base64,AAAA", "name": "clip.mp4"}
        audio = {"type": "audio", "data_url": "data:audio/wav;base64,AAAA", "name": "voice.wav"}

        # Multimodal video model accepts video
        v_ok = ag.media_part(video, True, False, llamacpp=True, model="Qwen2.5-VL-7B")
        self.assertEqual(v_ok["type"], "video_url")

        # Non-video model rejects video with explanation
        v_no = ag.media_part(video, True, False, llamacpp=True, model="Llama-3-8B")
        self.assertEqual(v_no["type"], "text")
        self.assertIn("does not support video", v_no["text"])

        # Multimodal audio model accepts audio
        a_ok = ag.media_part(audio, True, False, llamacpp=True, model="Qwen2-Audio-7B")
        self.assertEqual(a_ok["type"], "input_audio")

        # Non-audio model rejects audio with explanation
        a_no = ag.media_part(audio, True, False, llamacpp=True, model="Llama-3-8B")
        self.assertEqual(a_no["type"], "text")
        self.assertIn("does not support audio", a_no["text"])

        # Vision disabled skips video
        v_off = ag.media_part(video, False, False, llamacpp=True, model="Qwen2.5-VL-7B")
        self.assertIn("vision is off", v_off["text"])

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


class ThoughtSignatureHelpers(unittest.TestCase):
    def test_signature_is_read_from_the_google_extra_content(self):
        tc = {"id": "a", "function": {"name": "find_nodes", "arguments": "{}"},
              "extra_content": {"google": {"thought_signature": "CvcQAdHtim/pKv/c=="}}}
        self.assertEqual(ag.thought_signature(tc), "CvcQAdHtim/pKv/c==")
        self.assertEqual(ag.thought_signature({"thought_signature": "x"}), "x")
        self.assertEqual(ag.thought_signature({"function": {"thought_signature": "y"}}), "y")
        self.assertEqual(ag.thought_signature({"id": "a"}), "")

    def test_openai_calls_keep_the_signature(self):
        msg = {"tool_calls": [
            {"id": "a", "function": {"name": "find_nodes", "arguments": '{"q": "3d"}'}},
        ], "extra_content": {"google": {"thought_signature": "sig-1"}}}
        calls = ag.openai_calls(msg)
        self.assertEqual(calls[0]["name"], "find_nodes")
        self.assertEqual(calls[0]["arguments"], {"q": "3d"})
        self.assertEqual(calls[0]["thought_signature"], "sig-1")

    def test_gemini_replay_carries_the_signature_back(self):
        messages = [
            {"role": "assistant", "tool_calls": [
                {"id": "a", "name": "find_nodes", "arguments": {"q": "3d"}, "thought_signature": "sig-1"},
            ]},
            {"role": "tool", "tool_call_id": "a", "content": "ok"},
        ]
        out = ag.to_openai("sys", messages, vision=False, named_tools=True, gemini=True)
        call = out[1]["tool_calls"][0]
        self.assertEqual(call["extra_content"]["google"]["thought_signature"], "sig-1")
        other = ag.to_openai("sys", messages, vision=False, named_tools=True, gemini=False)
        self.assertNotIn("extra_content", other[1]["tool_calls"][0])

    def test_missing_signature_error_is_explained(self):
        raw = "400: Function call is missing a thought_signature in functionCall parts."
        self.assertIn("dropped the Gemini thought signature", ag.llm_error_text(raw))
        self.assertEqual(ag.llm_error_text("500: boom"), "500: boom")

    def test_raw_gemini_tool_call_shape_is_accepted(self):
        messages = [{"role": "assistant", "tool_calls": [{
            "id": "a", "type": "function",
            "function": {"name": "find_nodes", "arguments": "{\"q\": \"3d\"}"},
            "extra_content": {"google": {"thought_signature": "sig-2"}},
        }]}]
        out = ag.to_openai("sys", messages, vision=False, named_tools=True, gemini=True)
        call = out[1]["tool_calls"][0]
        self.assertEqual(call["function"]["name"], "find_nodes")
        self.assertEqual(json.loads(call["function"]["arguments"]), {"q": "3d"})
        self.assertEqual(call["extra_content"]["google"]["thought_signature"], "sig-2")


class GeminiStreamTests(unittest.TestCase):
    body = ""

    @classmethod
    def setUpClass(cls):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                data = GeminiStreamTests.body.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    @staticmethod
    def sse(chunks):
        return "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"

    def run_stream(self, chunks, tools):
        GeminiStreamTests.body = self.sse(chunks)
        cfg = {"base_url": self.url, "model": "gemini-3-pro", "api_key": "k"}

        async def run():
            events = []
            async for ev in ag.stream_openai(cfg, "sys", [{"role": "user", "content": "hi"}], tools):
                events.append(ev)
            return events

        return asyncio.run(run())

    def test_stream_keeps_the_thought_signature(self):
        chunks = [
            {"choices": [{"delta": {"content": "Working"}}]},
            {"choices": [{"delta": {"tool_calls": [{
                "id": "default_api:create_roadmap",
                "type": "function",
                "function": {"name": "create_roadmap", "arguments": "{\"summary\":\"x\"}"},
                "extra_content": {"google": {"thought_signature": "sig-abc"}},
            }]}}]},
            {"choices": [{"delta": {}}]},
        ]
        tools = [{"name": "create_roadmap", "description": "d", "parameters": {"type": "object", "properties": {}}}]
        events = self.run_stream(chunks, tools)
        done = events[-1]
        self.assertEqual(done["type"], "done")
        call = done["tool_calls"][0]
        self.assertEqual(call["name"], "create_roadmap")
        self.assertEqual(call["arguments"], {"summary": "x"})
        self.assertEqual(call["thought_signature"], "sig-abc")

    def test_parallel_calls_without_index_stay_separate(self):
        chunks = [
            {"choices": [{"delta": {"tool_calls": [{
                "id": "a", "type": "function",
                "function": {"name": "first_tool", "arguments": "{}"},
                "extra_content": {"google": {"thought_signature": "sig-1"}},
            }]}}]},
            {"choices": [{"delta": {"tool_calls": [{
                "id": "b", "type": "function",
                "function": {"name": "second_tool", "arguments": "{}"},
            }]}}]},
        ]
        tools = [{"name": "first_tool", "description": "d", "parameters": {"type": "object", "properties": {}}},
                 {"name": "second_tool", "description": "d", "parameters": {"type": "object", "properties": {}}}]
        events = self.run_stream(chunks, tools)
        calls = events[-1]["tool_calls"]
        self.assertEqual([c["name"] for c in calls], ["first_tool", "second_tool"])
        self.assertEqual(calls[0]["thought_signature"], "sig-1")
        self.assertNotIn("thought_signature", calls[1])


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

    def test_public_download_redirects_are_limited_to_hugging_face(self):
        for url in (
            "https://huggingface.co/o/r/resolve/main/m.safetensors",
            "https://cdn-lfs.huggingface.co/repos/ab/cd/file",
            "https://cdn-lfs.hf.co/repos/ab/cd/file",
            "https://cas-bridge.xethub.hf.co/xet-bridge-us/abc",
        ):
            with self.subTest(url=url):
                self.assertEqual(ag.public_download_redirect(url), url)
        for url in (
            "http://huggingface.co/o/r/resolve/main/m",
            "https://evil.example/file",
            "https://huggingface.co.evil.example/file",
            "https://user:pass@huggingface.co/file",
            "https://127.0.0.1/file",
        ):
            with self.subTest(url=url), self.assertRaises(ag.LLMError):
                ag.public_download_redirect(url)

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


class PersonaTests(unittest.TestCase):
    def test_persona_name_sanitizes_and_caps(self):
        self.assertEqual(ag.persona_name("  Nova \n Light "), "Nova Light")
        self.assertEqual(ag.persona_name("x" * 80), "x" * 40)
        self.assertEqual(ag.persona_name("   "), "")

    def test_system_prompt_uses_custom_agent_name(self):
        text = ag.build_system({"agent_name": "Nova", "user_name": "Толя"}, {"language": "Russian"})
        self.assertIn("You are Nova", text)
        self.assertIn("Толя", text)
        self.assertNotIn("{agent_name}", text)

    def test_system_prompt_defaults_to_comfy_agent(self):
        text = ag.build_system({}, {})
        self.assertIn("You are Comfy Agent", text)
        self.assertNotIn("The user's name is", text)


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

    def test_knowledge_maps_jobs_to_native_node_names(self):
        hits = ag.knowledge_search("load 3d model node", 4)
        self.assertTrue(hits)
        text = " ".join(h["text"] for h in hits)
        self.assertIn("Load3D", text)
        self.assertIn("Load 3D & Animation", text)

    def test_knowledge_doc_lists_node_purposes(self):
        docs = ag.knowledge_docs()
        files = {d["file"] for d in docs}
        self.assertIn("nodes.md", files)
        nodes = [d for d in docs if d["file"] == "nodes.md"]
        body = " ".join(d["text"] for d in nodes)
        for name in ["LoadImage", "KSampler", "CheckpointLoaderSimple", "SaveImage"]:
            self.assertIn(name, body)


class ModelReadinessTests(unittest.TestCase):
    def test_system_prompt_requires_the_model_check(self):
        text = ag.build_system({}, {})
        self.assertIn("check_model_setup", text)

    def test_system_prompt_explains_the_batch_parameter(self):
        text = ag.build_system({}, {})
        self.assertIn("batch", text)

    def test_prompting_guide_maps_families_to_prompt_styles(self):
        docs = ag.knowledge_docs()
        files = {d["file"] for d in docs}
        self.assertIn("model-prompting.md", files)
        body = " ".join(d["text"] for d in docs if d["file"] == "model-prompting.md")
        for name in ["FLUX.1", "Z-Image", "Qwen-Image", "negative prompt"]:
            self.assertIn(name, body)

    def test_prompting_guide_is_searchable_by_family(self):
        hits = ag.knowledge_search("prompting z-image turbo", 4)
        self.assertTrue(hits)
        self.assertTrue(any(h["source"] == "model-prompting.md" for h in hits))


class CompatibilityTests(unittest.TestCase):
    def test_report_has_backend_and_frontend_capabilities(self):
        report = ag.compatibility_report()
        self.assertIn("checks", report)
        self.assertTrue(report["checks"])
        ids = {c["id"] for c in report["checks"]}
        for cid in ("python", "folder_paths", "server", "nodes", "extension", "aiohttp"):
            self.assertIn(cid, ids)
        for check in report["checks"]:
            self.assertIn(check["level"], ("ok", "warn", "fail"))
            self.assertIsInstance(check["ok"], bool)
            self.assertTrue(check["name"])
        python = next(c for c in report["checks"] if c["id"] == "python")
        self.assertEqual(python["level"], "ok")
        extension = next(c for c in report["checks"] if c["id"] == "extension")
        self.assertEqual(extension["level"], "ok")
        self.assertEqual(report["failed"], sum(1 for c in report["checks"] if c["level"] == "fail"))
        self.assertEqual(report["ok"], report["failed"] == 0)


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


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = os.path.join(self.tmp.name, "custom_nodes")
        os.makedirs(self.base)
        self.original_dirs = ag.custom_nodes_dirs
        ag.custom_nodes_dirs = lambda: [self.base]
        ag.PACK_CLASS_CACHE.clear()

    def tearDown(self):
        ag.custom_nodes_dirs = self.original_dirs
        ag.PACK_CLASS_CACHE.clear()
        sys.modules.pop("nodes", None)
        self.tmp.cleanup()

    def write_pack(self, folder, classes, disabled=False):
        path = os.path.join(self.base, folder + (".disabled" if disabled else ""))
        os.makedirs(path, exist_ok=True)
        mapping = ",\n".join(f'    "{c}": object' for c in classes)
        with open(os.path.join(path, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("NODE_CLASS_MAPPINGS = {\n" + mapping + "\n}\n")

    def test_preflight_classifies_node_types(self):
        self.write_pack("GoodPack", ["PackNode"])
        self.write_pack("OffPack", ["DisabledNode"], disabled=True)

        class KSampler:
            MODULE = ""

        fake = types.ModuleType("nodes")
        fake.NODE_CLASS_MAPPINGS = {"KSampler": KSampler}
        sys.modules["nodes"] = fake

        rows = {
            r["type"]: r
            for r in ag.preflight_nodes(
                ["KSampler", "PackNode", "DisabledNode", "FaceDetailer", "TotallyUnknown"]
            )
        }
        self.assertEqual(rows["KSampler"]["state"], "loaded")
        self.assertEqual(rows["PackNode"]["state"], "import_error")
        self.assertEqual(rows["PackNode"]["pack"], "GoodPack")
        self.assertEqual(rows["DisabledNode"]["state"], "pack_disabled")
        self.assertEqual(rows["FaceDetailer"]["state"], "missing_pack")
        self.assertEqual(rows["FaceDetailer"]["repo"], "ltdrdata/ComfyUI-Impact-Pack")
        self.assertEqual(rows["TotallyUnknown"]["state"], "unknown_class")

    def test_known_pack_repo_matches_prefix(self):
        self.assertEqual(ag.known_pack_repo("VHS_VideoCombine"), "Kosinkadink/ComfyUI-VideoHelperSuite")
        self.assertEqual(ag.known_pack_repo("TotallyUnknown"), "")


class ContextBudgetTests(unittest.TestCase):
    def messages(self, images=0, text="hello"):
        content = [{"type": "text", "text": text}]
        for i in range(images):
            content.append({"type": "image", "data_url": "data:image/png;base64,AAAA"})
        return [{"role": "user", "content": content}]

    def test_estimate_counts_text_tools_and_images(self):
        plain = ag.estimate_prompt_tokens("sys", [{"role": "user", "content": "abc"}], [])
        self.assertGreater(plain, 0)
        with_img = ag.estimate_prompt_tokens("sys", self.messages(images=2), [])
        self.assertGreaterEqual(with_img - plain, 5000)

    def test_fit_context_keeps_messages_that_fit(self):
        msgs = self.messages(images=1)
        kept, over = ag.fit_context(msgs, [], "sys", 100000)
        self.assertEqual(len(kept), 1)
        self.assertLessEqual(over, 100000)

    def test_fit_context_strips_older_images_when_over_budget(self):
        msgs = [
            {"role": "user", "content": [{"type": "image", "data_url": "data:image/png;base64,AAAA"}]},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": [{"type": "image", "data_url": "data:image/png;base64,BBBB"}]},
        ]
        kept, over = ag.fit_context(msgs, [], "sys", 6000)
        self.assertLessEqual(over, 6000)
        images = [p for m in kept for p in (m["content"] if isinstance(m["content"], list) else []) if p.get("type") == "image"]
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["data_url"].endswith("BBBB"), True)

    def test_fit_context_without_limit_returns_input(self):
        msgs = self.messages(images=3)
        kept, over = ag.fit_context(msgs, [], "sys", 0)
        self.assertEqual(kept, msgs)
        self.assertEqual(over, 0)

    def test_strip_images_keeps_last_images_only(self):
        msgs = [
            {"role": "user", "content": [{"type": "image", "data_url": "a"}, {"type": "text", "text": "t"}]},
            {"role": "user", "content": [{"type": "image", "data_url": "b"}]},
        ]
        out = ag.strip_images(msgs, 1)
        images = [p for m in out for p in (m["content"] if isinstance(m["content"], list) else []) if p.get("type") == "image"]
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["data_url"], "b")

    def test_fit_context_trims_old_turns_when_budget_is_small(self):
        msgs = [{"role": "user", "content": "the goal"}]
        for i in range(20):
            msgs.append({"role": "assistant", "content": "reply %d " % i + "x" * 400})
            msgs.append({"role": "user", "content": "question %d " % i + "y" * 400})
        kept, over = ag.fit_context(msgs, [], "sys", 1200)
        self.assertLess(over, 1200)
        self.assertLess(len(kept), len(msgs))
        self.assertEqual(kept[0]["content"], "the goal")
        self.assertEqual(kept[-1]["content"], msgs[-1]["content"])

    def test_trim_history_drops_orphan_tool_messages(self):
        msgs = [
            {"role": "user", "content": "goal"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "function": {"name": "x", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "result"},
            {"role": "user", "content": "next"},
        ]
        trimmed = ag.trim_history(msgs, 1)
        roles = [m["role"] for m in trimmed]
        self.assertNotIn("tool", roles)
        self.assertEqual(trimmed[0]["content"], "goal")

    def test_trim_history_cancels_unanswered_tool_calls(self):
        msgs = [
            {"role": "user", "content": "goal"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "function": {"name": "x", "arguments": "{}"}}]},
            {"role": "user", "content": "next"},
        ]
        trimmed = ag.trim_history(msgs, 2)
        ids = [m.get("tool_call_id") for m in trimmed if m["role"] == "tool"]
        self.assertIn("c1", ids)


if __name__ == "__main__":
    unittest.main()
