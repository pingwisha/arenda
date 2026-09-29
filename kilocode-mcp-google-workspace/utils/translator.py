from __future__ import annotations

import re
from typing import Optional


TRANSLATIONS = {
    "kitchen": "кухня",
    "kitchenette": "кухня",
    "washer": "стиральная машина",
    "washing machine": "стиральная машина",
    "dishwasher": "посудомоечная машина",
    "wifi": "wi-fi",
    "internet": "интернет",
    "fridge": "холодильник",
    "refrigerator": "холодильник",
    "stove": "плита",
    "oven": "духовка",
    "hot water": "горячая вода",
    "bed": "кровать",
    "sofa": "диван",
    "furnished": "меблирован",
    "pet friendly": "разрешены животные",
    "pets allowed": "разрешены животные",
    "dog": "собака",
    "cat": "кошка",
    "apartment": "квартира",
    "house": "дом",
    "studio": "студия",
    "bedroom": "спальня",
    "bathroom": "ванная",
    "floor": "этаж",
    "elevator": "лифт",
    "balcony": "балкон",
    "terrace": "терасса",
    "parking": "парковка",
    "air conditioning": "кондиционер",
    "heating": "отопление",
    "deposit": "залог",
    "commission": "комиссия",
    "utilities": "коммуналка",
    "electricity": "электричество",
    "water": "вода",
    "Belgrade": "Белград",
    "Vračar": "Врачар",
    "Novi Beograd": "Новый Белград",
    "Stari Grad": "Старый город",
    "Zemun": "Земун",
    "Dedinje": "Дединье",
    "Senjak": "Сеняк",
    "Karaburma": "Карабурма",
    "Konjarnik": "Конярник",
    "Mirijevo": "Миријево",
    "Braće Jerković": "Братья Джеркович",
    "Bežanija": "Бежания",
    "Kalemegdan": "Калемегдан",
    "Krnjača": "Крняча",
    "Palilula": "Палилула",
    "Voždovac": "Вождовац",
    "Čukarica": "Чукарица",
    "Rakovica": "Раковица",
    "Zvezdara": "Звездара",
    "Savski Venac": "Савски венац",
    "Grocka": "Гроцка",
    "Lazarevac": "Лазаревац",
    "Mladenovac": "Младеновац",
    "Obrenovac": "Обреновац",
    "Sopot": "Сопот",
    "Surčin": "Сурчин",
    "Altina": "Алтына",
    "Plavi Horizonti": "Плави Хоризонти",
    "Bežanijska Kosa": "Бежанијска Коса",
    "Jovanova": "Йованова",
    "Ledine": "Ледине",
    "Novo Beograd": "Новый Белград",
    "Studentski Grad": "Студенческий город",
    "Vidikovačka Padina": "Видиковачка Падина",
    "Banjica": "Баница",
    "Kumodraž": "Кумодраж",
    "Leštane": "Лештане",
    "Veliki Mokri Lug": "Велики Мокри Луг",
    "Beli Potok": "Бели Поток",
    "Pinosava": "Пиносава",
    "Ripanj": "Рипань",
    "Ralja": "Раља",
    "Umčari": "Умчари",
    "Železnik": "Железник",
    "Žarkovo": "Жарково",
    "Košutnjak": "Кошутняк",
    "Banovo Brdo": "Баново Брдо",
    "Topčidersko Brdo": "Топчидерско Брдо",
    "Senjski Rudnik": "Сеньски Рудник",
    "Ripanj": "Рипань",
}


def translate_text(text: str) -> str:
    if not text:
        return ""
    result = text
    for eng, rus in TRANSLATIONS.items():
        result = re.sub(re.escape(eng), rus, result, flags=re.IGNORECASE)
    return result


def translate_listing(listing: dict) -> dict:
    result = dict(listing)
    for key in ["title", "district", "address", "property_type", "furniture_desc", "notes", "source_text"]:
        if key in result and result[key]:
            result[key] = translate_text(str(result[key]))
    return result
