import importlib.util
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "products", "comfyui-workflow-master", "scripts", "comfyui_client.py")
spec = importlib.util.spec_from_file_location("comfyui_client", PATH)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class StandaloneSkillTests(unittest.TestCase):
    def test_valid_local_workflow(self):
        workflow = {
            "1": {"class_type": "Source", "inputs": {"value": 1}},
            "2": {"class_type": "Sink", "inputs": {"image": ["1", 0]}},
        }
        self.assertEqual(client.local_errors(workflow), [])

    def test_missing_link_and_invalid_nodes_are_reported(self):
        workflow = {
            "1": {"inputs": {"image": ["9", 0]}},
            "2": "wrong",
        }
        errors = client.local_errors(workflow)
        self.assertTrue(any("missing class_type" in error for error in errors))
        self.assertTrue(any("missing node 9" in error for error in errors))
        self.assertTrue(any("must be an object" in error for error in errors))

    def test_output_files(self):
        history = {"outputs": {"4": {"images": [{"filename": "x.png", "subfolder": "", "type": "output"}]}}}
        self.assertEqual(client.output_files(history)[0]["filename"], "x.png")


if __name__ == "__main__":
    unittest.main()
