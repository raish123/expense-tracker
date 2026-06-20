"""Thin CLI wrapper around database.db.seed_dummy_data().

Usage:
    python scripts/seed_dummy.py                          # 5 users / 8 expenses each
    python scripts/seed_dummy.py users=10 expenses-per-user=12

All SQL/generation lives in database/db.py — this script only parses args,
ensures the schema exists, calls the helper, and prints a report. Dev-only.
"""

import sys
from pathlib import Path

# Allow running as `python scripts/seed_dummy.py` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db import init_db, seed_dummy_data  # noqa: E402


def _parse_args(argv: list[str]) -> dict[str, int]:
    opts = {"num_users": 5, "expenses_per_user": 8}
    for arg in argv:
        if "=" not in arg:
            raise SystemExit(f"Unrecognized argument: {arg!r} (expected key=value)")
        key, value = arg.split("=", 1)
        try:
            n = int(value)
        except ValueError:
            raise SystemExit(f"{key} must be an integer, got {value!r}")
        if n < 1:
            raise SystemExit(f"{key} must be >= 1, got {n}")
        if key == "users":
            opts["num_users"] = n
        elif key == "expenses-per-user":
            opts["expenses_per_user"] = n
        else:
            raise SystemExit(f"Unknown option {key!r} (use users= / expenses-per-user=)")
    return opts


def main() -> None:
    opts = _parse_args(sys.argv[1:])
    init_db()
    summary = seed_dummy_data(opts["num_users"], opts["expenses_per_user"])
    print(
        f"Seeded: {summary['users_inserted']} users inserted, "
        f"{summary['users_skipped']} skipped (already existed), "
        f"{summary['expenses_inserted']} expenses inserted."
    )


if __name__ == "__main__":
    main()
