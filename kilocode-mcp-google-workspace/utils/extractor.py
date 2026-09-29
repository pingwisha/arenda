from __future__ import annotations

import re
from typing import Any, Dict, Optional


def clean_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_price(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = clean_text(value)
    if not text:
        return None

    currency_matches = re.findall(r"(\d[\d\s.,]*)\s*(?:€|eur|EUR)", text, flags=re.IGNORECASE)
    if currency_matches:
        candidate = currency_matches[-1].replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return float(candidate)
        except ValueError:
            pass

    digits = re.findall(r"(\d+[\.,]?\d*)", text.replace("€", " ").replace("EUR", " "))
    if not digits:
        return None
    number = digits[-1].replace(".", "").replace(",", ".")
    try:
        return float(number)
    except ValueError:
        return None


def parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    text = re.sub(r"[^0-9]", "", clean_text(value))
    return int(text) if text else None


def safe_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    text = clean_text(value).lower()
    return any(token in text for token in ["да", "yes", "allow", "allowed", "true", "moguće", "1", "включено", "есть", "разрешено"])


def extract_from_description(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    return {
        "pets_allowed": any(token in text_lower for token in ["собака", "кошка", "животные", "pet friendly", "pets allowed", "dog", "cat", "sa psom", "sa mačkom", "kućni ljubimci", "psi", "мачке", "mogućnost sa psom", "можно с питомцами", "можно с питомцем", "разрешены животные", "разрешена собака", "разрешена кошка", "домашние животные"]),
        "furnished": any(token in text_lower for token in ["меблирован", "мебель", "кровать", "диван", "стол", "namešten", "namestena", "furniture", "mobili", "opremljen", "opremljena", "опремен"]),
        "washing_machine": any(token in text_lower for token in ["стиральная машина", "washing machine", "washer", "perilica", "ves masina", "vešeraj", "veš mašina", "стиралка", "машина для стирки"]),
        "dishwasher": any(token in text_lower for token in ["посудомоечная машина", "dishwasher", "sudomašina", "posudomachine", "suđa mašina", "sudomasina", "посудомойка", "машина для посуды"]),
        "kitchen": any(token in text_lower for token in ["кухня", "kitchen", "kuhinja", "kuhinja sa", "full kitchen", "odvojena kuhinja", "плита", "духовка", "oven", "stove"]),
        "hot_water": any(token in text_lower for token in ["горячая вода", "hot water", "topla voda", "грејање"]),
        "wifi": any(token in text_lower for token in ["wi-fi", "wifi", "интернет", "internet", "wi fi"]),
        "fridge": any(token in text_lower for token in ["холодильник", "fridge", "refrigerator", "frižider", "ledenica"]),
        "stove": any(token in text_lower for token in ["плита", "stove", "šporet", "cooktop"]),
        "oven": any(token in text_lower for token in ["духовка", "oven", "пећ"]),
        "beds_for_all": any(token in text_lower for token in ["кровать", "bed", "krevet", "спальное место", "sleeping"]),
    }


def detect_rooms_count(text: str) -> int:
    match = re.search(r"(\d+)\s*(?:soba|sobe|spavaća soba|room|rooms|bedroom|bedrooms|спальн|комнат)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def detect_beds_count(text: str) -> int:
    match = re.search(r"(\d+)\s*(?:кровати|кроватей|bed|beds|спальных мест)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def detect_area(text: str) -> Optional[float]:
    match = re.search(r"(\d+[\.,]?\d*)\s*(?:m²|m2|кв\.?\s*м|м\s*2|квм)", text, flags=re.IGNORECASE)
    if match:
        value = match.group(1).replace(",", ".")
        try:
            return float(value)
        except ValueError:
            pass
    return None


def detect_floor(text: str) -> str:
    match = re.search(r"(?:этаж|floor|sprat|kat)\s*[:\s]*(\d+[\/\d\s]*)?(?:\s*из\s*(\d+))?", text, flags=re.IGNORECASE)
    if match:
        floor = match.group(1) or ""
        total = match.group(2) or ""
        if floor and total:
            return f"{floor.strip()}/{total.strip()}"
        return floor.strip() or total.strip()
    return ""


def detect_pet_fee(text: str) -> float:
    match = re.search(r"(?:pet fee|доплата за животных|доплата за животное|animal fee|fee.*pet).*?(\d+[\.,]?\d*)\s*(?:€|eur|EUR)?", text, flags=re.IGNORECASE)
    if match:
        value = match.group(1).replace(",", ".")
        try:
            return float(value)
        except ValueError:
            pass
    return 0.0


def detect_min_lease(text: str) -> str:
    match = re.search(r"(?:мин.*?срок|minimum.*?stay|min.*?lease|минимальный срок).*?(\d+)\s*(?:мес|месяц|month|months|месеци|месеца)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1) + " мес"
    return ""


def detect_district(text: str, url: str = "") -> str:
    candidates = []
    if url:
        candidates.append(url)
    candidates.append(text)

    districts = [
        "Vračar", "Novi Beograd", "Stari Grad", "Zemun", "Dedinje", "Senjak",
        "Karaburma", "Konjarnik", "Mirijevo", "Braće Jerković", "Bežanija",
        "Kalemegdan", "Krnjača", "Palilula", "Voždovac", "Čukarica",
        "Rakovica", "Zvezdara", "Savski Venac", "Grocka", "Altina",
        "Plavi Horizonti", "Bežanijska Kosa", "Jovanova", "Ledine",
        "Studentski Grad", "Vidikovačka Padina", "Banjica", "Kumodraž",
        "Leštane", "Veliki Mokri Lug", "Beli Potok", "Pinosava",
        "Ripanj", "Ralja", "Umčari", "Železnik", "Žarkovo",
        "Košutnjak", "Banovo Brdo", "Topčidersko Brdo", "Senjski Rudnik",
        "Beograd", "Белград", "zemun", "vračar", "novi beograd", "stari grad",
        "Земун", "Врачар", "Новый Белград", "Старый город"
    ]

    for candidate in candidates:
        text_lower = candidate.lower()
        for district in districts:
            if district.lower() in text_lower:
                return district
    return "Белград"


def extract_listing_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    text = clean_text(raw.get("source_text") or raw.get("title") or "")
    text_lower = text.lower()
    description_features = extract_from_description(text)

    price = raw.get("price_eur") or parse_price(raw.get("price_raw")) or parse_price(text)
    rooms = raw.get("rooms_count") or detect_rooms_count(text)
    beds = raw.get("beds_count") or detect_beds_count(text)
    area = raw.get("area_m2") or detect_area(text)
    floor = raw.get("floor") or detect_floor(text)
    district = raw.get("district") or detect_district(text, raw.get("url", ""))

    return {
        "site": raw.get("site", ""),
        "title": raw.get("title", ""),
        "url": raw.get("url", ""),
        "price_eur": price or 0.0,
        "price_text": raw.get("price_text") or "",
        "posted_date": raw.get("posted_date") or "",
        "rooms_count": rooms,
        "beds_count": beds,
        "pets_allowed": description_features["pets_allowed"],
        "furnished": description_features["furnished"],
        "washer_machine": description_features["washing_machine"],
        "dishwasher": description_features["dishwasher"],
        "washing_machine": description_features["washing_machine"],
        "kitchen_separate": description_features["kitchen"],
        "hot_water": description_features["hot_water"],
        "wifi": description_features["wifi"],
        "fridge": description_features["fridge"],
        "stove": description_features["stove"],
        "oven": description_features["oven"],
        "beds_for_all": description_features["beds_for_all"],
        "area_m2": area,
        "floor": floor,
        "district": district,
        "pet_fee_eur": detect_pet_fee(text),
        "min_lease_months": detect_min_lease(text),
        "source_text": text,
        "raw": raw,
    }
