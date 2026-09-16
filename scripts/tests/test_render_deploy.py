import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from scripts.deploy_render import DeployError, deploy, request_json, wait_for_deploy

COMMIT = "a" * 40


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.requests.append(self.path)
        code, body = self.server.responses.pop(0)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        if code == 302:
            self.send_header("Location", "/must-not-follow")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


class RenderDeployTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.responses = []
        self.server.requests = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_waits_for_live_and_verifies_commit(self):
        self.server.responses = [
            (200, {"status": "build_in_progress"}),
            (200, {"status": "live", "commit": {"id": COMMIT}}),
        ]
        wait_for_deploy(self.url, "test-key", COMMIT, interval=0)
        self.assertEqual(len(self.server.requests), 2)

    def test_rejects_failed_cancelled_and_wrong_commit(self):
        for status in (
            "build_failed",
            "update_failed",
            "pre_deploy_failed",
            "canceled",
            "deactivated",
            "live",
        ):
            with self.subTest(status=status):
                self.server.responses = [(200, {"status": status, "commit": {"id": "b" * 40}})]
                with self.assertRaises(DeployError):
                    wait_for_deploy(self.url, "test-key", COMMIT, interval=0)

    def test_timeout_does_not_report_success(self):
        with self.assertRaisesRegex(DeployError, "Prazo"):
            wait_for_deploy(self.url, "test-key", COMMIT, timeout=0)
        self.assertEqual(self.server.requests, [])

    def test_does_not_follow_redirect_or_leak_error_response(self):
        for code in (302, 401, 500):
            with self.subTest(code=code):
                self.server.responses = [(code, {"message": "secret-response"})]
                with self.assertRaises(DeployError) as caught:
                    request_json(self.url, key="test-key")
                self.assertNotIn("secret-response", str(caught.exception))
                self.assertNotIn("test-key", str(caught.exception))
        self.assertNotIn("/must-not-follow", self.server.requests)

    def test_rejects_wrong_repo_branch_or_automatic_deploy_before_post(self):
        valid = {
            "repo": "https://github.com/Renatoxdev/elo-saude",
            "branch": "main",
            "autoDeploy": "no",
            "serviceDetails": {"url": "https://elo-saude-staging.onrender.com"},
        }
        for changes in (
            {"repo": "https://github.com/another/project"},
            {"branch": "feature"},
            {"autoDeploy": "yes"},
        ):
            with self.subTest(changes=changes):
                self.server.responses = [(200, {**valid, **changes})]
                with self.assertRaises(DeployError):
                    deploy("test-key", "srv-test", COMMIT, "Renatoxdev/elo-saude", api_url=self.url)
