"""Module entrypoint for `python -m solidity_fcg_tool`."""

from .cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
