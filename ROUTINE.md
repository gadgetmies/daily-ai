# Routine configuration

Settings for the routine at [claude.ai/code/routines](https://claude.ai/code/routines).

| Field | Value |
| --- | --- |
| Name | AI round up |
| Repositories | `gadgetmies/daily-ai` |
| Schedule | Weekdays, 09:00 (Europe/Helsinki) |
| Environment | Default is fine. See the note on setup scripts below. |
| Connectors | None required. Remove any that aren't needed. |

## Prompt

Paste everything below into the routine's **Instructions** box.

---

Gather the latest AI news from reputable sources and publish it as a podcast episode. The focus should be actionable and practitioner-facing, not business/finance news.

Prioritize, in roughly this order:

1. New tools, products, APIs, models, or skills/plugins/features that someone could actually go try or adopt this week (coding agents, dev tools, new model capabilities, notable open-weight releases, new integrations, browser/OS AI features, etc.).
2. New ways of working: techniques, workflows, prompting/agent-design patterns, benchmarks or evals that change how people should use AI day to day, and credible "here's what worked for us" reports from practitioners or companies.
3. Notable capability jumps or surprising technical results (a model doing something new, a big benchmark result, a real security/safety finding that changes how you should operate a tool) — especially when they have a practical, near-term impact on how listeners build or work.

De-prioritize heavily: funding rounds, valuations, IPO timing, M&A, lawsuits, antitrust/policy maneuvering, and geopolitics. Only include one of these if it directly and concretely changes what a builder/user can or should do (e.g. a policy change that blocks a tool they use, a license change on a model they might adopt) — and even then, frame it briefly around the practical implication rather than the deal/political mechanics. Skip pure stock-price/valuation/political-drama stories entirely.

Editorial requirements:

- Keep the content concise and accurate — state only what is stated in the sources (cross-check anything surprising against 2+ outlets before including it).
- Group multiple sources covering the same underlying story into a single item rather than listing them separately.
- For each tool/technique item, make the "so what" concrete: what you'd use it for, how to try it, or what to change in how you work — not just that it launched.
- Especially highlight things that are surprising and have (or will likely have) a practical impact.
- Do not repeat a story already covered in a previous round-up. Before finalizing the story list, read the archive at https://claude.ai/code/artifact/d6c6b4e2-73bd-4d9b-9ebb-bbdc72c1fde2 (Artifact action "read_db", collection "episodes", query ordered by "date" desc, limit ~15) to see which story keys/topics were already covered. Skip stories that are substantively the same as one already logged there. If a previously covered story has a genuinely new, material development, it's fine to include it, but frame it explicitly as an update ("following up on X from an earlier briefing...") rather than presenting it as new.
- After finalizing this episode's script, write a new entry back to that same archive (Artifact action "write_db", db_op "set", collection "episodes", doc_id = today's date as YYYY-MM-DD) with the shape {"date": "YYYY-MM-DD", "items": [{"key": "short-stable-slug", "title": "...", "summary": "one sentence"}, ...]} — one item per story covered, so future runs can dedupe against it.

Writing the script:

- Write it as spoken prose in a plain text file, one paragraph per beat, blank lines between paragraphs. No markdown headings, bullets, or URLs — it is going to be read aloud.
- Open by naming the day's date and previewing the items in one sentence. Close by pointing at the transcript for sources.
- Spell out things that a speech synthesiser reads badly: write dates as words ("the twenty-second of September"), expand symbols and units, and avoid bare version strings and acronyms that should be spelled out.
- Aim for four to seven minutes of speech, which is roughly 700 to 1100 words.

Producing and publishing (the repository `gadgetmies/daily-ai` is cloned for you; run these from its root):

1. `bash scripts/setup_tts.sh` — installs the Kokoro neural TTS stack and ffmpeg, and caches the model weights. Do not substitute a cloud TTS API: the environment's network access blocks them at the proxy with a 403, and retrying wastes the run.
2. Write the spoken script to `script.txt` and a transcript with source links to `episode.md`. The transcript is markdown, is published alongside the audio, and should list each story with its sources.
3. `python3 scripts/synth.py script.txt episode.mp3 --voice bf_emma` — synthesizes and masters the audio. Takes roughly 40 seconds per minute of speech.
4. `python3 scripts/publish.py --mp3 episode.mp3 --transcript episode.md --title "AI round-up, <day> <month>" --summary "<one sentence naming the stories>" --date <YYYY-MM-DD>` — adds the episode to the feed and pushes it.
5. Confirm the push succeeded and report, in a few lines, which stories you covered and the episode URL. If any step failed, say which one and what the error was rather than reporting success.

---

## Note on the environment setup script

`scripts/setup_tts.sh` downloads about 340 MB of model weights on a cold start,
which adds a minute or two to the run. To avoid paying that each time, copy the
contents of that script into the environment's **Setup script** field — setup
script results are cached between sessions. Step 1 of the prompt then becomes a
no-op that verifies the cache, so it can stay in either case.

If you'd rather not change the Default environment (the setup script applies to
every session that uses it), create a separate environment for this routine.
