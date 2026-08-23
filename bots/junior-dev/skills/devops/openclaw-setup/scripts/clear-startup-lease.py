#!/usr/bin/env python
"""
clear-startup-lease.py — OpenClaw stuck-startup fix.

Deletes the orphaned 'startup-migrations' lease row from OpenClaw's state
SQLite DB. This row is written at gateway boot and only cleared on a CLEAN
exit — if the gateway is killed/crashes mid-boot, the row stays and every
later launch fails with:
  "OpenClaw startup migrations are already running for this state directory"

SAFETY: only run this when NO openclaw gateway node.exe process is alive.
Running it while a gateway holds the lease is harmless but pointless.

Usage:
  cd "$HOME" && python clear-startup-lease.py
"""
import sqlite3
import os
import sys

DB = os.path.expanduser(r"~/.openclaw/state/openclaw.sqlite")


def main():
    if not os.path.exists(DB):
        print(f"ERROR: state DB not found at {DB}")
        sys.exit(1)

    c = sqlite3.connect(DB)
    cur = c.cursor()
    try:
        cur.execute("SELECT count(*) FROM state_leases")
        before = cur.fetchone()[0]
        cur.execute("DELETE FROM state_leases WHERE scope='startup-migrations'")
        c.commit()
        cur.execute("SELECT count(*) FROM state_leases")
        after = cur.fetchone()[0]
        print(f"leases before: {before}  after: {after}")
        if after == 0:
            print("OK: startup-migrations lease cleared. Launch the gateway now.")
        else:
            print("WARN: lease row remains — inspect state_leases manually.")
    except sqlite3.Error as e:
        print(f"SQLITE ERROR: {e}")
        sys.exit(2)
    finally:
        c.close()


if __name__ == "__main__":
    main()
