"""Reads a 'Share a movement profile' issue (from env), checks it and adds it to community/profiles.json.
Writes ok / game / message to $GITHUB_OUTPUT for the workflow."""
import json, os, re

ALLOWED = {"game", "multiplier", "minspeed", "minrange", "maxrange", "maxspeed", "omnicoupling"}
PATH = "community/profiles.json"


def out(**kv):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        for k, v in kv.items():
            v = str(v).replace("\n", " ").replace("\r", " ")
            f.write(f"{k}={v}\n")


def fields(body):
    """Issue forms render as '### Label' followed by the answer."""
    parts = re.split(r"^### (.+)$", body, flags=re.M)
    res = {}
    for i in range(1, len(parts) - 1, 2):
        val = parts[i + 1].strip()
        val = re.sub(r"^```\w*\s*|\s*```$", "", val).strip()
        res[parts[i].strip()] = "" if val == "_No response_" else val
    return res


def fail(msg):
    out(ok="false", game="", message="Couldn't add this profile: " + msg + " Edit the issue, then remove and re-add the approved label.")
    raise SystemExit(0)


f = fields(os.environ.get("ISSUE_BODY", ""))
appid = f.get("Steam App ID", "").strip()
game = re.sub(r"[^\w :'&.,()!-]", "", f.get("Game", "")).strip()[:80]
profile = " ".join(f.get("Profile", "").split())
author = re.sub(r"[^\w .'-]", "", f.get("Name to show", "")).strip()[:40] or "anonymous"
notes = f.get("Notes", "").strip()[:400] or None

if not re.fullmatch(r"\d{1,9}", appid):
    fail("the Steam App ID should be a number.")
if not game:
    fail("the game name is missing.")
tokens = re.findall(r"-(\w+)\s+(\S+)", profile)
if not tokens or " ".join(f"-{k} {v}" for k, v in tokens) != profile:
    fail("the profile should look like `-game Name -multiplier 1.2 -minspeed 0.3 ...`.")
clean = []
for k, v in tokens:
    k = k.lower()
    if k not in ALLOWED:
        fail(f"`-{k}` isn't a movement setting.")
    if k == "game":
        if not re.fullmatch(r"[A-Za-z0-9:'._]{1,60}", v):
            fail("the -game name has unexpected characters.")
    else:
        try:
            n = float(v)
        except ValueError:
            fail(f"`-{k}` should be a number.")
        if not 0 <= n <= 10:
            fail(f"`-{k}` is out of range.")
    clean.append(f"-{k} {v}")
profile = " ".join(clean)

with open(PATH, encoding="utf-8-sig") as fh:
    data = json.load(fh)
if any(p.get("appId") == int(appid) and " ".join(p.get("profile", "").split()) == profile for p in data["profiles"]):
    out(ok="true", game=game, message="Thanks! This profile is already in the shared list.")
    raise SystemExit(0)

data["profiles"].append({
    "appId": int(appid),
    "game": game,
    "author": author,
    "date": os.environ.get("ISSUE_DATE", "")[:10],
    "profile": profile,
    "notes": notes,
    "source": os.environ.get("ISSUE_URL"),
})
with open(PATH, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
out(ok="true", game=game, message=f"Thanks! Your {game} profile is now in the shared list. Omni Game Manager shows it the next time it starts.")
