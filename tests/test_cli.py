"""End-to-end CLI tests against a fake in-process JSON-RPC server."""

import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import fixtures
from transfertrace import cli

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _eth_call_result(to, data):
    sel = data[-8:].lower()
    t = to.lower()
    if sel == "95d89b41":  # symbol()
        if t == fixtures.USDC.lower():
            return fixtures.SYMBOL_USDC
        if t == fixtures.MKR.lower():
            return fixtures.SYMBOL_MKR
        return "0x"  # unknown contract: empty -> fallback "?"
    if sel == "313ce567":  # decimals()
        if t == fixtures.USDC.lower():
            return fixtures.DECIMALS_6
        if t == fixtures.MKR.lower():
            return fixtures.DECIMALS_18
        return "0x"
    return "0x"


class FakeRpcHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _respond(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, req):
        method = req.get("method")
        params = req.get("params", [])
        rid = req.get("id")
        if method == "eth_getTransactionByHash":
            result = ({"hash": params[0], "from": fixtures.VITALIK,
                       "to": fixtures.USDC}
                      if params[0] == fixtures.TXHASH else None)
        elif method == "eth_getTransactionReceipt":
            result = ({"status": "0x1", "blockNumber": "0x1234",
                       "logs": [fixtures.erc20_log(), fixtures.erc1155_single_log(),
                                fixtures.unknown_log()]}
                      if params[0] == fixtures.TXHASH else None)
        elif method == "eth_call":
            result = _eth_call_result(params[0]["to"], params[0]["data"])
        else:
            result = None
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length).decode())
        if isinstance(payload, list):
            self._respond([self._handle(r) for r in payload])
        else:
            self._respond(self._handle(payload))


class TestCliEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeRpcHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def _run(self, *args):
        cmd = [sys.executable, "-m", "transfertrace.cli", *args,
               "--rpc", "http://127.0.0.1:%d" % self.port]
        return subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)

    def test_text_output(self):
        p = self._run(fixtures.TXHASH)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("DECODE-ONLY", p.stdout)
        self.assertIn(fixtures.TXHASH, p.stdout)
        self.assertIn("SUCCESS", p.stdout)
        self.assertIn("USDC", p.stdout)
        self.assertIn("1.5 USDC", p.stdout)
        self.assertIn("[ERC1155]", p.stdout)
        # full addresses, never truncated
        self.assertIn(fixtures.VITALIK.lower(), p.stdout)
        self.assertIn(fixtures.BURN.lower(), p.stdout)

    def test_json_output(self):
        p = self._run(fixtures.TXHASH, "--json")
        self.assertEqual(p.returncode, 0, p.stderr)
        flow = json.loads(p.stdout)
        self.assertEqual(flow["status"], "0x1")
        self.assertEqual(flow["movement_count"], 2)
        self.assertEqual(flow["tokens"][0]["symbol"], "USDC")

    def test_unknown_tx_exit_1(self):
        p = self._run("0x" + "ff" * 32)
        self.assertEqual(p.returncode, 1)
        self.assertIn("not found", p.stderr)

    def test_bad_hash_exit_2(self):
        p = self._run("garbage")
        self.assertEqual(p.returncode, 2)

    def test_seed_phrase_exit_2(self):
        p = self._run("abandon " * 11 + "about")
        self.assertEqual(p.returncode, 2)
        self.assertIn("seed phrase", p.stderr.lower())

    def test_bare_key_hex_exit_2(self):
        p = self._run("ab" * 32)
        self.assertEqual(p.returncode, 2)
        self.assertIn("private key", p.stderr.lower())

    def test_rpc_unreachable_exit_1(self):
        cmd = [sys.executable, "-m", "transfertrace.cli", fixtures.TXHASH,
               "--rpc", "http://127.0.0.1:1"]
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT,
                           timeout=30)
        self.assertEqual(p.returncode, 1)
        self.assertIn("error", p.stderr.lower())


if __name__ == "__main__":
    unittest.main()
