# Granola meeting follow-ups

When I finish a meeting recorded in Granola, a Paseo session starts within about five minutes of Granola having its notes ready. It works out what the meeting was about and what follow-ups it has, puts my clear commitments on my task board, and drafts any messages I promised. It also starts a session that looks into each follow-up worth working on. Then it waits for me to reply, with something like "add 2 3", "drop 1", "draft 1" or "look into 9".

## How it works

1. A scheduled task runs `watch.py` every 5 minutes, without a window.
2. `watch.py` asks Granola's public API for notes updated since the last good poll (minus 2 hours), and for notes created in the last 7 days.
   - Granola lists a note only once its AI summary exists, which normally means the meeting has ended.
   - Granola has no feed of meetings in progress, and its webhooks also fire only once the summary exists, so polling loses at most 5 minutes.
3. For each new note I own, the watcher saves the note and a readable transcript to `%LOCALAPPDATA%\agent-setup\granola-watch\meetings\<date-time>-<note id>\`. Then it starts a top-level Paseo session titled "Meeting · <title>", labelled `granola.note` and `granola.date`.
4. That session follows [job.md](job.md):
   - it reads the meeting, then looks for context on the task board, in email and in earlier meetings with the same people;
   - it captures my clearly attributed, concrete commitments with `relationship_hub.capture_task`, with the idempotency key `granola-<note id>-<n>`, so a rerun never adds a task twice;
   - it writes `report.md` next to the note;
   - it writes `followups.json` and runs `followups.py create`, which gives each follow-up worth working on its own session (at most 8 new ones per meeting), or links a session I already used for that work;
   - it finishes with a short summary that reads well on a phone, with links to the tasks and sessions;
   - everything else (other people's commitments, ideas, new contacts, sending drafts) waits for me.
5. If a report starts with `Not a meeting:` (a pocket recording, a video playing), the watcher archives that session once it's idle, unless I replied in it.

**Follow-up sessions** are top-level Paseo sessions titled "Follow-up <date> · <item>" and labelled `granola.followup.note`, `granola.followup.key` and `granola.followup.date`. They never get `granola.note`, because `watch.py` uses that label to find the meeting's own session. Each one looks into its item read-only for about five minutes, prepares a draft or a plan, and waits for me. `sessions.json` in the meeting folder records them, so a rerun never duplicates a session. `followups.py archive-stale` archives earlier days' follow-up sessions that are idle and that I never replied to.

| File | What it does |
| --- | --- |
| `watch.py` | Polls Granola and starts the meeting sessions. Standard library only; run it with `python -I`. |
| `job.md` | What each meeting session does, and the formats of the report and the summary. Edit it to change what the session writes or captures. |
| `followups.py` | Starts or links a session for each follow-up (`create --meeting-dir <folder>`, with `--dry-run` to preview) and archives unopened ones (`archive-stale`). It uses the Paseo helpers in `../daily-digest/sessions.py`. The prompt each follow-up session gets is `PROMPT` near the top. |
| `register-task.ps1` | Creates or updates the Windows scheduled task: every 5 minutes, one run at a time, a 10-minute limit, no window. |
| `test_watch.py` | An offline test against a fake Granola API and a fake Paseo, in a temporary folder. Run it after changing `watch.py`. |

## Setup

1. In Granola, open Settings > Connectors > API keys and create a personal key with access to personal notes. Granola's API needs its Business plan.
2. Pipe the key into `python -I watch.py --set-key`. It saves the key in `%LOCALAPPDATA%\agent-setup\granola-watch\granola-api-key`, readable only by your account and SYSTEM.
3. Check the key, mark the notes already in Granola as handled, then register the task:

   ```
   python -I watch.py --check
   python -I watch.py --baseline
   powershell -NoProfile -ExecutionPolicy Bypass -File register-task.ps1
   ```

`--check` and `--baseline` print whose notes the key can see. Sessions start only for meetings owned by an address in `owner_emails`.

## Running it by hand

- `watch.py --dry-run` shows what a poll would do, and starts nothing.
- `watch.py --note not_XXXXXXXXXXXXXX` processes one note now, even an old or already handled one.
- Add `--test` to run an old meeting through the job without touching the task board or starting follow-up sessions. The session lists what it would have captured, and previews the follow-up sessions with `followups.py create --dry-run`.

## Settings

Put overrides in `%LOCALAPPDATA%\agent-setup\granola-watch\config.json`. The defaults are `DEFAULTS` in `watch.py`:

- `owner_emails`: whose meetings get sessions;
- `min_words` (50): shorter transcripts get no session;
- `lookback_days` (7);
- `settle_minutes` (2): a transcript that ended this recently waits one poll, in case it's still recording;
- `max_sessions_per_day` (15) and `max_sessions_per_run` (4);
- `provider`, `thinking`, `mode` and `cwd` for the meeting sessions.

## State and failures

`state.json` records every note seen, with its status:

- `baseline`;
- `spawned`, with the agent ID and folder;
- `skipped`, with the reason: someone else's note, or a transcript that's too short;
- `pending`, retried on every poll;
- `launching`, while a session starts. If a run dies there, the next poll looks for a session labelled with the note before starting another;
- `failed`.

`watch.log` records each poll, and `last_run.json` the last start.

If Granola rejects the key, if polls keep failing for 3 hours, or if a note fails for good (6 fetch attempts or 3 launch attempts), the watcher starts one session a day titled "Granola watch needs attention", which says what broke and how to fix it. If Paseo itself is down, the failure is only logged.

To stop the watcher, run `register-task.ps1 -Disable`.

## Limits

- **It starts only after the meeting.** If Granola writes a summary while the recording is still going, only the 2-minute settle check catches it.
- **Other people's words reach an agent with broad permissions.** The transcript holds what everyone in the meeting said, and the session runs with `bypassPermissions`. Three things guard against instructions planted in a meeting, and they are written rules, not an enforced boundary:
  - the session's prompt contains no meeting text;
  - `job.md` tells the session to treat everything in the folder as data;
  - the first pass only captures commitments and starts follow-up sessions. Those sessions' prompts carry the meeting session's own summary of their item, with short quotes, and no transcript text. They can still open the meeting folder, so their prompt also treats meeting text as data.
- **The machine has to be on.** After an outage, the next poll picks up notes updated since the last good poll, up to 7 days back.

## What to change for your setup

- **Session runner:** `watch.py` (`launch()`), `followups.py` and `../daily-digest/sessions.py` (`paseo()`) start and archive sessions through Paseo's command line. With another runner, replace those calls.
- **Task board:** steps 3 and 5 of job.md, and its "When James replies" section, use the `relationship_hub` tools. Point them at your own board, or have the session list commitments without capturing them.
- **Mail:** step 3 searches email read-only with `mail_search`. Use your own mail tool, or drop that lookup.
- **Scheduler:** `register-task.ps1` uses Windows Task Scheduler. On a Mac, run `watch.py` every 5 minutes with launchd or cron.
- **Paths and names:** the Python and script paths in step 9 of job.md, which point at my own checkout, `C:\Users\you`, and "James" throughout the prompts.
