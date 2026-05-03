"""Lightweight strings(1) replacement for binary analysis on systems where
GNU binutils aren't available (Git Bash on Windows). Prints printable ASCII
runs of length >= min_len, one per line."""
import argparse
import re
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-n", "--min-len", type=int, default=4)
    ap.add_argument("--re", help="optional regex filter applied to each string")
    args = ap.parse_args()

    pat = re.compile(rb"[\x20-\x7e]{%d,}" % args.min_len)
    filt = re.compile(args.re) if args.re else None

    with open(args.path, "rb") as f:
        data = f.read()

    for m in pat.finditer(data):
        s = m.group().decode("ascii", errors="replace")
        if filt and not filt.search(s):
            continue
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
