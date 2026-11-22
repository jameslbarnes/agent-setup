"""Offline check of normalize -> store -> pending -> apply -> render with a synthetic API page."""
import json
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import bookmarks as b  # noqa: E402

root = Path(tempfile.mkdtemp(prefix="xbm-test-"))
b.RESEARCH = root / "research"
b.SOURCES = b.RESEARCH / "sources"
b.STORE = b.SOURCES / "bookmarks.jsonl"
b.SUMMARIES = b.SOURCES / "summaries.jsonl"
b.CATALOG = b.RESEARCH / "catalog.md"
b.STATE = root / "state"
b.FETCH_LOG = b.STATE / "fetch-log.jsonl"
b.SHAPE = b.STATE / "api-shape.json"
b.TRIAGE = b.SOURCES / "triage.jsonl"
b.PEOPLE = b.SOURCES / "people.jsonl"
b.CONTACTS = b.STATE / "contacts.json"
b.SHARE_BRIEF = root / "share_brief.md"  # stand-in: the real sharing prompt isn't in this copy
b.SHARE_BRIEF.write_text("Shares for {{DATE}}:\n{{SHARES}}\nTool: {{TOOL}}\n", encoding="utf-8")
b.STATE.mkdir(parents=True, exist_ok=True)
b.CONTACTS.write_text(json.dumps({"people": [
    {"id": "p1", "name": "Ada Lovelace", "company": "Engines", "projects": [{"project": "Clients", "stage": "REPLIED", "context": "angel"}]},
    {"id": "p2", "name": "Grace Hopper", "projects": [{"project": "Friends", "stage": "READY"}]}]}), encoding="utf-8")
b.AREAS_DIR = root / "areas"
b.AREAS_FILE = root / "areas.json"
(b.AREAS_DIR / "music").mkdir(parents=True)
(b.AREAS_DIR / "music" / "STATE.md").write_text("# Music\n\n## Log\n<!-- agents append here -->\n", encoding="utf-8")
b.AREAS_FILE.write_text(json.dumps([{"id": "music", "name": "Music", "covers": "the songs"}, {"id": "garden", "name": "Garden"}]), encoding="utf-8")

PAGES = [
    {
        "data": [
            {"id": "300", "author_id": "u1", "created_at": "2026-11-06T10:00:00.000Z", "text": "Short text https://t.co/a",
             "note_tweet": {"text": "Long note text with [brackets] and <tags> https://t.co/a",
                            "entities": {"urls": [{"url": "https://t.co/a", "expanded_url": "https://example.com/paper",
                                                   "title": "A paper", "description": "About things"}]}},
             "entities": {"urls": [{"url": "https://t.co/a", "expanded_url": "https://example.com/paper"},
                                   {"url": "https://t.co/q", "expanded_url": "https://x.com/u2/status/200"}]},
             "referenced_tweets": [{"type": "quoted", "id": "200"}],
             "attachments": {"media_keys": ["m1"]}},
            {"id": "250", "author_id": "u2", "created_at": "2026-10-01T10:00:00.000Z", "text": "https://t.co/art",
             "entities": {"urls": [{"url": "https://t.co/art", "expanded_url": "http://x.com/i/article/77",
                                    "unwound_url": "https://x.com/i/article/77"}]},
             "article": {"title": "An article", "preview_text": "Preview", "plain_text": "Full article text with a line separator",
                         "entities": {"urls": [{"text": "https://github.com/o/r"}, {"text": "agent.py"}]}}},
        ],
        "includes": {
            "users": [{"id": "u1", "username": "alice", "name": "Alice"}, {"id": "u2", "username": "bob", "name": "Bob"}],
            "tweets": [{"id": "200", "author_id": "u2", "text": "Quoted text https://t.co/z",
                        "entities": {"urls": [{"url": "https://t.co/z", "expanded_url": "https://github.com/o/r"}]}}],
            "media": [{"media_key": "m1", "type": "photo", "url": "https://pbs.twimg.com/x.jpg", "alt_text": "a chart"}],
        },
        "meta": {"next_token": "T2"},
    },
    {"data": [{"id": "100", "author_id": "u2", "created_at": "2026-10-01T09:00:00.000Z", "text": "Oldest"}],
     "includes": {"users": [{"id": "u2", "username": "bob", "name": "Bob"}]}, "meta": {}},
]


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.rate = {}
        self.pages = list(PAGES)

    def get(self, path, params):
        self.calls += 1
        assert path == f"/2/users/{b.ACCOUNT_ID}/bookmarks", path
        return self.pages.pop(0)


