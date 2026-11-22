# X bookmarks → research library

Every morning, a scheduled agent session files each new bookmark from my X account into a research folder. Each bookmark gets a summary, a line in that day's file and the running themes report, and exactly one outcome, so my attention goes only to decisions. The session follows [job.md](job.md).

| Outcome | What happens | How it reaches me |
|---|---|---|
| act | `bookmarks.py launch` starts a top-level Paseo research session from [research_brief.md](research_brief.md). It answers the triage question from primary sources and earlier reports, runs only free offline checks, writes a report and stops at one decision. | The morning message links the session. |
| deadline | The same kind of session drafts the deliverable (`draft.md`, never submitted) and adds a task due on the deadline. | The task and the morning message. |
| reference | Filed with its area tag. Agents working in that area find it with `bookmarks_search area=<area>`. | Only inside the work. |
| read | `bookmarks.py reading-list --mark`, on Sundays. | The Sunday message. |
| keep | Filed and searchable. | Never. |

Limits:

- at most 2 act sessions a day, plus every deadline due within 14 days;
- act items not researched within 30 days become reference;
- the decisions I give in a session are recorded with `bookmarks.py decide`, and triage reads them to calibrate;
- research sessions may run only free, offline checks, and must propose anything that costs money.

## Files

- `bookmarks.py` is the command-line tool the session runs. Its docstring lists every command:
  - fetch and summarize: `fetch`, `pending`, `apply`, `render`, `rebuild`, `read-link` and `status`;
  - triage: `pending-triage` and `triage-apply`;
  - outcomes: `queue`, `launch`, `mark`, `decide` and `reading-list`.
- `job.md` holds the daily session's instructions, including how to summarize and how to triage.
- `research_brief.md` is the prompt each research session starts from.
- `xapi.py` is a minimal X API v2 client. It only ever makes GET requests.
- `mcp_server.py` is a read-only MCP server named "bookmarks", standard library only. Its tools are `bookmarks_search` (words or "phrases", plus optional `topic`, `author` and `since`), `bookmarks_recent`, `bookmarks_get` (by id or URL) and `bookmarks_topics`. It loads the data on the first call and reloads it when the files change. Register it with `claude mcp add --scope user bookmarks -- <python> -I <path>/mcp_server.py`.
- `test_offline.py` checks the whole pipeline offline, against a made-up API page. Run it after changing `bookmarks.py`.
- `test_mcp_idle.py` measures how much memory the MCP server uses once it has started and is waiting.

Matching bookmarks to my contacts, and drafting notes to share posts with them, isn't in this copy. The contact export and the sharing prompt are left out, and job.md no longer asks for matches. The code for it (`people-apply`, `launch-share`, `share-mark` and the MCP server's `person=` filter) is still in `bookmarks.py` and `mcp_server.py`, and does nothing without a contacts file.

## X access

`xapi.py` gets its `Authorization` header from a separate login helper, `~/.config/x-mcp/headers.ps1`, which isn't included. That helper keeps an OAuth 2.0 user token encrypted with Windows DPAPI and renews it with the refresh token. Replace `auth_header()` with your own way of getting a user token with the `bookmark.read` scope.

- **Requests:** only `GET /2/users/<your user id>/bookmarks`. Nothing is ever written to X.
- **Renewal:** user tokens last about two hours, and renewing one needs the app's Client Secret.
- **Cost:** X bills bookmark reads as an Owned Read at $0.001 per post when the app belongs to the same account. A daily run reads one page of 10, and more only when there are more than 10 new bookmarks. X may also bill the authors and quoted posts each page returns at its standard rates; I haven't confirmed that.
- **Rate limit:** 180 requests per 15 minutes.

Things that break the login:

- **A second sign-in for the same app.** X keeps one live OAuth 2.0 login per user per app, so authorizing the app anywhere else invalidates the saved one. Keep one token store and have every tool read it.
- **Regenerating the Client Secret.** Renewals fail until the new secret is imported.
- **The refresh token running out.** X documents refresh tokens as single-use and lasting about six months.
- **Disconnecting the app** under X → Settings → Connected apps.
- **Falling back to OAuth 1.0a.** X retires it on 2027-01-31, and tokens converted from it don't include `bookmark.read`.

If the login breaks, the daily session says so in its morning message. If the Client Secret is missing, import it again. If X rejected the login, it needs a fresh OAuth 2.0 approval of the same app with the same scopes, signed in to X in a browser.

## Data

- `sources/bookmarks.jsonl` in the research folder holds one normalized record per bookmark, with the raw API objects under `raw`. `seen_order` is the order bookmarks were made, higher meaning later, because the API doesn't say when something was bookmarked. `first_seen` is the date the job first saw it.
- Raw API pages, each run's `pending.json` and `summaries.json`, and `fetch-log.jsonl` are kept in `%LOCALAPPDATA%\agent-setup\x-bookmarks\`.
- `bookmarks.py fetch --full` pages through everything again and refreshes `last_seen`, without deleting anything.

## What to change for your setup

- **Paths:** `RESEARCH`, `STATE`, `LIBRARY`, `AREAS_DIR` and `AREAS_FILE` at the top of `bookmarks.py`, `FOLDER` in `mcp_server.py`, and the paths in job.md and research_brief.md.
- **Account:** `ACCOUNT_ID` (your numeric X user id) and `ACCOUNT` in `bookmarks.py`.
- **Areas:** triage files each bookmark under one of your work areas, which `pending-triage` reads from `AREAS_FILE` and the notes in `AREAS_DIR`. Also rewrite the short description of your work under **why** in job.md's summary guide.
- **Schedule:** in my setup it's a Paseo schedule that starts a session with job.md every morning. Any scheduler that starts an agent session with that prompt works.
- **Research library:** research sessions write their reports in the format of my research library, which isn't included. Give your agent a folder and a short format to follow.
