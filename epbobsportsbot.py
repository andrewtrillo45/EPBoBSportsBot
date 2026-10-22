"""
EPBoBSportsBot - posts the latest gaming + sports news into Discord channels.

Runs on a schedule (GitHub Actions), checks every feed in feeds.yaml,
and posts anything new through the Discord webhook for that channel.
Stories already posted are remembered in seen.json so nothing double-posts.
"""

import calendar
import hashlib
import html
import json
import os
import re
import sys
import time
from pathlib import Path

import feedparser
import requests
import yaml

ROOT = Path(__file__).parent
FEEDS_FILE = ROOT / "feeds.yaml"
SEEN_FILE = ROOT / "seen.json"
BOT_NAME = "EPBoBSportsBot"
KEEP_SEEN_PER_CHANNEL = 400  # how many old story IDs to remember per channel

COLORS = {"gaming": 0x9B59B6, "sports": 0x1F8B4C}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 EPBoBSportsBot/1.0"
)
DRY_RUN = os.environ.get("DRY_RUN") == "1"


# ---------- helpers ----------

def load_seen():
    if SEEN_FILE.exists():
        try:
            return json.loads(SEEN_FILE.read_text())
        except json.JSONDecodeError:
            print("seen.json was damaged, starting fresh")
    return {}


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(seen, indent=1, sort_keys=True))


def normalize_title(title):
    # Google News adds " - Outlet Name" to the end; strip it so the same story
    # from two outlets is treated as one.
    t = re.sub(r"\s+-\s+[^-]{2,40}$", "", title or "")
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def story_id(title):
    return hashlib.sha1(normalize_title(title).encode()).hexdigest()[:16]


def clean_summary(text, limit=280):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def entry_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        if entry.get(key):
            return calendar.timegm(entry[key])
    return None


def entry_image(entry):
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key) or []:
            if m.get("url"):
                return m["url"]
    for link in entry.get("links", []):
        if link.get("type", "").startswith("image/"):
            return link.get("href")
    return None


def fetch_feed(url):
    if url.startswith("file://"):  # used for local testing
        return feedparser.parse(url[7:])
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    r.raise_for_status()
    return feedparser.parse(r.content)


def post_to_discord(webhook, embed):
    payload = {"username": BOT_NAME, "embeds": [embed]}
    if DRY_RUN:
        print("   [dry run] would post:", embed["title"])
        return True
    for _ in range(3):
        r = requests.post(webhook, json=payload, timeout=20)
        if r.status_code == 429:  # Discord rate limit - wait and retry
            time.sleep(float(r.json().get("retry_after", 2)) + 0.5)
            continue
        if r.ok:
            time.sleep(1.2)  # stay well under Discord's limits
            return True
        print(f"   Discord error {r.status_code}: {r.text[:200]}")
        return False
    return False


# ---------- Sleeper trending players ----------

SLEEPER_API = "https://api.sleeper.app/v1"
PLAYERS_FILE = ROOT / "sleeper_players.json"


