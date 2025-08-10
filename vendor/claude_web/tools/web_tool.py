import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests  # type: ignore
import websocket  # type: ignore


@dataclass
class WebConfig:
    port: int = int(os.getenv("CHROME_CDP_PORT", "9222"))
    min_delay: float = float(os.getenv("MIN_DELAY_SECONDS", "1.0"))
    max_delay: float = float(os.getenv("MAX_DELAY_SECONDS", "3.0"))


class WebTool:
    """CDP client exposing primitives: connect, go, click, fill, key, js, screenshot, wait."""

    def __init__(self, port: Optional[int] = None):
        self.port = port or WebConfig().port
        self.ws = None
        self.msg_id = 0

    def _get_ws_url(self) -> str:
        """Pick a valid page target's WebSocket URL; create one if none exist."""
        resp = requests.get(f"http://localhost:{self.port}/json", timeout=1.0)
        tabs = resp.json() if resp.ok else []
        # Prefer a 'page' target with a debugger URL
        for t in tabs:
            if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                return t["webSocketDebuggerUrl"]
        # Fallback: last resort, pick any with ws url
        for t in tabs:
            if t.get("webSocketDebuggerUrl"):
                return t["webSocketDebuggerUrl"]
        # As a last resort, try to open a new blank tab then retry
        try:
            requests.get(f"http://localhost:{self.port}/json/new?", timeout=1.0)
            time.sleep(0.2)
            tabs = requests.get(f"http://localhost:{self.port}/json", timeout=1.0).json()
            for t in tabs:
                if t.get("webSocketDebuggerUrl"):
                    return t["webSocketDebuggerUrl"]
        except Exception:
            pass
        raise RuntimeError(f"No CDP tabs found at port {self.port}. Start Chrome with --remote-debugging-port.")

    def connect(self):
        ws_url = self._get_ws_url()
        # Align with Chrome origin expectations; no Origin header by default
        self.ws = websocket.create_connection(ws_url, timeout=3)
        self.cmd("Page.enable")
        self.cmd("DOM.enable")
        self.cmd("Runtime.enable")

    def cmd(self, method: str, params: Optional[dict] = None):
        # Reconnect lazily if needed
        if self.ws is None:
            self.connect()
        self.msg_id += 1
        msg = {"id": self.msg_id, "method": method, "params": params or {}}
        payload = json.dumps(msg)
        tried_reconnect = False
        while True:
            try:
                self.ws.send(payload)
                while True:
                    resp = json.loads(self.ws.recv())
                    if resp.get("id") == self.msg_id:
                        return resp
            except Exception as e:
                if tried_reconnect:
                    raise RuntimeError(f"CDP command failed for {method}: {e}")
                # attempt reconnect once
                tried_reconnect = True
                try:
                    self.connect()
                except Exception as re:
                    # bubble up if cannot reconnect
                    raise RuntimeError(f"CDP reconnect failed for {method}: {re}")

    def _sleep(self):
        time.sleep(WebConfig().min_delay)

    def go(self, url: str):
        self.cmd("Page.navigate", {"url": url})
        time.sleep(2)

    def click(self, selector: str) -> bool:
        doc = self.cmd("DOM.getDocument")
        root = doc["result"]["root"]["nodeId"]
        element = self.cmd("DOM.querySelector", {"nodeId": root, "selector": selector})
        node_id = element["result"].get("nodeId")
        if not node_id:
            return False
        box = self.cmd("DOM.getBoxModel", {"nodeId": node_id})
        if "error" in box:
            return False
        content = box["result"]["model"]["content"]
        x = (content[0] + content[4]) / 2
        y = (content[1] + content[5]) / 2
        self.cmd("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        self.cmd("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
        return True

    def type(self, text: str):
        for ch in text:
            self.cmd("Input.dispatchKeyEvent", {"type": "char", "text": ch})

    def fill(self, selector: str, text: str):
        if self.click(selector):
            self.cmd("Input.dispatchKeyEvent", {"type": "keyDown", "key": "a", "modifiers": 2})
            self.type(text)

    def key(self, key_name: str):
        self.cmd("Input.dispatchKeyEvent", {"type": "keyDown", "key": key_name})

    def js(self, code: str) -> Any:
        """Evaluate JS and return structured result when possible.
        Uses returnByValue to get JSON-serializable objects directly.
        """
        try:
            result = self.cmd(
                "Runtime.evaluate",
                {"expression": code, "returnByValue": True},
            )
            if "error" in result:
                return None
            # Chrome CDP returns { result: { result: { type, value? } }, exceptionDetails? }
            if result.get("exceptionDetails"):
                return None
            inner = result.get("result", {}).get("result", {})
            if "value" in inner:
                return inner["value"]
            # Fallbacks for primitives without value
            rtype = inner.get("type", "undefined")
            if rtype in {"string", "number", "boolean"}:
                return inner.get("value")
            # null subtype
            if rtype == "object" and inner.get("subtype") == "null":
                return None
            return inner.get("description")
        except Exception:
            return None

    def wait(self, selector: str, timeout: float = 10.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            doc = self.cmd("DOM.getDocument")
            root = doc["result"]["root"]["nodeId"]
            el = self.cmd("DOM.querySelector", {"nodeId": root, "selector": selector})
            # Handle CDP response structure - check if result exists and has nodeId
            if el and "result" in el and el["result"] and el["result"].get("nodeId"):
                return True
            time.sleep(0.5)
        return False

    def screenshot(self, path: Optional[str] = None, quality: int = 80, fmt: str = "jpeg"):
        params = {"format": fmt}
        if fmt == "jpeg":
            params["quality"] = quality
        data = self.cmd("Page.captureScreenshot", params)["result"]["data"]
        if path:
            with open(path, "wb") as f:
                f.write(base64.b64decode(data))
            return path
        return data

    def close(self):
        if self.ws:
            self.ws.close()
            self.ws = None
