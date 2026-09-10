"""``orbit-context`` — the context-domain indexer for Orbit's local graph.

Five commands. ``index`` writes the graph; ``migrate`` brings an existing store
to the ontology when the two have parted; ``show`` reads one clause back out of
the file it came from, at the byte offsets the graph recorded; ``repo-map``
prints one repository's governance surface, read from the graph, inside a stated
budget; ``ladder`` walks the ``RUNG_OF`` edges of one book and prints its rungs
in size order.

``show`` writes the clause's bytes to stdout and nothing else, so what comes out
is the span of the file and can be compared to it byte for byte; the locator
goes to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import history, ladders, repomap, retrieve, store
from .indexer import index, migrate
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

    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Remove columns the ontology no longer declares, where they hold "
             "no values",
    )
    migrate_parser.add_argument(
        "--db", dest="db_path", default=str(store.DEFAULT_DB_PATH),
        help="Override the DuckDB path (default: ~/.orbit-context/context.duckdb)",
    )
    migrate_parser.add_argument(
        "--ontology", dest="ontology_root", default=None,
        help="Override the ontology root (default: orbit/ontology)",
    )
    migrate_parser.add_argument(
        "--remove-values", dest="remove_values", action="store_true",
        help="Also remove a column that is holding values, and what it holds. "
             "Without this the migration stops and names such a column: "
             "whether what it holds is a leftover or data is not something "
             "this tool can tell, so it is a decision taken here, by hand.",
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

    map_parser = subparsers.add_parser(
        "repo-map",
        help="Print one repository's governance surface, inside a stated budget",
    )
    map_parser.add_argument(
        "--repo", dest="repo", default=".",
        help="A path inside the repository to map (default: the working "
             "directory). Its git state selects the indexed snapshot.",
    )
    map_parser.add_argument(
        "--base", dest="base", default=None,
        help="The ref commits ahead are counted against. Default: "
             f"${history.BASE_VARIABLE}, then origin/HEAD, then the first of "
             + ", ".join(history.BASE_CANDIDATES) + " that resolves.",
    )
    map_parser.add_argument(
        "--session", dest="session", default=None,
        help="This session's id, for counting which commits ahead carry its "
             f"{history.TRAILER_KEY} trailer. Default: read from "
             + " or ".join(history.SESSION_VARIABLES) + ". Where none is "
             "available the count is reported as not measured, never as zero.",
    )
    map_parser.add_argument(
        "--budget", dest="budget", type=int, default=repomap.BUDGET_BYTES,
        help=f"Byte budget for the output (default: {repomap.BUDGET_BYTES}, "
             f"{repomap.BUDGET_CITATION}).",
    )
    map_parser.add_argument(
        "--db", dest="db_path", default=str(store.DEFAULT_DB_PATH),
        help="Override the DuckDB path (default: ~/.orbit-context/context.duckdb)",
    )

    ladder_parser = subparsers.add_parser(
        "ladder",
        help="Print a book's rungs with their byte counts, in size order",
    )
    ladder_parser.add_argument(
        "name", nargs="?", default=None,
        help="The book to print: its stem, its directory, or the base rung's "
             "path. Omitted, every ladder in the snapshot is printed.",
    )
    ladder_parser.add_argument(
        "--repo", dest="repo", default=".",
        help="A path inside the repository to read (default: the working "
             "directory). Its git state selects the indexed snapshot.",
    )
    ladder_parser.add_argument(
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
        # No warning loop over `schema` here: a table carrying a column the
        # ontology does not declare raises SchemaDrift above, so by this line
        # `columns_not_declared_in_ontology` is empty on every table.
        print(json.dumps(statistics, indent=2))
        return 0

    if args.command == "migrate":
        try:
            report = migrate(args.db_path, ontology_root=args.ontology_root,
                             remove_values=args.remove_values)
        except (OntologyError, StoreError) as error:
            print(f"orbit-context: {error}", file=sys.stderr)
            return 1
        print(json.dumps(report, indent=2))
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

    if args.command == "repo-map":
        try:
            print(repomap.repo_map(
                args.repo, db_path=args.db_path, base=args.base,
                session=args.session, budget=args.budget,
            ), end="")
        except (repomap.RepoMapError, StoreError, GitError,
                retrieve.RetrievalError) as error:
            print(f"orbit-context: {error}", file=sys.stderr)
            return 1
        return 0

    if args.command == "ladder":
        try:
            print(ladders.ladder(args.repo, db_path=args.db_path, name=args.name),
                  end="")
        except (ladders.LadderError, StoreError, GitError,
                retrieve.RetrievalError) as error:
            print(f"orbit-context: {error}", file=sys.stderr)
            return 1
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
