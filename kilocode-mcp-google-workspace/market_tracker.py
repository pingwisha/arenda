from __future__ import annotations

import argparse
import json
from datetime import date
from typing import List, Optional

from scraper import SITE_URLS, listing_matches, scrape_site, scrape_urls
from parsers.airbnb import parse_airbnb_site
from google_sheets_sync import sync_records
from models.listing import Listing
from utils.translator import translate_listing


def _normalize_raw(raw: dict) -> Listing:
    price_eur = float(raw.get("price_eur") or 0.0)
    price_text = raw.get("price_text") or raw.get("price_raw") or ""
    if not price_text and price_eur:
        price_text = f"{price_eur} EUR"
    posted_date = raw.get("posted_date") or raw.get("found_date") or ""
    if isinstance(posted_date, date):
        posted_date = posted_date.isoformat()

    listing = Listing(
        id=raw.get("url", ""),
        platform=raw.get("site", ""),
        url=raw.get("url", ""),
        title=raw.get("title", ""),
        district=raw.get("district", "Белград"),
        address=raw.get("address", ""),
        property_type="Квартира",
        rooms=raw.get("rooms_count", 0) or 0,
        kitchen=raw.get("kitchen_separate", False) or raw.get("kitchen", False),
        area_m2=raw.get("area_m2"),
        floor=raw.get("floor", ""),
        price_eur=price_eur,
        price_text=price_text,
        currency="EUR",
        posted_date=posted_date,
        utilities_eur=raw.get("utilities_eur"),
        electricity_included=raw.get("electricity_included"),
        deposit_eur=raw.get("deposit_eur"),
        deposit_refundable=raw.get("deposit_refundable", True),
        other_payments=raw.get("other_payments", ""),
        total_cost_eur=raw.get("total_cost_eur"),
        payment_3_weeks=raw.get("payment_3_weeks", False),
        min_lease_months=raw.get("min_lease_months", ""),
        dogs_allowed=raw.get("pets_allowed", False),
        cats_allowed=raw.get("pets_allowed", False),
        pet_fee_eur=float(raw.get("pet_fee_eur") or 0.0),
        fridge=raw.get("fridge", False),
        stove=raw.get("stove", False),
        oven=raw.get("oven", False),
        washing_machine=raw.get("washer_machine", False),
        dishwasher=raw.get("dishwasher", False),
        hot_water=raw.get("hot_water", False),
        wifi=raw.get("wifi", False),
        beds_for_all=raw.get("beds_for_all", False),
        furniture_desc=raw.get("furniture_desc", ""),
        first_seen=date.today(),
        found_date=date.today(),
        last_updated=date.today(),
        rented_date=None,
        days_on_market=0,
        current_price_eur=price_eur,
        price_change_eur=0.0,
        status="Активно",
        notes=raw.get("notes", ""),
        source_text=raw.get("source_text", ""),
        raw=raw,
    )
    translated = translate_listing(listing.__dict__)
    for key, value in translated.items():
        if hasattr(listing, key):
            setattr(listing, key, value)
    return listing


def _listing_matches_criteria(listing: Listing) -> bool:
    if listing.rooms < 3:
        return False
    if listing.price_eur <= 0 or listing.price_eur > 900:
        return False
    if not listing.dogs_allowed:
        return False
    if not listing.washing_machine:
        return False
    if not listing.dishwasher:
        return False
    if not listing.kitchen:
        return False
    return True


def _listing_matches_criteria_lenient(listing: Listing) -> bool:
    if listing.rooms < 3:
        return False
    if listing.price_eur <= 0 or listing.price_eur > 900:
        return False
    if not listing.dogs_allowed:
        return False
    return True


def run_tracker(site_names: List[str] | None = None, dry_run: bool = False, output_json: Optional[str] = None, verbose: bool = True, urls: Optional[List[str]] = None) -> List[Listing]:
    sites = site_names or sorted(list(SITE_URLS.keys()) + ["airbnb.ru"])
    all_rows: List[Listing] = []

    if urls:
        for url in urls:
            site = url.split("/", 3)[2].replace("www.", "") if url.startswith("http") else "unknown"
            rows = scrape_urls([url], site_hint=site)
            for row in rows:
                listing = _normalize_raw(row)
                listing.is_match = _listing_matches_criteria_lenient(listing)
                all_rows.append(listing)
    else:
        for site in sites:
            if site == "airbnb.ru":
                try:
                    listings = parse_airbnb_site()
                    for listing in listings:
                        listing.is_match = _listing_matches_criteria_lenient(listing)
                        all_rows.append(listing)
                    if verbose:
                        print(f"{site}: {len(listings)} listings scanned, {sum(1 for l in listings if l.is_match)} matches")
                    continue
                except Exception as exc:
                    if verbose:
                        print(f"{site}: error -> {exc}")
                    continue

            rows = scrape_site(site)
            for row in rows:
                listing = _normalize_raw(row)
                listing.is_match = _listing_matches_criteria_lenient(listing)
                all_rows.append(listing)
            if verbose:
                print(f"{site}: {len(rows)} listings scanned, {sum(1 for l in all_rows if l.is_match)} matches")

    if output_json:
        with open(output_json, "w", encoding="utf-8") as fh:
            json.dump([listing.__dict__ for listing in all_rows], fh, ensure_ascii=False, indent=2, default=str)

    if not dry_run:
        from google_sheets_sync import sync_records
        result = sync_records(all_rows)
        if verbose:
            print(f"Synced {len(all_rows)} listings: {result}")
    else:
        if verbose:
            print(f"Dry run: {len(all_rows)} listings would be synced")

    return all_rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape rental listings and sync matching results to Google Sheets.")
    parser.add_argument("--site", choices=sorted(list(SITE_URLS.keys()) + ["airbnb.ru"]), help="Only process one source website")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Google Sheets")
    parser.add_argument("--output-json", help="Optional path to save matching listings as JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress terminal output")
    parser.add_argument("--urls", nargs="*", default=[], help="Exact listing URLs to inspect directly")
    args = parser.parse_args()

    site_names = [args.site] if args.site else None
    run_tracker(site_names=site_names, dry_run=args.dry_run, output_json=args.output_json, verbose=not args.quiet, urls=args.urls or None)
