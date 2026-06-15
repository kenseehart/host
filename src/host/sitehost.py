"""CLI entrypoint — named sitehost to avoid collision with /usr/bin/host (DNS)."""

from host.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
