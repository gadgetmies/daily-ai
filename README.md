# daily-ai

Pipeline behind the **AI Round-up** podcast: a short practitioner-facing AI
briefing, generated each weekday morning by a Claude Code routine and published
as an RSS feed on GitHub Pages.

## How it fits together

```
routine run
  ├─ research + write the episode script        (the routine's prompt)
  ├─ scripts/setup_tts.sh    install Kokoro + ffmpeg, fetch model weights
  ├─ scripts/synth.py        script.txt  ->  mastered episode.mp3
  └─ scripts/publish.py      mp3 + transcript -> claude/gh-pages -> feed.xml
```

The feed is served from the `claude/gh-pages` branch at
<https://gadgetmies.github.io/daily-ai/feed.xml>.

## Why these choices

**Kokoro, not a cloud TTS API.** Cloud environments run with `Trusted` network
access by default, which allows package registries and GitHub and nothing else,
so calls to OpenAI, ElevenLabs, Google and friends fail at the proxy with a 403
on the CONNECT. Kokoro-82M is a local neural model whose weights live on GitHub
releases, which *is* reachable, and it is a large step up from RHVoice.

**The `claude/` branch prefix.** Routine runs push freely to `claude/`-prefixed
branches. Pushes elsewhere are checked and rejected if the branch is protected,
has an open PR, or carries commits authored by someone else — which a plain
`gh-pages` branch would, from the second run onward. GitHub Pages is happy to
serve from a branch with a slash in its name.

**An orphan commit, force-pushed.** Each run rebuilds the branch as a single
commit. Episodes are a few megabytes each; keeping history would grow the
repository without bound. Only the most recent 30 episodes are kept.

## Running it by hand

```bash
bash scripts/setup_tts.sh
python3 scripts/synth.py script.txt episode.mp3 --voice bf_emma
python3 scripts/publish.py \
  --mp3 episode.mp3 --transcript episode.md \
  --title "AI round-up, 22 September" \
  --summary "One sentence." --date 2026-09-22
```

Add `--dry-run --workdir build` to `publish.py` to build the site locally
without pushing. Repeated dry runs against the same workdir accumulate, so the
retention and pruning path gets exercised the same way it does in production.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `PODCAST_REPO` | `gadgetmies/daily-ai` | Repository the feed is published to |
| `PODCAST_BRANCH` | `claude/gh-pages` | Branch GitHub Pages serves |
| `MODEL_DIR` | `/tmp/kokoro` | Where the Kokoro weights are cached |
| `PODCAST_COMMIT_NAME` / `PODCAST_COMMIT_EMAIL` | repo owner | Commit identity |

`KEEP_EPISODES` (30) is set at the top of `scripts/publish.py`.

## One-time setup

1. Commit this repository to `main`.
2. Create a routine at [claude.ai/code/routines](https://claude.ai/code/routines)
   with this repository selected. See `ROUTINE.md` for the prompt.
3. After the first successful run, enable Pages:
   **Settings → Pages → Deploy from a branch → `claude/gh-pages` → `/ (root)`**.
4. Subscribe to `https://gadgetmies.github.io/daily-ai/feed.xml` in a podcast app.
