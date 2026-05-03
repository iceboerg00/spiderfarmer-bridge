"""Recursively walk all code objects in a .pyc and dump human-readable
summaries: function names, string consts, names, and disassembly.

Run with the same Python version the .pyc was compiled for.

Usage:
  python3.11 walk_pyc.py file.pyc
  python3.11 walk_pyc.py file.pyc --dis    # full disassembly
  python3.11 walk_pyc.py file.pyc --strings  # only string consts
"""
import argparse
import dis
import io
import marshal
import sys
import types

# Force UTF-8 stdout so non-ASCII strings (German source comments etc.) don't
# crash the Windows cp1252 console encoder.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def load_pyc(path: str) -> types.CodeType:
    with open(path, "rb") as f:
        data = f.read()
    return marshal.loads(data[16:])


def walk(co: types.CodeType, depth: int = 0, mode: str = "summary") -> None:
    indent = "  " * depth
    qual = co.co_qualname if hasattr(co, "co_qualname") else co.co_name
    sig = f"{co.co_name}({', '.join(co.co_varnames[:co.co_argcount])})"
    line = co.co_firstlineno
    print(f"{indent}── {sig}  [qual={qual}, line={line}, file={co.co_filename}]")

    if mode == "dis":
        for ins in dis.get_instructions(co):
            print(f"{indent}    {ins.offset:5d} {ins.opname:24s} {ins.argrepr}")
    else:
        # Print interesting constants (strings, numbers, tuples) and names
        strs = [c for c in co.co_consts if isinstance(c, str) and c]
        if strs:
            for s in strs:
                preview = s if len(s) <= 200 else s[:200] + "…"
                print(f"{indent}    str: {preview!r}")
        nums = [c for c in co.co_consts if isinstance(c, (int, float)) and not isinstance(c, bool)]
        if nums:
            print(f"{indent}    nums: {nums}")
        if co.co_names:
            print(f"{indent}    names: {list(co.co_names)}")

    # Recurse into nested code objects
    for c in co.co_consts:
        if isinstance(c, types.CodeType):
            walk(c, depth + 1, mode)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pyc")
    ap.add_argument("--dis", action="store_true", help="full disassembly")
    ap.add_argument("--strings", action="store_true",
                    help="only string consts, one per line, flat")
    args = ap.parse_args()

    co = load_pyc(args.pyc)

    if args.strings:
        seen: set[str] = set()

        def collect(c: types.CodeType) -> None:
            for k in c.co_consts:
                if isinstance(k, str) and k and k not in seen:
                    seen.add(k)
                if isinstance(k, types.CodeType):
                    collect(k)

        collect(co)
        for s in sorted(seen):
            print(s)
        return 0

    walk(co, mode="dis" if args.dis else "summary")
    return 0


if __name__ == "__main__":
    sys.exit(main())
