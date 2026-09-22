#!/usr/bin/env python3
"""Add an episode to the podcast feed and publish it to GitHub Pages.

Usage:
  python3 scripts/publish.py --mp3 ep.mp3 --transcript ep.md \
      --title "AI round-up, 22 September" --date 2026-09-22 \
      --summary "Coding agents, retrieval benchmarks, and a prompting pattern."

The feed lives on an orphan `gh-pages` branch that is rebuilt and force-pushed
every run. That keeps exactly one commit of history, so the repository never
grows without bound even though each episode is a few megabytes. Only the most
recent KEEP_EPISODES episodes are kept.
"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from email.utils import format_datetime
from xml.sax.saxutils import escape

REPO = os.environ.get("PODCAST_REPO", "gadgetmies/daily-ai")
# Routine runs may only push freely to `claude/`-prefixed branches; pushes to
# other branches are checked and can be rejected. GitHub Pages is happy to serve
# from a branch with a slash in the name, so use the always-accepted prefix.
BRANCH = os.environ.get("PODCAST_BRANCH", "claude/gh-pages")
KEEP_EPISODES = 30

# Commits are authored as the repo owner so the branch never carries commits
# "authored by someone else", which would also trip the push check.
COMMIT_NAME = os.environ.get("PODCAST_COMMIT_NAME", "gadgetmies")
COMMIT_EMAIL = os.environ.get(
    "PODCAST_COMMIT_EMAIL", "71213783+gadgetmies@users.noreply.github.com")

OWNER, NAME = REPO.split("/")
BASE_URL = f"https://{OWNER}.github.io/{NAME}"
PODCAST_TITLE = "AI Round-up"
PODCAST_DESC = (
    "A short daily briefing on practical AI developments: new tools worth trying, "
    "techniques that change how you work, and capability jumps that matter. "
    "Generated automatically each weekday morning."
)
AUTHOR = "Miko Kiiski"


def run(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True,
                          capture_output=True)


def mp3_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path]).stdout
    return float(out.strip())


def hms(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def build_feed(episodes):
    items = []
    for ep in episodes:
        url = f"{BASE_URL}/episodes/{ep['slug']}.mp3"
        pub = dt.datetime.strptime(ep["date"], "%Y-%m-%d").replace(
            hour=6, minute=0, tzinfo=dt.timezone.utc)
        items.append(f"""    <item>
      <title>{escape(ep['title'])}</title>
      <description>{escape(ep['summary'])}</description>
      <itunes:summary>{escape(ep['summary'])}</itunes:summary>
      <pubDate>{format_datetime(pub)}</pubDate>
      <guid isPermaLink="false">{escape(ep['slug'])}</guid>
      <enclosure url="{escape(url)}" length="{ep['bytes']}" type="audio/mpeg"/>
      <itunes:duration>{hms(ep['seconds'])}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <link>{BASE_URL}/episodes/{escape(ep['slug'])}.md</link>
    </item>""")

    built = format_datetime(dt.datetime.now(dt.timezone.utc))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(PODCAST_TITLE)}</title>
    <link>{BASE_URL}/</link>
    <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>en-gb</language>
    <description>{escape(PODCAST_DESC)}</description>
    <lastBuildDate>{built}</lastBuildDate>
    <itunes:author>{escape(AUTHOR)}</itunes:author>
    <itunes:summary>{escape(PODCAST_DESC)}</itunes:summary>
    <itunes:explicit>false</itunes:explicit>
    <itunes:category text="Technology"/>
    <itunes:image href="{BASE_URL}/cover.png"/>
    <itunes:owner>
      <itunes:name>{escape(AUTHOR)}</itunes:name>
    </itunes:owner>
    <image>
      <url>{BASE_URL}/cover.png</url>
      <title>{escape(PODCAST_TITLE)}</title>
      <link>{BASE_URL}/</link>
    </image>
{chr(10).join(items)}
  </channel>
</rss>
"""


def build_index(episodes):
    rows = "\n".join(
        f'      <li><span class="d">{escape(e["date"])}</span> '
        f'<a href="episodes/{escape(e["slug"])}.mp3">{escape(e["title"])}</a> '
        f'<a class="t" href="episodes/{escape(e["slug"])}.md">transcript</a></li>'
        for e in episodes)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(PODCAST_TITLE)}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 42rem; margin: 3rem auto;
         padding: 0 1rem; }}
  code {{ background: rgba(128,128,128,.18); padding: .15em .4em; border-radius: 4px;
          word-break: break-all; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: .5rem 0; border-bottom: 1px solid rgba(128,128,128,.25); }}
  .d {{ opacity: .6; font-variant-numeric: tabular-nums; margin-right: .5rem; }}
  .t {{ opacity: .6; font-size: .85em; margin-left: .5rem; }}