def load_player_names(sport, cache):
    """Sleeper asks that the big player list be downloaded at most once a day,
    so a slim copy (id -> name/position/team) is kept in sleeper_players.json."""
    entry = cache.get(sport)
    if entry and time.time() - entry.get("updated", 0) < 23 * 3600:
        return entry["players"]
    r = requests.get(f"{SLEEPER_API}/players/{sport}", headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    slim = {}
    for pid, p in r.json().items():
        name = p.get("full_name") or " ".join(x for x in (p.get("first_name"), p.get("last_name")) if x)
        if not name and p.get("position") == "DEF":
            name = f"{p.get('team', pid)} Defense"
        slim[pid] = [name or pid, p.get("position") or "", p.get("team") or "FA"]
    cache[sport] = {"updated": time.time(), "players": slim}
    return slim


def sleeper_lines(sport, kind, lookback, limit, names):
    r = requests.get(
        f"{SLEEPER_API}/players/{sport}/trending/{kind}",
        params={"lookback_hours": lookback, "limit": limit},
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    r.raise_for_status()
    lines = []
    for i, row in enumerate(r.json(), 1):
        name, pos, team = names.get(str(row.get("player_id")), [str(row.get("player_id")), "", ""])
        tag = f" ({pos}, {team})" if pos else ""
        lines.append(f"`{i:>2}.` **{name}**{tag} — {row.get('count', 0):,}")
    return "\n".join(lines) or "No data right now."


def post_sleeper_trending(config, webhooks, seen, problems):
    st = config.get("sleeper_trending")
    if not st:
        return
    state = seen.setdefault("_sleeper", {})
    every = st.get("every_hours", 8) * 3600
    lookback = st.get("lookback_hours", 24)
    limit = st.get("limit", 10)
    cache = {}
    if PLAYERS_FILE.exists():
        try:
            cache = json.loads(PLAYERS_FILE.read_text())
        except json.JSONDecodeError:
            cache = {}

    for sport, channel in st.get("sports", {}).items():
        if time.time() - state.get(sport, 0) < every:
            continue
        webhook = webhooks.get(channel)
        if not webhook and not DRY_RUN:
            continue
        try:
            names = load_player_names(sport, cache)
            adds = sleeper_lines(sport, "add", lookback, limit, names)
            drops = sleeper_lines(sport, "drop", lookback, limit, names)
        except Exception as e:
            problems.append(f"sleeper/{sport}: {e}")
            continue
        embed = {
            "title": f"📈 Trending on Sleeper — {sport.upper()} (last {lookback}h)",
            "url": "https://sleeper.com/",
            "color": 0x00C2A8,
            "fields": [
                {"name": "🔥 Most Added", "value": adds[:1024], "inline": False},
                {"name": "🧊 Most Dropped", "value": drops[:1024], "inline": False},
            ],
            "footer": {"text": f"Sleeper • {BOT_NAME}"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if post_to_discord(webhook, embed):
            state[sport] = time.time()
            print(f"- sleeper {sport}: posted trending to #{channel}")

    if cache:
        PLAYERS_FILE.write_text(json.dumps(cache, separators=(",", ":")))


# ---------- main ----------

def main():
    config = yaml.safe_load(FEEDS_FILE.read_text())
    settings = config.get("settings", {})
    max_posts = settings.get("max_posts_per_channel_per_run", 4)
    max_age = settings.get("max_age_hours", 24) * 3600
    first_run_posts = settings.get("first_run_posts", 1)

    try:
        webhooks = json.loads(os.environ.get("WEBHOOKS", "{}"))
    except json.JSONDecodeError:
        sys.exit("WEBHOOKS secret is not valid JSON - check the setup guide")

    seen = load_seen()
    now = time.time()
    problems = []

    for channel, info in config["channels"].items():
        webhook = webhooks.get(channel)
        if not webhook and not DRY_RUN:
            print(f"- {channel}: no webhook set, skipping")
            continue

        first_run = channel not in seen
        seen_ids = seen.get(channel, [])
        seen_set = set(seen_ids)
        fresh = {}

        for feed in info["feeds"]:
            try:
                parsed = fetch_feed(feed["url"])
            except Exception as e:  # one broken source never stops the rest
                problems.append(f"{channel}/{feed['name']}: {e}")
                continue
            for entry in parsed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link")
                if not title or not link:
                    continue
                # Optional keyword filter: only keep stories whose title mentions one of these
                include = feed.get("include")
                if include and not any(k.lower() in title.lower() for k in include):
                    continue
                sid = story_id(title)
                if sid in seen_set or sid in fresh:
                    continue
                ts = entry_time(entry)
                if ts and now - ts > max_age:
                    continue
                fresh[sid] = {
                    "title": title,
                    "link": link,
                    "ts": ts or now,
                    "source": feed["name"],
                    "summary": clean_summary(entry.get("summary")),
                    "image": entry_image(entry),
                }

        # newest first
        stories = sorted(fresh.items(), key=lambda kv: kv[1]["ts"], reverse=True)
        limit = first_run_posts if first_run else max_posts
        to_post = stories[:limit]

        # oldest of the batch goes first so the channel reads in order
        posted = 0
        for sid, s in reversed(to_post):
            embed = {
                "title": f"{info.get('emoji', '')} {s['title']}"[:256],
                "url": s["link"],
                "color": COLORS.get(info.get("category"), 0x5865F2),
                "footer": {"text": f"{s['source']} • {BOT_NAME}"},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(s["ts"])),
            }
            if s["summary"]:
                embed["description"] = s["summary"]
            if s["image"]:
                embed["thumbnail"] = {"url": s["image"]}
            if post_to_discord(webhook, embed):
                seen_ids.append(sid)
                posted += 1

        # On the first run, mark everything as seen so old news isn't dumped later.
        # Otherwise, skipped extras (over the cap) are also marked so they don't pile up.
        for sid, _ in stories:
            if sid not in seen_ids:
                seen_ids.append(sid)

        seen[channel] = seen_ids[-KEEP_SEEN_PER_CHANNEL:]
        print(f"- {channel}: {len(stories)} new, posted {posted}")

    post_sleeper_trending(config, webhooks, seen, problems)

    save_seen(seen)
    if problems:
        print("\nSources that failed this run (others still worked):")
        for p in problems:
            print("  ", p)


if __name__ == "__main__":
    main()
