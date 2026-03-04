import re


VAX_KEYS = [
    ("DTAP", "DTaP"),
    ("PCV", "PCV"),
    ("MMRV", "MMRV"),
    ("VARICELLA", "Varicella"),
]


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def parse_vaccines_status(raw):
    """
    Parse free-text vaccines_status/vaccines_notes into a structured summary.

    Returns dict with:
      - utd: bool (up to date)
      - missing: list of human labels (e.g. ["DTaP", "PCV"])
      - medical_exemption: bool
    """
    text = strip_html(raw)
    up = text.upper()

    medical_exemption = any(x in up for x in ["MED EXEMPT", "MEDICAL EXEMPT", "EXEMPT"])

    utd = "UTD" in up or "UP TO DATE" in up

    missing = []
    for token, label in VAX_KEYS:
        # Match patterns like "MISSING DTaP", "DTaP MISSING", "DTaP DUE", "NEEDS DTaP"
        if re.search(rf"(MISSING|NEEDS|DUE).*{token}|{token}.*(MISSING|NEEDS|DUE)", up):
            missing.append(label)

    return {
        "utd": utd,
        "missing": missing,
        "medical_exemption": medical_exemption,
    }