b.Client = FakeClient
ns = types.SimpleNamespace
b.cmd_fetch(ns(full=True, page_size=0, max_pages=60))
store = b.read_jsonl(b.STORE)
assert [r["id"] for r in sorted(store.values(), key=lambda r: r["seen_order"])] == ["100", "250", "300"], store.keys()
top = store["300"]
assert top["text"].startswith("Long note"), top["text"]
assert top["quoted"]["author"]["username"] == "bob" and top["quoted"]["links"][0]["url"] == "https://github.com/o/r"
assert [l["url"] for l in top["links"]] == ["https://example.com/paper"], top["links"]
assert top["media"][0]["alt_text"] == "a chart"
assert top["url"] == "https://x.com/alice/status/300"
art = store["250"]
assert art["article"]["title"] == "An article" and art["article"]["links"] == ["https://github.com/o/r"], art["article"]
assert art["links"] == [], art["links"]
b.cmd_rebuild(ns())
assert b.read_jsonl(b.STORE)["250"]["article"]["plain_text"].endswith("line separator")

# A daily run that finds one new bookmark on top of the saved ones.
PAGES[:] = [{"data": [{"id": "400", "author_id": "u1", "created_at": "2026-11-07T08:00:00.000Z", "text": "New one"},
                      {"id": "300", "author_id": "u1", "created_at": "2026-11-06T10:00:00.000Z", "text": "x"}],
             "includes": {"users": [{"id": "u1", "username": "alice", "name": "Alice"}]}, "meta": {"next_token": "T3"}}]
b.cmd_fetch(ns(full=False, page_size=0, max_pages=60))
store = b.read_jsonl(b.STORE)
assert store["400"]["seen_order"] == 4 and len(store) == 4

out = root / "pending.json"
b.cmd_pending(ns(out=str(out), offset=0, limit=0))
pending = json.loads(out.read_text(encoding="utf-8"))
assert [i["id"] for i in pending["items"]] == ["400", "300", "250", "100"], pending["items"]
summaries = root / "summaries.json"
summaries.write_text(json.dumps([
    {"id": "400", "summary": "Alice's new post.", "topics": ["AI Agents"], "kind": "post"},
    {"id": "300", "summary": "A paper about things, quoting Bob's repo.", "topics": ["research", "ai agents"], "kind": "paper",
     "links_read": ["https://example.com/paper"], "why": "Relevant to Music."},
    {"id": "999", "summary": "unknown", "topics": ["x"]},
    {"id": "250", "summary": "", "topics": ["x"]},
]), encoding="utf-8")
b.cmd_apply(ns(files=[str(summaries)]))
catalog = b.CATALOG.read_text(encoding="utf-8")
assert "ai agents (2)" in catalog and "Not summarized yet" in catalog and "\\[brackets\\]" not in catalog
assert "X Article: An article." in catalog
assert pending["items"][2]["article"]["title"] == "An article"
assert catalog.index("Posted 2026-11") < catalog.index("Posted 2026-10")
assert catalog.index("status/400") < catalog.index("status/300")

