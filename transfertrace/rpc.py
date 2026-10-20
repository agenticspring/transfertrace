"""Minimal read-only JSON-RPC client over public Ethereum endpoints.

stdlib only (urllib). Supports single and batch requests. No signing,
no broadcasting, no private keys anywhere in this project.
"""

import json
import urllib.request
import urllib.error


class RpcError(Exception):
    pass


class RpcClient:
    def __init__(self, url, timeout=20):
        self.url = url
        self.timeout = timeout
        self._id = 0

    def _next_id(self):
        self._id += 1
        return self._id

    def _post(self, payload):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=body,
            headers={"Content-Type": "application/json",
                     "User-Agent": "transfertrace/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RpcError("HTTP %s from RPC endpoint" % e.code)
        except urllib.error.URLError as e:
            raise RpcError("network error reaching RPC endpoint: %s" % e.reason)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise RpcError("invalid JSON from RPC endpoint: %s" % e)

    def call(self, method, params):
        payload = {"jsonrpc": "2.0", "id": self._next_id(),
                   "method": method, "params": params}
        resp = self._post(payload)
        if "error" in resp:
            err = resp["error"]
            raise RpcError("RPC error %s: %s"
                           % (err.get("code"), err.get("message")))
        return resp.get("result")

    def batch(self, calls):
        """calls: list of (method, params). Returns list of results in order."""
        payload = [{"jsonrpc": "2.0", "id": self._next_id(),
                    "method": m, "params": p} for m, p in calls]
        resp = self._post(payload)
        if not isinstance(resp, list):
            raise RpcError("batch response was not a list")
        by_id = {r.get("id"): r for r in resp}
        out = []
        for item in payload:
            r = by_id.get(item["id"], {})
            if "error" in r:
                err = r["error"]
                raise RpcError("RPC error %s: %s"
                               % (err.get("code"), err.get("message")))
            out.append(r.get("result"))
        return out
