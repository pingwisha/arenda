from __future__ import annotations

import os
import time
from datetime import date
from typing import Any, Dict, Iterable, List, Optional

from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

from models.listing import Listing


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _retry_api_call(callable, max_retries=5, base_delay=2.0):
    for attempt in range(max_retries):
        try:
            return callable()
        except HttpError as e:
            if e.resp.status in (429, 500, 502, 503, 504):
                wait = base_delay * (2 ** attempt)
                print(f"Google Sheets API error {e.resp.status}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    return callable()


def resolve_credentials_path() -> Optional[str]:
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path and os.path.exists(env_path):
        return env_path

    project_root = os.path.dirname(os.path.abspath(__file__))
    default_paths = [
        os.path.join(project_root, "service-account-key.json"),
        os.path.join(project_root, "service_account.json"),
        os.path.join(project_root, "credentials.json"),
    ]
    for candidate in default_paths:
        if os.path.exists(candidate):
            return candidate

    return None


def excel_column_name(index: int) -> str:
    result = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def get_service() -> Any:
    cred_path = resolve_credentials_path()
    if not cred_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set and no default service account key was found in the project folder")
    creds = service_account.Credentials.from_service_account_file(cred_path, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def get_spreadsheet_id() -> str:
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    if not spreadsheet_id:
        fallback = "1yXzUII6pZ9rg57C0c7gefl57z88uz1_mKlNBy8Nu4g0"
        if fallback:
            return fallback
        raise ValueError("SPREADSHEET_ID is not set")
    return spreadsheet_id


def ensure_sheet(service: Any, spreadsheet_id: str, sheet_name: str) -> None:
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing = [sheet.get("properties", {}).get("title") for sheet in spreadsheet.get("sheets", [])]
    if sheet_name not in existing:
        request = {
            "addSheet": {
                "properties": {
                    "title": sheet_name,
                    "sheetType": "GRID",
                    "gridProperties": {"rowCount": 2000, "columnCount": 80},
                }
            }
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [request]},
        ).execute()

    def _do_write_headers():
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:{excel_column_name(len(HEADERS_RU))}1",
            valueInputOption="RAW",
            body={"values": [HEADERS_RU]},
        ).execute()

    _retry_api_call(_do_write_headers)


HEADERS_RU = [
    "ID_объявления",
    "Площадка",
    "Ссылка",
    "Дата_объявления",
    "Дата_первого_появления",
    "Дата_нашли",
    "Дата_последнего_обновления",
    "Дата_сдачи",
    "Дней_на_рынке",
    "Район",
    "Адрес",
    "Тип_жилья",
    "Комнат",
    "Кухня",
    "Площадь_м2",
    "Этаж",
    "Цена_EUR",
    "Цена_текст",
    "Валюта",
    "Коммуналка_EUR",
    "Электричество_включено",
    "Залог_EUR",
    "Залог_возвращается",
    "Другие_платежи",
    "Итоговая_стоимость_EUR",
    "Оплата_за_3_недели",
    "Мин_срок_аренды_мес",
    "Собака_разрешена",
    "Кошка_разрешена",
    "Доплата_за_животных_EUR",
    "Холодильник",
    "Плита",
    "Духовка",
    "Стиральная_машина",
    "Посудомоечная_машина",
    "Горячая_вода",
    "Wi_Fi",
    "Мебель_кровати",
    "Мебель_общая",
    "Цена_сейчас_EUR",
    "Изменение_цены_EUR",
    "Статус",
    "Подходит",
    "Примечания",
]

