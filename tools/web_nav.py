from adalflow.core.func_tool import FunctionTool
from vendor.claude_web.tools.web_tool import WebTool
from config import CDPConfig

_web = None


def _ensure():
    global _web
    if _web:
        return _web
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


GoTool = FunctionTool(go, name="go")
ClickTool = FunctionTool(click, name="click")
TypeTool = FunctionTool(type_, name="type")
KeyTool = FunctionTool(key, name="key")
JsTool = FunctionTool(js, name="js")
WaitTool = FunctionTool(wait, name="wait")
