from typing import Dict


def draft_dm(profile: Dict) -> str:
    name = (profile.get("name") or "there").split()[0]
    role = profile.get("headline") or "your background"
    return (
        f"Hey {name} — noticed {role}. We're exploring roles that might fit your stack. "
        f"Curious to share what you're excited about next?"
    )
