import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scraper import extract_cards, normalize_listing, listing_matches, scrape_urls
from google_sheets_sync import excel_column_name, resolve_credentials_path
from market_tracker import run_tracker


def test_listing_matches_accepts_valid_offer():
    listing = {
        "site": "4zida.rs",
        "title": "3 bedroom apartment with pets allowed, furnished, kitchen, washer, dishwasher",
        "url": "https://example.com",
        "price_eur": 780,
        "rooms_count": 3,
        "pets_allowed": True,
        "furnished": True,
        "washer_machine": True,
        "dishwasher": True,
        "kitchen_separate": True,
        "raw_text": "3 soba, namestena, kuhinja, pasija, ves masina, sudomasina",
    }
    assert listing_matches(listing) is True


def test_listing_matches_rejects_too_expensive_or_missing_features():
    listing = {
        "site": "oglasi.rs",
        "title": "2 bedroom apartment",
        "url": "https://example.com",
        "price_eur": 1100,
        "rooms_count": 2,
        "pets_allowed": True,
        "furnished": False,
        "washer_machine": True,
        "dishwasher": False,
        "kitchen_separate": True,
    }
    assert listing_matches(listing) is False


def test_extract_cards_handles_4zida_detail_link_pattern(monkeypatch):
    html = '''
    <html><body>
      <div class="relative flex flex-col">
        <a href="/izdavanje-stanova/kertvaros-gradske-lokacije-subotica/jednosoban-stan/63a8420870dfede34a09011e">Pogledaj detaljnije</a>
        <div>Premijum 26 Partizanskih Baza 97 Kertvaroš, Gradske lokacije, Subotica 690 € MESEČNO 1 soba Namešteno Parking Centralno Useljivo Vlasnik</div>
      </div>
      <div class="relative flex flex-col">
        <a href="/izdavanje-stanova/kertvaros-gradske-lokacije-subotica/jednosoban-stan/63a8420870dfede34a09011e">Pogledaj detaljnije</a>
        <div>Premijum 26 Partizanskih Baza 97 Kertvaroš, Gradske lokacije, Subotica 690 € MESEČNO 1 soba Namešteno Parking Centralno Useljivo Vlasnik</div>
      </div>
      <div class="relative flex flex-col">
        <a href="/izdavanje-stanova/other-city/another-stan/abc">Pogledaj detaljnije</a>
        <div>Previous slide Next slide Premijum 99 Other City 1200 € MESEČNO</div>
      </div>
    </body></html>
    '''
    monkeypatch.setattr("scraper.fetch_html", lambda url, timeout=20: html)
    cards = extract_cards(html, "4zida.rs")
    assert len(cards) == 1
    assert cards[0]["url"].endswith("63a8420870dfede34a09011e")
    assert cards[0]["price_eur"] == 690
    assert "kertvaros" in cards[0]["title"].lower()


def test_excel_column_name_handles_more_than_26_columns():
    assert excel_column_name(1) == "A"
    assert excel_column_name(26) == "Z"
    assert excel_column_name(27) == "AA"
    assert excel_column_name(52) == "AZ"
    assert excel_column_name(53) == "BA"


def test_run_tracker_supports_monitoring_and_json_output(tmp_path):
    output_file = tmp_path / "monitor_results.json"
    rows = run_tracker(site_names=["4zida.rs"], dry_run=True, output_json=str(output_file), verbose=False)
    assert isinstance(rows, list)
    assert output_file.exists()


def test_scrape_urls_processes_explicit_listing_pages(monkeypatch):
    html = '''
    <html><body>
      <h1>3 soba, namestena, kuhinja, pasija, ves masina, sudomasina</h1>
      <div class="price">690 €</div>
      <div>3 soba, namešteno, kuhinja, pasija, veš mašina, sudomašina</div>
    </body></html>
    '''

    monkeypatch.setattr("scraper.fetch_html", lambda url, timeout=20: html)
    rows = scrape_urls(["https://www.4zida.rs/izdavanje-stanova/test/3soba/abc123"])
    assert len(rows) == 1
    assert rows[0]["site"] == "4zida.rs"
    assert rows[0]["price_eur"] == 690.0
    assert rows[0]["rooms_count"] == 3
    assert rows[0]["is_match"] is True


def test_resolve_credentials_path_uses_project_default(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    expected = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service-account-key.json"))
    assert os.path.exists(expected)
    assert resolve_credentials_path() == expected