URL_COLUMN_INDEX = 2  # 0-based: C column = index 2
ID_COLUMN_INDEX = 0   # A column = index 0
STATUS_COLUMN_INDEX = 39  # 0-based: AM column = index 39 (Статус)
PRICE_COLUMN_INDEX = 40   # 0-based: AN column = index 40 (Цена_сейчас_EUR)
UPDATED_COLUMN_INDEX = 6  # 0-based: G column = index 6 (Дата_последнего_обновления)
RENTED_COLUMN_INDEX = 7    # 0-based: H column = index 7 (Дата_сдачи)
MARKET_DAYS_INDEX = 8      # 0-based: I column = index 8 (Дней_на_рынке)
POSTED_DATE_INDEX = 3      # 0-based: D column = index 3 (Дата_объявления)
IS_MATCH_INDEX = 41        # 0-based: AO column = index 41 (Подходит)


def _get_existing_data(service: Any, spreadsheet_id: str, sheet_name: str) -> Dict[str, Dict[str, Any]]:
    ensure_sheet(service, spreadsheet_id, sheet_name)
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:{excel_column_name(len(HEADERS_RU))}100000",
    ).execute()
    
    rows = result.get("values", [])
    if not rows:
        return {}
    
    headers = rows[0]
    existing = {}
    for idx, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        url = row[URL_COLUMN_INDEX] if len(row) > URL_COLUMN_INDEX else ""
        listing_id = row[ID_COLUMN_INDEX] if len(row) > ID_COLUMN_INDEX else ""
        key = url or listing_id
        if key:
            existing[key] = {
                "row_index": idx,
                "data": {headers[i] if i < len(headers) else f"col_{i}": row[i] if i < len(row) else "" for i in range(len(headers))}
            }
    return existing


def _update_existing_listing(service: Any, spreadsheet_id: str, sheet_name: str, row_index: int, listing: Listing) -> None:
    today = date.today().isoformat()
    
    update_values = {
        "Цена_EUR": listing.price_eur,
        "Цена_текст": listing.price_text or (f"{listing.price_eur} EUR/мес" if listing.price_eur else ""),
        "Дата_объявления": listing.posted_date or "",
        "Дата_последнего_обновления": today,
        "Цена_сейчас_EUR": listing.current_price_eur if listing.current_price_eur else listing.price_eur,
        "Изменение_цены_EUR": listing.price_change_eur,
        "Статус": listing.status,
        "Подходит": "да" if listing.is_match else "нет",
    }
    
    def _do_update():
        data = []
        for header, value in update_values.items():
            col_idx = HEADERS_RU.index(header)
            col_letter = excel_column_name(col_idx)
            data.append({
                "range": f"{sheet_name}!{col_letter}{row_index}",
                "values": [[value]],
            })
        
        body = {
            "valueInputOption": "RAW",
            "data": data,
        }
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body,
        ).execute()
    
    _retry_api_call(_do_update)


def sync_records(listings: List[Listing], sheet_name: str = "Объявления") -> Dict[str, int]:
    service = get_service()
    spreadsheet_id = get_spreadsheet_id()
    
    ensure_sheet(service, spreadsheet_id, sheet_name)
    
    # Get existing data for deduplication
    existing = _get_existing_data(service, spreadsheet_id, sheet_name)
    
    new_rows = []
    updated_count = 0
    new_count = 0
    today = date.today().isoformat()
    
    for listing in listings:
        key = listing.url or listing.id
        if key in existing:
            row_index = existing[key]["row_index"]
            old_data = existing[key]["data"]
            
            try:
                old_price = float(old_data.get("Цена_сейчас_EUR", listing.price_eur) or listing.price_eur)
            except (TypeError, ValueError):
                old_price = listing.price_eur
            if old_price != listing.price_eur:
                listing.price_change_eur = listing.price_eur - old_price
                listing.status = "Цена_изменилась"
            else:
                listing.price_change_eur = 0.0
                listing.status = "Активно"
            
            listing.last_updated = date.today()
            _update_existing_listing(service, spreadsheet_id, sheet_name, row_index, listing)
            updated_count += 1
        else:
            listing.first_seen = date.today()
            listing.found_date = date.today()
            listing.last_updated = date.today()
            listing.current_price_eur = listing.price_eur
            listing.price_change_eur = 0.0
            listing.status = "Активно"
            listing.days_on_market = 0
            new_rows.append(listing)
            new_count += 1
    
    if new_rows:
        values = [listing.to_sheet_row() for listing in new_rows]
        body = {"values": values}
        
        next_row = 2
        if existing:
            max_row = max(data["row_index"] for data in existing.values())
            next_row = max_row + 1
        
        end_row = next_row + len(values) - 1
        end_col = excel_column_name(len(HEADERS_RU))
        range_str = f"{sheet_name}!A{next_row}:{end_col}{end_row}"
        
        def _do_append():
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_str,
                valueInputOption="RAW",
                body=body,
            ).execute()
        
        _retry_api_call(_do_append)
    
    _write_analytics(service, spreadsheet_id, listings, sheet_name)
    
    return {"new": new_count, "updated": updated_count, "total": new_count + updated_count}


