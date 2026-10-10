#!/usr/bin/env python3
"""Compatibility wrapper: same as `python3 picker.py --role mid ...`."""

import sys

import picker

if __name__ == "__main__":
    if "--role" not in sys.argv:
        sys.argv.insert(1, "--role")
        sys.argv.insert(2, "mid")
    picker.main()