# Triage: work list, validation, queue, launch (dry run), progress, decisions, area log, reading list.
summaries.write_text(json.dumps([{"id": i, "summary": f"Summary of {i}. More.", "topics": ["ai agents"]} for i in ("250", "100")]), encoding="utf-8")
b.cmd_apply(ns(files=[str(summaries)]))
work = root / "triage-in.json"
b.cmd_pending_triage(ns(out=str(work), offset=0, limit=0))
work_list = json.loads(work.read_text(encoding="utf-8"))
assert {a["id"] for a in work_list["areas"]} == {"music", "garden"} and len(work_list["items"]) == 4
triage_file = root / "triage.json"
triage_file.write_text(json.dumps([
    {"id": "400", "outcome": "act", "area": "music", "priority": 5, "reason": "r", "question": "Could it replace the gate?",
     "people": [{"person": "p1", "why": "Her fund backs voice tools.", "action": "share"},
                {"person": "nobody", "why": "x", "action": "share"}]},
    {"id": "300", "outcome": "deadline", "area": "none", "priority": 4, "reason": "r", "question": "Draft it", "deadline": "2999-01-01"},
    {"id": "250", "outcome": "reference", "area": "music", "priority": 3, "reason": "r"},
    {"id": "100", "outcome": "read", "area": "none", "priority": 2, "reason": "r", "minutes": 12},
    {"id": "999", "outcome": "act", "area": "music", "question": "q"},
    {"id": "250", "outcome": "reference", "area": "none"},
    {"id": "400", "outcome": "act", "area": "nowhere", "question": "q"},
]), encoding="utf-8")
b.cmd_triage_apply(ns(files=[str(triage_file)]))
triage = b.read_jsonl(b.TRIAGE)
assert triage["400"]["status"] == "queued" and triage["250"]["status"] == "filed" and triage["100"]["status"] == "unlisted"
assert triage["300"]["deadline"] == "2999-01-01"
deadlines, acts = b._queue(triage, b.read_jsonl(b.STORE))
assert [t["id"] for t in deadlines] == ["300"] and [t["id"] for t in acts] == ["400"]
b.cmd_launch(ns(id="400", dry_run=True, force=False))
b.cmd_mark(ns(id="400", status="done", report=r"C:\x\report.md", note=None))
b.cmd_decide(ns(id="400", decision="no", note="not now"))
b.cmd_triage_apply(ns(files=[str(triage_file)]))  # re-triage keeps progress and decisions
triage = b.read_jsonl(b.TRIAGE)
assert triage["400"]["status"] == "done" and triage["400"]["decision"] == "no"
assert b.read_jsonl(b.TRIAGE)["400"]["decision_note"] == "not now"
again = root / "triage-in-2.json"
b.cmd_pending_triage(ns(out=str(again), offset=0, limit=0))
assert json.loads(again.read_text(encoding="utf-8"))["recent_decisions"][0]["decision"] == "no"
b.cmd_reading_list(ns(limit=5, mark=True))
assert b.read_jsonl(b.TRIAGE)["100"]["status"] == "listed"

# People: matches from triage and from people-apply, the share session (dry run) and its outcome.
assert work_list["contacts"][0]["name"] == "Ada Lovelace" and "email" not in json.dumps(work_list["contacts"])
people = b.read_jsonl(b.PEOPLE)
assert [m["person"] for m in people["400"]["people"]] == ["p1"] and people["400"]["people"][0]["status"] == "suggested"
people_file = root / "people.json"
people_file.write_text(json.dumps([{"id": "250", "people": [{"person": "p2", "why": "She asked about harnesses.", "action": "mention"},
                                                            {"person": "p1", "why": "x", "action": "maybe"}]}]), encoding="utf-8")
b.cmd_people_apply(ns(files=[str(people_file)]))
people = b.read_jsonl(b.PEOPLE)
assert people["250"]["people"] == [{"person": "p2", "name": "Grace Hopper", "why": "She asked about harnesses.", "action": "mention"}]
b.cmd_launch_share(ns(limit=5, dry_run=True))
b.cmd_share_mark(ns(id="400", person="p1", status="shared"))
assert b.read_jsonl(b.PEOPLE)["400"]["people"][0]["status"] == "shared"
b.cmd_triage_apply(ns(files=[str(triage_file)]))  # re-triage keeps the share outcome
assert b.read_jsonl(b.PEOPLE)["400"]["people"][0]["status"] == "shared"
catalog = b.CATALOG.read_text(encoding="utf-8")
assert "_Research:_ Could it replace the gate? (done, James: no)." in catalog and "_Deadline 2999-01-01:_" in catalog
assert "_Worth your time_ (about 12 min)." in catalog and "Outcomes: act 1, deadline 1, reference 1, read 1." in catalog
assert "_Relevant to:_ Ada Lovelace (worth sharing, shared): Her fund backs voice tools." in catalog
assert "_Relevant to:_ Grace Hopper: She asked about harnesses." in catalog

# Area notes are read-only for this system: nothing above may have written to them.
assert (b.AREAS_DIR / "music" / "STATE.md").read_text(encoding="utf-8") == "# Music\n\n## Log\n<!-- agents append here -->\n"
assert not hasattr(b, "cmd_area_log")
print("OK", root)
