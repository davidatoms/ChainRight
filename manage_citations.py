#!/usr/bin/env python3
"""Manage CITATIONS.json — toggle the `verified` flag per citation.

Three modes:

    list                          — show all citations as a table
    list --unverified             — only show entries with verified=false
    list --verified               — only show entries with verified=true
    verify <id>                   — set verified=true on the matching id
    unverify <id>                 — set verified=false on the matching id
    interactive                   — step through entries, prompt v/u/s/q for each

Subcommand examples:

    python manage_citations.py list
    python manage_citations.py list --unverified
    python manage_citations.py verify kaplan2020scaling
    python manage_citations.py interactive --unverified-only

The file path defaults to ./CITATIONS.json relative to the current working
directory; override with --path.

After every state change the JSON is rewritten in place with metadata
counts updated. Save-on-each-change is deliberate: an interactive
session that's interrupted should not lose verified flags.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def load_citations(path: Path) -> Dict:
    if not path.exists():
        raise SystemExit(f"CITATIONS.json not found at {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_citations(path: Path, data: Dict) -> None:
    citations = data.get("citations", [])
    data["metadata"] = {
        **data.get("metadata", {}),
        "total": len(citations),
        "verified_count": sum(1 for c in citations if c.get("verified")),
        "last_modified": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def find_citation(citations: List[Dict], cite_id: str) -> Optional[Dict]:
    for c in citations:
        if c.get("id") == cite_id:
            return c
    return None


def short_form(c: Dict, width: int = 70) -> str:
    """One-line summary of a citation."""
    flag = "[OK]" if c.get("verified") else "[? ]"
    title = c.get("title", "")
    if len(title) > width:
        title = title[: width - 3] + "..."
    return f"{flag} {c.get('id', ''):28s}  {c.get('year', '?'):<5}  {title}"


def cmd_list(args, data: Dict) -> int:
    citations = data["citations"]
    if args.unverified:
        citations = [c for c in citations if not c.get("verified")]
    elif args.verified:
        citations = [c for c in citations if c.get("verified")]

    if args.json:
        print(json.dumps(citations, indent=2, ensure_ascii=False))
        return 0

    if not citations:
        print("No citations match.")
        return 0

    print(f"{'flag':5s}  {'id':28s}  {'year':5s}  title")
    print("-" * 100)
    for c in citations:
        print(short_form(c))

    md = data.get("metadata", {})
    print()
    print(f"Total: {md.get('total', '?')}  Verified: {md.get('verified_count', '?')}")
    return 0


def cmd_set_verified(args, data: Dict, value: bool) -> int:
    c = find_citation(data["citations"], args.cite_id)
    if c is None:
        print(f"No citation found with id {args.cite_id!r}.", file=sys.stderr)
        print("Try `manage_citations.py list` to see all ids.", file=sys.stderr)
        return 2
    if c.get("verified") == value:
        print(f"{args.cite_id}: already {'verified' if value else 'unverified'}; no change.")
        return 0
    c["verified"] = value
    save_citations(args.path, data)
    print(f"{args.cite_id}: {'verified' if value else 'unverified'}.")
    return 0


def _format_long(c: Dict) -> str:
    """Multi-line presentation of a single citation for interactive review."""
    lines = [
        f"  id:        {c.get('id')}",
        f"  authors:   {c.get('authors')}",
        f"  year:      {c.get('year')}",
        f"  title:     {c.get('title')}",
        f"  venue:     {c.get('venue')}",
    ]
    if c.get("arxiv_id"):
        lines.append(f"  arxiv:     {c['arxiv_id']}")
    if c.get("doi"):
        lines.append(f"  doi:       {c['doi']}")
    if c.get("url"):
        lines.append(f"  url:       {c['url']}")
    if c.get("mentioned_in"):
        lines.append("  mentioned in:")
        for m in c["mentioned_in"]:
            lines.append(f"    - {m}")
    if c.get("notes"):
        lines.append(f"  notes:     {c['notes']}")
    lines.append(f"  status:    {'VERIFIED' if c.get('verified') else 'UNVERIFIED'}")
    return "\n".join(lines)


def cmd_interactive(args, data: Dict) -> int:
    citations = data["citations"]
    if args.unverified_only:
        target_indices = [i for i, c in enumerate(citations) if not c.get("verified")]
    else:
        target_indices = list(range(len(citations)))

    if not target_indices:
        print("No citations to review.")
        return 0

    print(f"Reviewing {len(target_indices)} citation(s). "
          f"Commands: [v]erify, [u]nverify, [s]kip, [n]otes, [q]uit.")
    print()

    for n, idx in enumerate(target_indices, start=1):
        c = citations[idx]
        print(f"--- [{n}/{len(target_indices)}] {c.get('id')} ---")
        print(_format_long(c))
        print()

        while True:
            try:
                choice = input("  action [v/u/s/n/q]? ").strip().lower()
            except EOFError:
                print()
                save_citations(args.path, data)
                return 0
            except KeyboardInterrupt:
                print()
                save_citations(args.path, data)
                return 0

            if choice in ("v", "verify"):
                if c.get("verified") is True:
                    print("  already verified.")
                else:
                    c["verified"] = True
                    save_citations(args.path, data)
                    print("  marked VERIFIED.")
                break
            if choice in ("u", "unverify"):
                if c.get("verified") is False:
                    print("  already unverified.")
                else:
                    c["verified"] = False
                    save_citations(args.path, data)
                    print("  marked UNVERIFIED.")
                break
            if choice in ("s", "skip", ""):
                break
            if choice in ("n", "notes"):
                print("  Enter notes (single line, empty cancels):")
                try:
                    note = input("  > ").strip()
                except EOFError:
                    note = ""
                if note:
                    c["notes"] = note
                    save_citations(args.path, data)
                    print("  notes updated.")
                continue
            if choice in ("q", "quit", "exit"):
                save_citations(args.path, data)
                print("  quit.")
                return 0
            print("  unknown command. v=verify, u=unverify, s=skip, n=notes, q=quit.")
        print()

    save_citations(args.path, data)
    md = data["metadata"]
    print(f"Done. Verified {md['verified_count']}/{md['total']} citations.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="manage_citations",
        description="Inspect and update CITATIONS.json verification status.",
    )
    p.add_argument(
        "--path",
        type=Path,
        default=Path("CITATIONS.json"),
        help="Path to CITATIONS.json (default: ./CITATIONS.json)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List citations as a table.")
    g = p_list.add_mutually_exclusive_group()
    g.add_argument("--verified", action="store_true", help="Only show verified entries.")
    g.add_argument("--unverified", action="store_true", help="Only show unverified entries.")
    p_list.add_argument("--json", action="store_true", help="Emit JSON instead of a table.")

    p_v = sub.add_parser("verify", help="Mark a citation verified.")
    p_v.add_argument("cite_id", help="The id of the citation to verify.")

    p_u = sub.add_parser("unverify", help="Mark a citation unverified.")
    p_u.add_argument("cite_id", help="The id of the citation to unverify.")

    p_i = sub.add_parser("interactive", help="Step through citations and verify each.")
    p_i.add_argument(
        "--unverified-only",
        action="store_true",
        help="Only present entries that are currently unverified.",
    )

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    data = load_citations(args.path)

    if args.command == "list":
        return cmd_list(args, data)
    if args.command == "verify":
        return cmd_set_verified(args, data, value=True)
    if args.command == "unverify":
        return cmd_set_verified(args, data, value=False)
    if args.command == "interactive":
        return cmd_interactive(args, data)
    raise SystemExit(f"unknown command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
