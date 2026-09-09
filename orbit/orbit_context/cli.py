"""``orbit-context`` — the context-domain indexer for Orbit's local graph.

Two commands. ``index`` writes the graph; ``show`` reads one clause back out of
the file it came from, at the byte offsets the graph recorded. ``show`` writes
the clause's bytes to stdout and nothing else, so what comes out is the span of
the file and can be compared to it byte for byte; the locator goes to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import retrieve, store
from .indexer import index
from .ontology import OntologyError
from .store import StoreError
from .workspace import GitError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orbit-context",
        description="Index context surfaces into Orbit's local DuckDB graph.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser(
        "index", help="Index an estate and output graph statistics as JSON"
    )
    index_parser.add_argument("path", help="Path to the estate or repository to index")
    index_parser.add_argument(
        "--db", dest="db_path", default=str(store.DEFAULT_DB_PATH),
        help="Override the DuckDB path (default: ~/.orbit-context/context.duckdb)",
    )
    index_parser.add_argument(
        "--ontology", dest="ontology_root", default=None,
        help="Override the ontology root (default: orbit/ontology)",
    )
    index_parser.add_argument(
        "-s", "--stats", action="store_true",
        help="Include per-file skipped and errored detail in the output",
    )

    show_parser = subparsers.add_parser(
        "show",
        help="Print one clause's bytes, read from the file at its recorded offsets",
    )
    show_parser.add_argument(
        "fqn", help="The clause address: an fqn, e.g. "
                    "'CLAUDE.md#Estimating rules#M6 anchors', or a clause id",
    )
    show_parser.add_argument(
        "--repo", dest="repo", default=".",
        help="A path inside the repository the clause belongs to (default: the "
             "working directory). Its git state selects the snapshot to read.",
    )
    show_parser.add_argument(
        "--own", action="store_true",
        help="Print only this clause's own bytes, with descendant clauses "
             "removed. A parent's span includes everything nested under it, so "
             "without this a heading returns its whole subtree.",
    )
    show_parser.add_argument(
        "--db", dest="db_path", default=str(store.DEFAULT_DB_PATH),
        help="Override the DuckDB path (default: ~/.orbit-context/context.duckdb)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "index":
        try:
            statistics = index(
                args.path,
                db_path=args.db_path,
                ontology_root=args.ontology_root,
                detailed=args.stats,
            )
        except (OntologyError, StoreError, GitError) as error:
            print(f"orbit-context: {error}", file=sys.stderr)
            return 1
        for table in statistics["schema"]:
            undeclared = table["columns_not_declared_in_ontology"]
            if undeclared:
                print(
                    f"orbit-context: {table['table']} carries columns the "
                    f"ontology does not declare: {', '.join(undeclared)}",
                    file=sys.stderr,
                )
        print(json.dumps(statistics, indent=2))
        return 0

    if args.command == "show":
        try:
            clause = retrieve.resolve(args.fqn, repo=args.repo, db_path=args.db_path)
        except retrieve.AmbiguousAddress as error:
            # Nothing on stdout. A caller redirecting stdout to a file must get
            # one clause's bytes or no bytes -- never two spans concatenated.
            print(f"orbit-context: AMBIGUOUS: {error}", file=sys.stderr)
            for candidate in error.candidates:
                print(f"  {candidate.locator}", file=sys.stderr)
            return 2
        except retrieve.StaleIndex as error:
            print(f"orbit-context: STALE: {error}", file=sys.stderr)
            return 3
        except (StoreError, GitError, retrieve.RetrievalError) as error:
            print(f"orbit-context: {error}", file=sys.stderr)
            return 1
        try:
            if args.own:
                inner = retrieve.descendants(clause, repo=args.repo, db_path=args.db_path)
                body = clause.read_own(inner)
            else:
                body = clause.read()
        except retrieve.StaleIndex as error:
            print(f"orbit-context: STALE: {error}", file=sys.stderr)
            return 3
        except retrieve.RetrievalError as error:
            print(f"orbit-context: {error}", file=sys.stderr)
            return 1
        # The locator on stderr, the bytes on stdout: redirecting stdout to a
        # file must produce the span of the file, and nothing else.
        print(f"orbit-context: {clause.locator}", file=sys.stderr)
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
