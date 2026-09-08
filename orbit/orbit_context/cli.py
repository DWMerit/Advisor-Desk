"""``orbit-context`` — the context-domain indexer for Orbit's local graph."""

from __future__ import annotations

import argparse
import json
import sys

from . import store
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
        help="Override the DuckDB path (default: ~/.orbit/graph.duckdb)",
    )
    index_parser.add_argument(
        "--ontology", dest="ontology_root", default=None,
        help="Override the ontology root (default: orbit/ontology)",
    )
    index_parser.add_argument(
        "-s", "--stats", action="store_true",
        help="Include per-file skipped and errored detail in the output",
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
        undeclared = statistics["schema"]["columns_not_declared_in_ontology"]
        if undeclared:
            print(
                f"orbit-context: {statistics['schema']['table']} carries columns the "
                f"ontology does not declare: {', '.join(undeclared)}",
                file=sys.stderr,
            )
        print(json.dumps(statistics, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
