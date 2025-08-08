from adalflow.core.func_tool import FunctionTool
from .web_nav import JsTool

PROFILE_JS = r"""
(() => {
  const grab = sel => document.querySelector(sel)?.textContent?.trim() || null;
  const byText = (txt) => {
    const el = Array.from(document.querySelectorAll('section, div,h2,h3'))
      .find(n => (n.innerText||'').toLowerCase().includes(txt));
    return el?.innerText || null;
  };
  const name = grab('main h1, .pv-text-details__left-panel h1');
  const headline = grab('.text-body-medium.break-words, [data-test-id*="headline"]');
  const about = byText('about');
  const experience = byText('experience');
  const education = byText('education');
  const location = Array.from(document.querySelectorAll('li, span'))
    .map(x => x.textContent?.trim()).find(t => /bay area|san francisco|san jose|oakland/i.test(t)) || null;
  return ({ name, headline, about, experience, education, location, url: window.location.href });
})()
"""


def extract_profile() -> dict:
    return JsTool.call(PROFILE_JS)


ExtractProfileTool = FunctionTool(extract_profile, name="extract_profile")
