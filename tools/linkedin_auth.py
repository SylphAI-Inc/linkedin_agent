"""LinkedIn authentication detection and handling tools."""

from adalflow.core.func_tool import FunctionTool
from .web_nav import js as run_js, go as nav_go, wait as nav_wait, click as nav_click


def check_auth_status() -> dict:
    """Check if user is logged into LinkedIn and return status details.
    
    Returns:
        dict: {"authenticated": bool, "page_type": str, "message": str}
    """
    # Check URL first
    current_url = run_js("window.location.href") or ""
    
    # Check for obvious auth indicators
    page_text = (run_js("document.body.innerText") or "").lower()
    
    auth_indicators = {
        "sign_in_required": any(phrase in page_text for phrase in [
            "sign in", "log in", "join linkedin", "welcome back"
        ]),
        "has_profile_nav": bool(run_js("""
            document.querySelector('button[aria-label*="me"], a[href*="/in/"], .global-nav__me')
        """)),
        "has_search_box": bool(run_js("""
            document.querySelector('input[placeholder*="search" i], .search-global-typeahead__input')
        """)),
        "on_feed_page": "/feed/" in current_url,
        "on_login_page": any(path in current_url for path in ["/login", "/uas/login"]),
    }
    
    # Determine authentication status
    if auth_indicators["on_login_page"] or auth_indicators["sign_in_required"]:
        authenticated = False
        message = "User needs to sign in to LinkedIn"
        page_type = "login_required" 
    elif auth_indicators["has_profile_nav"] and auth_indicators["has_search_box"]:
        authenticated = True
        message = "User is signed in to LinkedIn"
        page_type = "authenticated"
    else:
        authenticated = False
        message = "Authentication status unclear - user may need to sign in"
        page_type = "unknown"
    
    return {
        "authenticated": authenticated,
        "page_type": page_type,
        "message": message,
        "url": current_url,
        "indicators": auth_indicators
    }


def navigate_to_linkedin() -> str:
    """Navigate to LinkedIn main page and return status."""
    nav_go("https://www.linkedin.com")
    nav_wait("body", 5.0)
    
    auth_status = check_auth_status()
    return f"Navigated to LinkedIn. Auth status: {auth_status['message']}"


def prompt_for_login() -> str:
    """Provide instructions for manual login when auth is required.
    
    This function doesn't perform automatic login (for security/TOS reasons)
    but provides clear guidance to the user.
    """
    auth_status = check_auth_status()
    
    if auth_status["authenticated"]:
        return "User is already authenticated on LinkedIn"
    
    instructions = [
        "⚠️  LinkedIn authentication required",
        "Please manually sign in to LinkedIn:",
        "1. Open https://www.linkedin.com in your browser",
        "2. Sign in with your LinkedIn credentials", 
        "3. Once signed in, the agent can proceed with search operations",
        "",
        "For automated workflows, consider using LinkedIn API or ensure",
        "your browser session maintains authentication between runs."
    ]
    
    return "\n".join(instructions)


# Export as FunctionTools
CheckAuthTool = FunctionTool(fn=check_auth_status)
NavigateLinkedInTool = FunctionTool(fn=navigate_to_linkedin)
PromptLoginTool = FunctionTool(fn=prompt_for_login)