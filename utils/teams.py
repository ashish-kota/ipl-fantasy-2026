import os

# Maps exact team name (as used in matches.csv) to logo file path
TEAM_LOGOS = {
    "Chennai Super Kings": "data/csk.png",
    "Delhi Capitals": "data/dc.png",
    "Gujarat Titans": "data/gt.png",
    "Kolkata Knight Riders": "data/kkr.png",
    "Lucknow Super Giants": "data/lsg.png",
    "Mumbai Indians": "data/mi.png",
    "Punjab Kings": "data/pk.png",
    "Royal Challengers Bengaluru": "data/rcb.png",
    "Rajasthan Royals": "data/rr.png",
    "Sunrisers Hyderabad": "data/srh.png",
}

# Short display names for space-constrained UI
TEAM_SHORT = {
    "Chennai Super Kings": "CSK",
    "Delhi Capitals": "DC",
    "Gujarat Titans": "GT",
    "Kolkata Knight Riders": "KKR",
    "Lucknow Super Giants": "LSG",
    "Mumbai Indians": "MI",
    "Punjab Kings": "PBKS",
    "Royal Challengers Bengaluru": "RCB",
    "Rajasthan Royals": "RR",
    "Sunrisers Hyderabad": "SRH",
}


def get_logo(team_name: str) -> str | None:
    """Return logo path if it exists, else None."""
    path = TEAM_LOGOS.get(team_name)
    if path and os.path.exists(path):
        return path
    return None


def get_short(team_name: str) -> str:
    """Return short team code."""
    return TEAM_SHORT.get(team_name, team_name)
