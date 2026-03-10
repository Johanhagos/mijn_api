"""Simple country name -> ISO2 mapping used by the agent for VAT lookups.
Keep this small and extend as needed.
"""

MAP = {
    "netherlands": "NL",
    "holland": "NL",
    "nederland": "NL",
    "sweden": "SE",
    "sverige": "SE",
    "germany": "DE",
    "deutschland": "DE",
    "france": "FR",
    "united kingdom": "GB",
    "uk": "GB",
    "united states": "US",
    "usa": "US",
    "canada": "CA",
    "australia": "AU",
}


def lookup(name: str) -> str | None:
    if not name:
        return None
    key = name.strip().lower()
    # direct match
    if key in MAP:
        return MAP[key]
    # try approximate: check if any map key is contained in the name
    for k, v in MAP.items():
        if k in key:
            return v
    return None
