from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


@dataclass
class Listing:
    id: str
    platform: str
    url: str
    title: str = ""
    district: str = ""
    address: str = ""
    property_type: str = "Квартира"
    rooms: int = 0
    kitchen: bool = False
    area_m2: Optional[float] = None
    floor: str = ""
    price_eur: float = 0.0
    price_text: str = ""
    currency: str = "EUR"
    posted_date: str = ""
    is_match: bool = False
    utilities_eur: Optional[float] = None
    electricity_included: Optional[bool] = None
    deposit_eur: Optional[float] = None
    deposit_refundable: bool = True
    other_payments: str = ""
    total_cost_eur: Optional[float] = None
    payment_3_weeks: bool = False
    min_lease_months: str = ""
    dogs_allowed: bool = False
    cats_allowed: bool = False
    pet_fee_eur: float = 0.0
    fridge: bool = False
    stove: bool = False
    oven: bool = False
    washing_machine: bool = False
    dishwasher: bool = False
    hot_water: bool = False
    wifi: bool = False
    beds_for_all: bool = False
    furniture_desc: str = ""
    first_seen: Optional[date] = None
    found_date: Optional[date] = None
    last_updated: Optional[date] = None
    rented_date: Optional[date] = None
    days_on_market: int = 0
    current_price_eur: float = 0.0
    price_change_eur: float = 0.0
    status: str = "Активно"
    notes: str = ""
    source_text: str = ""
    raw: dict = field(default_factory=dict)

    def _ru(self, value: Optional[bool], unknown: bool = False) -> str:
        if value is None or (unknown and not value):
            return "не указано"
        return "да" if value else "нет"

    def to_sheet_row(self) -> List[object]:
        price_text = self.price_text or (f"{self.price_eur} EUR/мес" if self.price_eur else "")
        return [
            self.id,
            self.platform,
            self.url,
            self.posted_date or (self.first_seen.isoformat() if self.first_seen else ""),
            self.first_seen.isoformat() if self.first_seen else "",
            self.found_date.isoformat() if self.found_date else "",
            self.last_updated.isoformat() if self.last_updated else "",
            self.rented_date.isoformat() if self.rented_date else "",
            self.days_on_market,
            self.district,
            self.address,
            self.property_type,
            self.rooms,
            self._ru(self.kitchen, unknown=True),
            self.area_m2 if self.area_m2 is not None else "",
            self.floor,
            self.price_eur if self.price_eur else "",
            price_text,
            self.currency,
            self.utilities_eur if self.utilities_eur is not None else "",
            self._ru(self.electricity_included, unknown=True),
            self.deposit_eur if self.deposit_eur is not None else "",
            self._ru(self.deposit_refundable),
            self.other_payments,
            self.total_cost_eur if self.total_cost_eur is not None else "",
            self._ru(self.payment_3_weeks),
            self.min_lease_months,
            self._ru(self.dogs_allowed, unknown=True),
            self._ru(self.cats_allowed, unknown=True),
            self.pet_fee_eur if self.pet_fee_eur else "",
            self._ru(self.fridge, unknown=True),
            self._ru(self.stove, unknown=True),
            self._ru(self.oven, unknown=True),
            self._ru(self.washing_machine, unknown=True),
            self._ru(self.dishwasher, unknown=True),
            self._ru(self.hot_water, unknown=True),
            self._ru(self.wifi, unknown=True),
            self._ru(self.beds_for_all, unknown=True),
            self.furniture_desc,
            self.current_price_eur if self.current_price_eur else self.price_eur,
            self.price_change_eur,
            self.status,
            "да" if self.is_match else "нет",
            self.notes,
        ]