def _write_analytics(service: Any, spreadsheet_id: str, listings: List[Listing], sheet_name: str = "Объявления") -> None:
    if not listings:
        return

    analytics_sheet_name = "Аналитика"
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_sheets = [sheet.get("properties", {}).get("title") for sheet in spreadsheet.get("sheets", [])]
    if analytics_sheet_name not in existing_sheets:
        analytics_body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": analytics_sheet_name,
                        }
                    }
                }
            ]
        }
        try:
            _retry_api_call(lambda: service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=analytics_body,
            ).execute())
        except HttpError as exc:
            if exc.resp.status != 409:
                raise

    total = len(listings)
    matching = sum(1 for listing in listings if listing.is_match)
    prices = [listing.price_eur for listing in listings if listing.price_eur > 0]
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0
    platforms = {}
    for listing in listings:
        platforms[listing.platform] = platforms.get(listing.platform, 0) + 1

    rows = [
        ["Показатель", "Значение"],
        ["Всего объявлений", total],
        ["Подходящих", matching],
        ["Средняя цена EUR", avg_price],
        ["Мин цена EUR", min_price],
        ["Макс цена EUR", max_price],
    ]
    for platform, count in sorted(platforms.items()):
        rows.append([f"Площадка: {platform}", count])

    def _do_write():
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{analytics_sheet_name}!A1:B{len(rows)}",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()

    _retry_api_call(_do_write)


def read_listings(sheet_name: str = "Объявления") -> List[Dict[str, Any]]:
    service = get_service()
    spreadsheet_id = get_spreadsheet_id()
    
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:{excel_column_name(len(HEADERS_RU))}100000",
    ).execute()
    
    rows = result.get("values", [])
    if not rows:
        return []
    
    headers = rows[0]
    listings = []
    for row in rows[1:]:
        if not row or all(cell is None or not str(cell).strip() for cell in row):
            continue
        listing = {headers[i] if i < len(headers) else f"col_{i}": row[i] if i < len(row) else "" for i in range(len(headers))}
        listings.append(listing)
    
    return listings


def mark_missing_as_disappeared(sheet_name: str = "Объявления") -> int:
    service = get_service()
    spreadsheet_id = get_spreadsheet_id()
    
    ensure_sheet(service, spreadsheet_id, sheet_name)
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A{STATUS_COLUMN_INDEX + 1}:{excel_column_name(len(HEADERS_RU))}100000",
    ).execute()
    
    rows = result.get("values", [])
    if not rows:
        return 0
    
    today = date.today().isoformat()
    updates = []
    for i, row in enumerate(rows):
        if not row:
            continue
        status = row[0] if row else ""
        if status == "Активно":
            updates.append({
                "range": f"{sheet_name}!AM{i + 2}",
                "values": [["Исчезло"]],
            })
            updates.append({
                "range": f"{sheet_name}!F{i + 2}",
                "values": [[today]],
            })
    
    if updates:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"valueInputOption": "RAW", "data": updates},
        ).execute()
    
    return len(updates)
