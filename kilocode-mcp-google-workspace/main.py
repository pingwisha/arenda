from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from market_tracker import run_tracker


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Kilo автономный парсер объявлений аренды квартир в Белграде")
    parser.add_argument("--site", choices=sorted([
        "4zida.rs", "cityexpert.rs", "halooglasi.com", "imovina.net",
        "nekretnine.rs", "oglasi.rs", "airbnb.ru"
    ]), help="Сайт для парсинга")
    parser.add_argument("--all", action="store_true", help="Запустить все парсеры")
    parser.add_argument("--dry-run", action="store_true", help="Только показать, не записывать в Google Sheets")
    parser.add_argument("--output-json", help="Сохранить результаты в JSON")
    parser.add_argument("--quiet", action="store_true", help="Тихий режим")
    parser.add_argument("--urls", nargs="*", default=[], help="URL объявлений для парсинга")
    args = parser.parse_args(argv)

    if not args.site and not args.all and not args.urls:
        args.all = True

    site_names = None
    if args.site:
        site_names = [args.site]
    elif args.all:
        site_names = sorted([
            "4zida.rs", "cityexpert.rs", "halooglasi.com", "imovina.net",
            "nekretnine.rs", "oglasi.rs", "airbnb.ru"
        ])

    run_tracker(
        site_names=site_names,
        dry_run=args.dry_run,
        output_json=args.output_json,
        verbose=not args.quiet,
        urls=args.urls or None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
