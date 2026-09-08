#!/usr/bin/env python3
"""
PROTOTYPE. Throwaway by construction: no tests, no abstractions, no persistence,
no error handling beyond what makes it run. Not to be merged.

THE ONE QUESTION THIS EXISTS TO ANSWER
--------------------------------------
Is the Orbit node/edge/evidence model (spec 0001, sections 5-10) small enough to
build, and rich enough to describe a real estate, without deciding what anything
means?

Spec: orbit/specs/0001-observation-foundation.md

Usage:
    python3 orbit_prototype.py <command> [--roots PATH ...] [--json] [args]

Commands: estate orient boot cold-start would-load inbound outbound trace
          links unmatched outside unpointed dupes blindspots
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

DETECTORS = "proto-0"

# ----------------------------------------------------------------- model ----

NODES = {}
EDGES = []
LEDGER = []
BLIND = []


def ev(cls, source, locator):
    return {"class": cls, "source": source, "locator": locator, "detector": DETECTORS}


def node(nid, kind, attrs, evidence):
    if nid not in NODES:
        NODES[nid] = {"id": nid, "kind": kind, "attrs": attrs,
                      "roles": [], "evidence": evidence}
    return NODES[nid]


def edge(frm, to, kind, subtype, evidence):
    EDGES.append({"from": frm, "to": to, "kind": kind,
                  "subtype": subtype, "evidence": evidence})


def role(nid, name, evidence):
    if nid in NODES:
        NODES[nid]["roles"].append({"role": name, "evidence": evidence})


def blind(what, why):
    BLIND.append({"unknown": what, "why": why,
                  "evidence": ev("UNKNOWN", "runtime", "-")})


# ------------------------------------------------------------ collectors ----

SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
        "build", ".mypy_cache", ".pytest_cache", ".ruff_cache"}

TEXTY = {".md", ".txt", ".py", ".js", ".mjs", ".ts", ".tsx", ".json", ".toml",
         ".yaml", ".yml", ".sh", ".bash", ".cfg", ".ini", ".rules", ".env"}


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo] + list(args),
                       capture_output=True, text=True)
    return p.stdout.strip(), p.returncode


def find_repos(roots):
    found = []
    for root in roots:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if ".git" in dirnames or ".git" in filenames:
                found.append(dirpath)
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP)
    return found


def collect_repo(repo):
    nid = "repo:" + repo
    head, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    sha, _ = git(repo, "rev-parse", "HEAD")
    remotes, _ = git(repo, "remote", "-v")
    branches, _ = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads")
    remote_branches, _ = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/remotes")
    status, _ = git(repo, "status", "--porcelain")
    worktrees, _ = git(repo, "worktree", "list", "--porcelain")
    ab, rc = git(repo, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")

    fetch_head = os.path.join(repo, ".git", "FETCH_HEAD")
    last_fetch = None
    if os.path.isfile(fetch_head):
        last_fetch = int(os.path.getmtime(fetch_head))

    dirty = [l for l in status.splitlines() if l]
    attrs = {
        "path": repo,
        "head_ref": head if head != "HEAD" else None,
        "detached": head == "HEAD",
        "head_sha": sha,
        "remotes": sorted(set(l.split("\t")[1].split(" ")[0]
                              for l in remotes.splitlines() if "\t" in l)),
        "local_branches": branches.splitlines(),
        "remote_tracking_branches": remote_branches.splitlines(),
        "dirty_entries": len(dirty),
        "untracked_entries": len([l for l in dirty if l.startswith("??")]),
        "ahead_behind": (ab.split() if rc == 0 and ab else None),
        "last_fetch_epoch": last_fetch,
        "worktrees": [l.split(" ", 1)[1] for l in worktrees.splitlines()
                      if l.startswith("worktree ")],
        "submodules_declared": os.path.isfile(os.path.join(repo, ".gitmodules")),
    }
    attr_evidence = {
        "head_sha": ev("OBSERVED", "git", "git -C %s rev-parse HEAD" % repo),
        "local_branches": ev("OBSERVED", "git", "git -C %s for-each-ref refs/heads" % repo),
        "ahead_behind": ev("OBSERVED", "git",
                           "git -C %s rev-list --left-right --count HEAD...@{upstream}"
                           " (as of last fetch, never fetched by orbit)" % repo),
        "submodules_declared": ev("DECLARED", "config", os.path.join(repo, ".gitmodules")),
    }
    n = node(nid, "Scope", attrs, ev("OBSERVED", "filesystem", os.path.join(repo, ".git")))
    n["attrs_kind"] = "repository"
    n["attr_evidence"] = attr_evidence

    if attrs["local_branches"]:
        blind("content on branches other than %r in %s" % (attrs["head_ref"], repo),
              "orbit reads only the checked-out tree; entering another branch would "
              "require a checkout")
    return nid


def read_text(path):
    try:
        if os.path.getsize(path) > 2_000_000:
            return None
        with open(path, "rb") as f:
            raw = f.read()
        if b"\x00" in raw[:4096]:
            return None
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return None


def collect_files(repo, repo_nid):
    out = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP)
        if dirpath != repo and (os.path.isdir(os.path.join(dirpath, ".git"))
                                or os.path.isfile(os.path.join(dirpath, ".git"))):
            dirnames[:] = []          # a nested repo collects itself
            continue
        for fn in sorted(filenames):
            path = os.path.join(dirpath, fn)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            nid = "file:" + path
            with open(path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()[:16]
            node(nid, "File",
                 {"path": path, "rel": os.path.relpath(path, repo), "bytes": size,
                  "sha256_16": h, "executable": os.access(path, os.X_OK),
                  "repo": repo},
                 ev("OBSERVED", "filesystem", path))
            edge(repo_nid, nid, "contains", "filesystem-walk",
                 ev("OBSERVED", "filesystem", path))
            out.append(path)
    return out


# -------------------------------------------------------------- detectors ---

INSTRUCTION_NAMES = {"CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules",
                     "copilot-instructions.md", ".windsurfrules"}
GEN_MARKER = re.compile(r"(DO NOT EDIT|@generated|Generated by[: ]+([^\n]+))", re.I)
TEST_PATH = re.compile(r"(^|/)(tests?|spec)/|(^|/)test_[^/]+\.py$|\.(test|spec)\.[jt]sx?$")
ADR_PATH = re.compile(r"(^|/)(adr|adrs|decisions|docs/decisions)(/|$)", re.I)


def frontmatter(text):
    if not text.startswith("---"):
        return None, 0
    end = text.find("\n---", 3)
    if end < 0:
        return None, 0
    block = text[3:end]
    fields = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields, len(text[:end + 4].encode())


def detect_roles(path, text, repo):
    nid = "file:" + path
    base = os.path.basename(path)
    rel = os.path.relpath(path, repo)

    if base in INSTRUCTION_NAMES:
        role(nid, "instruction-surface",
             ev("OBSERVED", "filesystem", "%s (filename convention)" % path))
    if base == "SKILL.md":
        fm, _ = frontmatter(text or "")
        if fm and "name" in fm and "description" in fm:
            role(nid, "skill-package", ev("OBSERVED", "frontmatter", path + ":1"))
    if "/.claude/agents/" in path.replace(os.sep, "/"):
        role(nid, "agent-definition", ev("OBSERVED", "filesystem", path))
    if "/.claude/commands/" in path.replace(os.sep, "/"):
        role(nid, "command-definition", ev("OBSERVED", "filesystem", path))
    if os.access(path, os.X_OK) or (text or "").startswith("#!"):
        role(nid, "executable", ev("OBSERVED", "file-content", path + ":1"))
    if base in {"settings.json", "settings.local.json", "pyproject.toml",
                "package.json", "orbit.toml", ".gitmodules"}:
        role(nid, "config", ev("OBSERVED", "filesystem", path))
    if TEST_PATH.search(rel.replace(os.sep, "/")):
        role(nid, "test", ev("INFERRED", "filesystem",
                             "%s (path matches a test convention)" % path))
    if ADR_PATH.search(rel.replace(os.sep, "/")) or base == "CHANGELOG.md":
        role(nid, "decision-surface", ev("INFERRED", "filesystem", path))
    if text:
        m = GEN_MARKER.search(text[:800])
        if m:
            role(nid, "generated-artifact",
                 ev("DECLARED", "file-header",
                    "%s:%d" % (path, text[:m.start()].count("\n") + 1)))
            raw = (m.group(2) or "").strip()
            producer = raw.split()[0].strip(".,`'\"") if raw else ""
            if producer:
                return producer, text[:m.start()].count("\n") + 1
    return None, None


MD_LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)>\s]+)")
PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)")
JS_IMPORT = re.compile(r"""(?:from|require\()\s*['"]([^'"]+)['"]""")
# The token must start at a real boundary. An earlier version put a backtick in
# a negative lookbehind, which did not skip inline code -- it shifted the match
# start into the middle of the token and produced ~1300 truncated phantom
# targets that then reported as "no indexed target match". A leading "/" is
# excluded from the boundary class so URL paths are not re-matched as bare ones.
BARE_PATH = re.compile(
    r"""(?:^|[\s`'"(<\[])((?:\.{0,2}/)?(?:[\w.\-]+/)+[\w.\-]+\.[A-Za-z0-9]{1,6})""")
SUPERSEDES = re.compile(r"^\s*(supersedes|replaces|superseded[_ -]by)\s*:\s*(\S+)", re.I)


def find_references(path, text):
    """(subtype, target, line, in_fence) tuples."""
    hits = []
    fence = False
    for i, line in enumerate(text.splitlines(), 1):
        st = line.strip()
        if st.startswith("```") or st.startswith("~~~"):
            fence = not fence
            continue
        for m in MD_LINK.finditer(line):
            hits.append(("markdown-link", m.group(1), i, fence))
        for m in JS_IMPORT.finditer(line):
            hits.append(("import-statement", m.group(1), i, fence))
        m = PY_IMPORT.match(line)
        if m:
            hits.append(("import-statement", m.group(1), i, fence))
        m = SUPERSEDES.match(line)
        if m:
            hits.append(("supersedes-claim", m.group(2), i, fence))
        for m in BARE_PATH.finditer(line):
            t = m.group(1)
            if not any(t == h[1] for h in hits if h[2] == i):
                hits.append(("bare-path-literal", t, i, fence))
    return hits


def inside_roots(path, roots):
    p = os.path.abspath(path)
    return any(p == r or p.startswith(r.rstrip(os.sep) + os.sep) for r in roots)


SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://|^mailto:|^#")


def resolve(target, from_path, repo, roots):
    if SCHEME.match(target):
        return ("ext", "unresolvable-scheme", target)
    t = target.split("#")[0].split("?")[0]
    if not t or t in {".", "./"}:
        return None
    cands = []
    if t.startswith("/"):
        cands.append(t)
    else:
        cands.append(os.path.normpath(os.path.join(os.path.dirname(from_path), t)))
        cands.append(os.path.normpath(os.path.join(repo, t)))
    for c in cands:
        if os.path.isfile(c):
            return ("file", None, c) if inside_roots(c, roots) \
                else ("ext", "outside-indexed-roots", c)
        if os.path.isdir(c):
            return ("dir", None, c) if inside_roots(c, roots) \
                else ("ext", "outside-indexed-roots", c)
    return ("ext", "no-indexed-target-match", target)


def ext_node(kind, addr):
    nid = "ext:%s:%s" % (kind, addr)
    node(nid, "ExternalRef", {"address": addr, "sub_kind": kind},
         ev("OBSERVED", "file-content", addr))
    return nid


# ----------------------------------------------------------- load ledger ----

def ledger_row(mechanism, source, activation, trigger, scope, inheritance,
               nbytes, lifetime, revocable, evidence, consumer_evidence=None):
    LEDGER.append({
        "mechanism": mechanism, "source": source, "activation": activation,
        "trigger": trigger, "scope": scope, "inheritance": inheritance,
        "bytes": nbytes,
        "est_tokens": (None if nbytes is None else round(nbytes / 4)),
        "est_tokens_evidence": ev("INFERRED", "file-content", "bytes/4 heuristic"),
        "lifetime": lifetime, "revocable": revocable,
        "consumer_evidence": consumer_evidence, "evidence": evidence,
    })


def build_ledger(repo, files, texts):
    rp = repo.rstrip(os.sep)
    for path in files:
        base = os.path.basename(path)
        rel = os.path.relpath(path, repo).replace(os.sep, "/")
        nb = NODES["file:" + path]["attrs"]["bytes"]

        if base in INSTRUCTION_NAMES:
            top = os.path.dirname(path).rstrip(os.sep) == rp
            ledger_row(
                "instruction-surface", path,
                "repo-entry" if top else "path-scoped",
                "session enters %s" % (repo if top else os.path.dirname(path)),
                repo if top else os.path.dirname(path),
                "adds to parent" if not top else "root",
                nb, "whole session", "no",
                ev("OBSERVED", "filesystem", path))

        if base == "SKILL.md":
            fm, fm_bytes = frontmatter(texts.get(path) or "")
            if fm and "description" in fm:
                ledger_row("skill-description", path, "boot",
                           "every session, for every installed skill",
                           "global", "n/a", fm_bytes, "whole session", "no",
                           ev("OBSERVED", "frontmatter", path + ":1"))
                ledger_row("skill-body", path, "explicit-invocation",
                           "skill %r invoked" % fm.get("name", "?"),
                           os.path.dirname(path), "n/a",
                           nb - fm_bytes, "rest of session", "no",
                           ev("OBSERVED", "filesystem", path))

        if "/.claude/agents/" in path.replace(os.sep, "/"):
            fm, fm_bytes = frontmatter(texts.get(path) or "")
            ledger_row("agent-description", path, "boot", "every session",
                       "global", "n/a", fm_bytes or 0, "whole session", "no",
                       ev("OBSERVED", "frontmatter", path + ":1"))
            ledger_row("agent-body", path, "agent-scoped", "agent spawned",
                       "that subagent only", "n/a", nb - (fm_bytes or 0),
                       "that subagent", "YES - subagent context ends",
                       ev("OBSERVED", "filesystem", path))

        if "/.claude/commands/" in path.replace(os.sep, "/"):
            ledger_row("slash-command", path, "explicit-invocation",
                       "/%s typed" % os.path.splitext(base)[0], repo, "n/a",
                       nb, "rest of session", "no",
                       ev("OBSERVED", "filesystem", path))

        if base in {"settings.json", "settings.local.json"} and "/.claude/" in \
                path.replace(os.sep, "/"):
            try:
                cfg = json.loads(texts.get(path) or "{}")
            except ValueError:
                continue
            text = texts.get(path) or ""
            for event, groups in (cfg.get("hooks") or {}).items():
                for g in groups:
                    matcher = g.get("matcher", "*")
                    for h in g.get("hooks", []):
                        cmd = h.get("command", "")
                        line = next((i for i, l in enumerate(text.splitlines(), 1)
                                     if cmd and cmd in l), 1)
                        ledger_row(
                            "hook:" + event, path, "boot" if event == "SessionStart"
                            else "event",
                            'matcher %r, command %r' % (matcher, cmd),
                            repo, "n/a", None, "whole session", "no",
                            ev("OBSERVED", "hook-definition", "%s:%d" % (path, line)))
                        blind("payload of hook %s -> %r" % (event, cmd),
                              "hook output is produced at runtime; orbit does not run it")
                        tgt = resolve(cmd.split()[0] if cmd else "", path, repo, ROOTS)
                        if tgt and tgt[0] == "file":
                            edge("file:" + path, "file:" + tgt[2], "invokes",
                                 "hook-command",
                                 ev("OBSERVED", "hook-definition", "%s:%d" % (path, line)))
                            role("file:" + tgt[2], "hook-target",
                                 ev("OBSERVED", "hook-definition", "%s:%d" % (path, line)))
                        elif tgt and tgt[0] == "ext":
                            edge("file:" + path, ext_node(tgt[1], tgt[2]), "invokes",
                                 "hook-command",
                                 ev("OBSERVED", "hook-definition", "%s:%d" % (path, line)))

    blind("MCP server instructions loaded at boot",
          "supplied by the client at runtime and sourced outside the estate")
    blind("user-global instruction surfaces (e.g. ~/.claude/CLAUDE.md)",
          "outside the indexed roots unless a root is widened to include them")


# ---------------------------------------------------------------- driver ----

ROOTS = []


def observe(roots):
    global ROOTS
    ROOTS = [os.path.abspath(r) for r in roots]
    for repo in find_repos(ROOTS):
        rnid = collect_repo(repo)
        files = collect_files(repo, rnid)
        texts = {}
        producers = {}
        for path in files:
            ext = os.path.splitext(path)[1].lower()
            text = read_text(path) if (ext in TEXTY or ext == "") else None
            texts[path] = text
            prod, line = detect_roles(path, text, repo)
            if prod:
                producers[path] = (prod, line)
        for path, text in texts.items():
            if not text:
                continue
            for subtype, target, line, fence in find_references(path, text):
                r = resolve(target, path, repo, ROOTS)
                if not r:
                    continue
                kind, sub, addr = r
                if kind == "file":
                    to = "file:" + addr
                    if to not in NODES:
                        continue
                elif kind == "dir":
                    to = "dir:" + addr
                    node(to, "Scope", {"path": addr}, ev("OBSERVED", "filesystem", addr))
                    NODES[to]["attrs_kind"] = "directory"
                else:
                    to = ext_node(sub, addr)
                e = ev("OBSERVED", "file-content", "%s:%d" % (path, line))
                e["in_code_fence"] = fence
                edge("file:" + path, to, "references", subtype, e)
        for path, (prod, line) in producers.items():
            r = resolve(prod, path, repo, ROOTS)
            if r and r[0] == "file":
                edge("file:" + r[2], "file:" + path, "produces", "artifact-header",
                     ev("DECLARED", "file-header", "%s:%d" % (path, line)))
                role("file:" + r[2], "generator",
                     ev("DECLARED", "file-header", "%s:%d" % (path, line)))
        build_ledger(repo, files, texts)

    by_hash = defaultdict(list)
    for n in NODES.values():
        if n["kind"] == "File":
            by_hash[n["attrs"]["sha256_16"]].append(n["id"])
    for h, ids in by_hash.items():
        if len(ids) > 1:
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    edge(ids[i], ids[j], "identical-bytes", "sha256",
                         ev("OBSERVED", "hash", h))


def boundary():
    return {"indexed_roots": ROOTS, "detector_set": DETECTORS,
            "excluded_dir_names": sorted(SKIP),
            "note": "only the checked-out tree of each repository was read"}


# --------------------------------------------------------------- queries ----

def q_estate():
    return [dict(n, attrs=n["attrs"]) for n in NODES.values()
            if n["kind"] == "Scope" and n.get("attrs_kind") == "repository"]


def q_boot(frm=None):
    rows = [r for r in LEDGER if r["activation"] in ("boot", "repo-entry")]
    if frm:
        frm = os.path.abspath(frm)
        rows = [r for r in rows if r["activation"] == "boot"
                or r["scope"] == frm or frm.startswith(str(r["scope"]))]
    return rows


def q_cold_start(frm=None):
    rows = q_boot(frm)
    known = sum(r["bytes"] or 0 for r in rows)
    unknown = [r for r in rows if r["bytes"] is None]
    return {"bytes_known": known, "est_tokens_known": round(known / 4),
            "unmeasurable_mechanisms": [r["mechanism"] for r in unknown],
            "unmeasurable_count": len(unknown),
            "rows": rows,
            "warning": "mechanisms with runtime payloads count as UNKNOWN, never zero"}


def q_would_load(selector):
    return [r for r in LEDGER
            if r["activation"] not in ("boot", "repo-entry")
            and (selector.lower() in str(r["source"]).lower()
                 or selector.lower() in str(r["trigger"]).lower()
                 or selector.lower() in r["mechanism"].lower())]


def q_inbound(path):
    nid = "file:" + os.path.abspath(path)
    return [e for e in EDGES if e["to"] == nid]


def q_outbound(path):
    nid = "file:" + os.path.abspath(path)
    return [e for e in EDGES if e["from"] == nid]


def q_trace(path):
    nid = "file:" + os.path.abspath(path)
    return {"produced_by": [e for e in EDGES if e["to"] == nid and e["kind"] == "produces"],
            "produces": [e for e in EDGES if e["from"] == nid and e["kind"] == "produces"],
            "referenced_by": [e for e in EDGES if e["to"] == nid and e["kind"] == "references"],
            "invoked_by": [e for e in EDGES if e["to"] == nid and e["kind"] == "invokes"]}


def q_links():
    out = []
    for e in EDGES:
        if e["kind"] != "references":
            continue
        a = NODES.get(e["from"], {}).get("attrs", {}).get("repo")
        b = NODES.get(e["to"], {}).get("attrs", {}).get("repo")
        if a and b and a != b:
            out.append(e)
    return out


def q_unmatched():
    ids = {n["id"] for n in NODES.values()
           if n["kind"] == "ExternalRef" and n["attrs"]["sub_kind"] == "no-indexed-target-match"}
    return [e for e in EDGES if e["to"] in ids]


def q_outside():
    ids = {n["id"] for n in NODES.values()
           if n["kind"] == "ExternalRef" and n["attrs"]["sub_kind"] == "outside-indexed-roots"}
    return [e for e in EDGES if e["to"] in ids]


def q_unpointed():
    pointed = {e["to"] for e in EDGES if e["kind"] != "contains"}
    loaded = {r["source"] for r in LEDGER}
    bare, auto = [], []
    for n in NODES.values():
        if n["kind"] != "File" or n["id"] in pointed:
            continue
        (auto if n["attrs"]["path"] in loaded else bare).append(n["attrs"]["path"])
    return {
        "zero_recognized_inbound_pointers": sorted(bare),
        "zero_pointers_but_auto_loaded": sorted(auto),
        "note": "the second bucket is load-bearing via the ledger, not via any "
                "edge; a load mechanism can have no in-repo origin to point from",
    }


def q_dupes():
    return [e for e in EDGES if e["kind"] == "identical-bytes"]


def q_orient():
    files = [n for n in NODES.values() if n["kind"] == "File"]
    roles = defaultdict(int)
    for n in files:
        for r in n["roles"]:
            roles[r["role"]] += 1
    kinds = defaultdict(int)
    for e in EDGES:
        kinds[e["kind"]] += 1
    return {
        "boundary": boundary(),
        "repositories": [{"path": n["attrs"]["path"], "head": n["attrs"]["head_ref"],
                          "dirty": n["attrs"]["dirty_entries"],
                          "branches": len(n["attrs"]["local_branches"])}
                         for n in q_estate()],
        "files": len(files),
        "roles_observed": dict(sorted(roles.items())),
        "edges_by_kind": dict(sorted(kinds.items())),
        "load_ledger_rows": len(LEDGER),
        "cold_start_bytes_known": q_cold_start()["bytes_known"],
        "cold_start_unmeasurable": q_cold_start()["unmeasurable_count"],
        "no_indexed_target_match": len(q_unmatched()),
        "outside_indexed_roots": len(q_outside()),
        "zero_recognized_inbound_pointers": len(q_unpointed()["zero_recognized_inbound_pointers"]),
        "zero_pointers_but_auto_loaded": len(q_unpointed()["zero_pointers_but_auto_loaded"]),
        "identical_byte_pairs": len(q_dupes()),
        "blindspots": len(BLIND),
    }


# ------------------------------------------------------------------ main ----

def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    roots = []
    if "--roots" in args:
        i = args.index("--roots")
        roots = args[i + 1:]
        args = args[:i]
    if not roots:
        roots = [os.getcwd()]
    cmd = args[0] if args else "orient"
    rest = args[1:]

    observe(roots)

    table = {
        "estate": lambda: q_estate(),
        "orient": lambda: q_orient(),
        "boot": lambda: q_boot(rest[0] if rest else None),
        "cold-start": lambda: q_cold_start(rest[0] if rest else None),
        "would-load": lambda: q_would_load(rest[0]),
        "inbound": lambda: q_inbound(rest[0]),
        "outbound": lambda: q_outbound(rest[0]),
        "trace": lambda: q_trace(rest[0]),
        "links": lambda: q_links(),
        "unmatched": lambda: q_unmatched(),
        "outside": lambda: q_outside(),
        "unpointed": lambda: q_unpointed(),
        "dupes": lambda: q_dupes(),
        "blindspots": lambda: BLIND,
    }
    if cmd not in table:
        print(__doc__)
        return 2
    result = {"boundary": boundary(), "command": cmd, "result": table[cmd]()}
    if as_json or cmd != "orient":
        print(json.dumps(result, indent=2, default=str))
    else:
        r = result["result"]
        print("indexed roots      :", ", ".join(r["boundary"]["indexed_roots"]))
        print("repositories       :", len(r["repositories"]))
        for repo in r["repositories"]:
            print("   %s  head=%s branches=%d dirty=%d"
                  % (repo["path"], repo["head"], repo["branches"], repo["dirty"]))
        print("files              :", r["files"])
        print("roles observed     :", r["roles_observed"] or "none")
        print("edges by kind      :", r["edges_by_kind"])
        print("load ledger rows   :", r["load_ledger_rows"])
        print("cold-start (known) : %d bytes (~%d tokens), %d mechanism(s) unmeasurable"
              % (r["cold_start_bytes_known"], r["cold_start_bytes_known"] / 4,
                 r["cold_start_unmeasurable"]))
        print("no indexed target match       :", r["no_indexed_target_match"])
        print("outside indexed roots         :", r["outside_indexed_roots"])
        print("zero recognized inbound ptrs  :", r["zero_recognized_inbound_pointers"])
        print("  ... but auto-loaded (ledger)  :", r["zero_pointers_but_auto_loaded"])
        print("identical byte pairs          :", r["identical_byte_pairs"])
        print("blindspots                    :", r["blindspots"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
