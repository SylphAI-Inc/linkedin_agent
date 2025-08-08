from adalflow.core.func_tool import FunctionTool
from vendor.claude_web.tools.web_tool import WebTool
from config import CDPConfig

_web = None


def _ensure():
    global _web
    if _web is None:
        _web = WebTool(port=CDPConfig().port)
    # (Re)connect if ws not ready
    try:
        if _web.ws is None:
            _web.connect()
    except Exception:
        # Force new instance on failure
        _web = WebTool(port=CDPConfig().port)
        _web.connect()
    return _web


def go(url: str) -> str:
    w = _ensure()
    w.go(url)
    return "navigated"


def click(selector: str) -> str:
    w = _ensure()
    w.click(selector)
    return "clicked"


def type_(selector: str, text: str) -> str:
    w = _ensure()
    w.fill(selector, text)
    return "typed"


def key(key_name: str) -> str:
    w = _ensure()
    w.key(key_name)
    return "keyed"


def js(code: str):
    w = _ensure()
    return w.js(code)


def wait(selector: str, timeout: float = 10.0) -> bool:
    w = _ensure()
    return w.wait(selector, timeout)


GoTool = FunctionTool(fn=go)
ClickTool = FunctionTool(fn=click)
TypeTool = FunctionTool(fn=type_)
KeyTool = FunctionTool(fn=key)
JsTool = FunctionTool(fn=js)
WaitTool = FunctionTool(fn=wait)