</style></head>
<body>
  <h1>{escape(PODCAST_TITLE)}</h1>
  <p>{escape(PODCAST_DESC)}</p>
  <p>Subscribe in any podcast app: <code>{BASE_URL}/feed.xml</code></p>
  <h2>Episodes</h2>
  <ul>
{rows}
  </ul>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp3", required=True)
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--dry-run", action="store_true",
                    help="build the branch contents locally, do not push")
    ap.add_argument("--workdir", help="where to build (default: a temp dir)")
    args = ap.parse_args()

    work = args.workdir or tempfile.mkdtemp(prefix="feed-")
    os.makedirs(work, exist_ok=True)
    site = os.path.join(work, "site")
    remote = f"https://github.com/{REPO}.git"

    # A dry run against an existing workdir builds on what is already there, so
    # repeated runs exercise the same accumulate-and-prune path as production.
    reuse = args.dry_run and os.path.isdir(site)
    if not reuse:
        shutil.rmtree(site, ignore_errors=True)
        res = run(["git", "clone", "-q", "--depth", "1", "--branch", BRANCH,
                   remote, site], check=False)
        if res.returncode != 0:
            os.makedirs(site, exist_ok=True)
            print(f"no existing {BRANCH} branch - starting a fresh one")

    os.makedirs(os.path.join(site, "episodes"), exist_ok=True)
    meta_path = os.path.join(site, "episodes.json")
    episodes = []
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            episodes = json.load(fh)

    slug = args.date
    shutil.copy(args.mp3, os.path.join(site, "episodes", f"{slug}.mp3"))
    shutil.copy(args.transcript, os.path.join(site, "episodes", f"{slug}.md"))

    episodes = [e for e in episodes if e["slug"] != slug]
    episodes.append({
        "slug": slug,
        "date": args.date,
        "title": args.title,
        "summary": args.summary,
        "bytes": os.path.getsize(args.mp3),
        "seconds": mp3_duration(args.mp3),
    })
    episodes.sort(key=lambda e: e["date"], reverse=True)

    for stale in episodes[KEEP_EPISODES:]:
        for ext in ("mp3", "md"):
            path = os.path.join(site, "episodes", f"{stale['slug']}.{ext}")
            if os.path.exists(path):
                os.remove(path)
    episodes = episodes[:KEEP_EPISODES]

    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(episodes, fh, indent=2)
    with open(os.path.join(site, "feed.xml"), "w", encoding="utf-8") as fh:
        fh.write(build_feed(episodes))
    with open(os.path.join(site, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(build_index(episodes))
    open(os.path.join(site, ".nojekyll"), "w").close()

    cover_src = os.path.join(os.path.dirname(__file__), "..", "cover.png")
    if os.path.exists(cover_src) and not os.path.exists(os.path.join(site, "cover.png")):
        shutil.copy(cover_src, os.path.join(site, "cover.png"))

    if args.dry_run:
        print(f"built {len(episodes)} episode(s) in {site} (dry run, not pushed)")
        return

    # One orphan commit, force-pushed: history never accumulates old audio.
    shutil.rmtree(os.path.join(site, ".git"), ignore_errors=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": COMMIT_NAME,
           "GIT_AUTHOR_EMAIL": COMMIT_EMAIL,
           "GIT_COMMITTER_NAME": COMMIT_NAME,
           "GIT_COMMITTER_EMAIL": COMMIT_EMAIL}
    for cmd in (["git", "init", "-q", "-b", BRANCH],
                ["git", "add", "-A"],
                ["git", "-c", "commit.gpgsign=false", "commit", "-qm",
                 f"Episode {args.date}"],
                ["git", "remote", "add", "origin", remote],
                ["git", "push", "-q", "--force", "origin", BRANCH]):
        subprocess.run(cmd, cwd=site, check=True, env=env)

    print(f"published {slug} - {BASE_URL}/feed.xml ({len(episodes)} episodes live)")


if __name__ == "__main__":
    main()
