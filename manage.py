#!/usr/bin/env python3
"""Account admin for hosted mode, from the server's command line. Passwords are asked for, never passed as arguments
(they would end up in shell history and process lists).

  python manage.py create-admin NAME     # new admin account
  python manage.py set-password NAME     # new password, signs the account out everywhere
  python manage.py list                  # accounts with role and status
"""

import argparse
import getpass
import sys

import auth
import db


def ask_password():
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Again: "):
        sys.exit("The passwords differ.")
    return pw


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create-admin").add_argument("name")
    sub.add_parser("set-password").add_argument("name")
    sub.add_parser("list")
    a = p.parse_args(argv)
    conn = db.connect()
    try:
        if a.cmd == "create-admin":
            auth.create_account(conn, a.name, ask_password(), role="admin")
            print(f"Admin {a.name} created.")
        elif a.cmd == "set-password":
            auth.set_password(conn, a.name, ask_password())
            print(f"Password for {a.name} changed; its sessions are signed out.")
        else:
            for r in auth.list_accounts(conn):
                print(
                    f"{r['username']:<24} {r['role']:<12} {'blocked' if r['blocked'] else 'active':<8} {r['created_at']}"
                )
    except auth.AuthError as e:
        sys.exit(str(e))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
