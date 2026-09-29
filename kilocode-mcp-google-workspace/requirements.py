from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent


@dataclass
class Requirement:
    section: str
    item: str
    category: str
    keywords: List[str] = field(default_factory=list)
    prohibited_patterns: List[str] = field(default_factory=list)


def _parse_md(path: Path) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current_section = ""
    if not path.exists():
        return sections
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            if line.startswith("## "):
                current_section = line.lstrip("# ").strip()
                sections[current_section] = []
            continue
        if line.startswith("- "):
            item = line[2:].strip()
            if current_section:
                sections.setdefault(current_section, []).append(item)
    return sections


def _extend_keywords(item: str) -> List[str]:
    keywords = [kw.strip().lower() for kw in re.split(r"[/,]", item)]
    extended = list(keywords)
    for kw in keywords:
        if kw == "плита":
            extended.extend(["šporet", "rerna", "ploča", "plita", "kuhinjski elementi", "плин", "шпора"])
        elif kw == "холодильник":
            extended.extend(["frižider", "frizider", "zamrzivač", "фрижидер"])
        elif kw == "стиральная машина":
            extended.extend(["veš mašina", "ves mašina", "ves masina", "веш машину"])
        elif kw == "горячая вода":
            extended.extend(["topla voda", "topla vode", "топлу воду"])
        elif kw == "wi-fi":
            extended.extend(["wifi", "интернет", "bežični"])
        elif kw == "собака":
            extended.extend(["psa", "psi", "pas", "kućni ljubimci", "ljubimci"])
        elif kw == "кот":
            extended.extend(["mačka", "mačke", "macka", "кошка", "kućni ljubimci", "ljubimci"])
        elif kw == "белград":
            extended.extend(["beograd", "belgrade"])
        elif kw == "сербия":
            extended.extend(["serbia", "srbija"])
        elif kw == "посудомоечная машина":
            extended.extend(["sudomašina", "posudomachine", "suđa mašina", "sudomasina", "посудомойка"])
        elif kw == "2 спальни":
            extended.extend(["2 спальни", "две спальни", "2 sobe", "dve sobe", "dvosoban"])
        elif kw == "3 кровати":
            extended.extend(["3 кровати", "три кровати", "3 bed", "three beds", "ležaj", "lezaj"])
    return [kw for kw in extended if kw]


def _prohibited_for(item: str) -> List[str]:
    prohibited_map = {
        "собака": ["не допускаются животные", "без животных", "zabranjeni ljubimci", "bez ljubimaca", "nije dozvoljeno sa ljubimcima", "ljubimci nisu dozvoljeni", "bez psa", "bez mačke", "без собаки", "собаки нет", "нельзя с собакой"],
        "кот": ["не допускаются животные", "без животных", "zabranjeni ljubimci", "bez ljubimaca", "nije dozvoljeno sa ljubimcima", "ljubimci nisu dozvoljeni", "bez psa", "bez mačke", "без кота", "кота нет", "нельзя с котом"],
        "плита": ["нема плин", "нема шпора", "nema ploču", "no stove", "bez ploče", "nema šporet", "nema rernu", "без плиты", "плиты нет", "нет плиты"],
        "холодильник": ["нема фрижидера", "нема холодильник", "nema frižider", "no fridge", "nema frizider", "без холодильника", "холодильника нет", "нет холодильника"],
        "стиральная машина": ["нема веш машину", "nema veš mašinu", "no washing machine", "nema ves masinu", "без стиральной машины", "стиральной машины нет", "нет стиральной машины"],
        "горячая вода": ["нема топлу воду", "nema toplu vodu", "no hot water", "без горячей воды", "горячей воды нет", "нет горячей воды"],
        "wi-fi": ["нема wifi", "нема интернет", "nema wifi", "no wifi", "без wi-fi", "wi-fi нет", "нет wi-fi", "без интернета"],
        "посудомоечная машина": ["нема sudomašinu", "nema sudomasinu", "no dishwasher", "без посудомоечной машины", "посудомоечной машины нет"],
    }
    return prohibited_map.get(item.lower(), [])


class Requirements:
    def __init__(self) -> None:
        self.must_have: Dict[str, List[str]] = {}
        self.nice_to_have: Dict[str, List[str]] = {}
        self.items: List[Requirement] = []
        self.load()

    def load(self) -> None:
        self.must_have = _parse_md(WORKSPACE / "must_have.md")
        self.nice_to_have = _parse_md(WORKSPACE / "nice_to_have.md")
        self._build_items()

    def _build_items(self) -> None:
        self.items = []
        for section, items in self.must_have.items():
            for item in items:
                self.items.append(Requirement(
                    section=section,
                    item=item,
                    category="must_have",
                    keywords=_extend_keywords(item),
                    prohibited_patterns=_prohibited_for(item),
                ))
        for section, items in self.nice_to_have.items():
            for item in items:
                self.items.append(Requirement(
                    section=section,
                    item=item,
                    category="nice_to_have",
                    keywords=_extend_keywords(item),
                    prohibited_patterns=_prohibited_for(item),
                ))

    def get_items(self, category: Optional[str] = None) -> List[Requirement]:
        if category:
            return [r for r in self.items if r.category == category]
        return list(self.items)


def validate_requirements(text: str, requirements: Optional[Requirements] = None) -> Dict:
    if requirements is None:
        requirements = Requirements()
    lower_text = text.lower()
    present = []
    missing = []
    unknown = []
    prohibited = []
    for req in requirements.get_items():
        hit = any(kw in lower_text for kw in req.keywords if kw)
        is_prohibited = any(pat in lower_text for pat in req.prohibited_patterns if pat)
        if is_prohibited:
            prohibited.append({"section": req.section, "item": req.item, "category": req.category, "reason": "prohibited"})
        elif hit:
            present.append({"section": req.section, "item": req.item, "category": req.category})
        else:
            missing.append({"section": req.section, "item": req.item, "category": req.category})
    return {
        "present": present,
        "missing": missing,
        "unknown": unknown,
        "prohibited": prohibited,
        "passed": len(prohibited) == 0,
    }


def _build_draft_message(missing_must: List[Dict[str, str]], missing_nice: List[Dict[str, str]], site: str) -> Tuple[str, List[str], List[str]]:
    questions = []
    missing_to_ask = []

    missing_items = missing_must + missing_nice

    for item in missing_items:
        item_name = item.get("item", "").lower()
        if item_name in ["коммуналка", "utilities", "коммуналка eur"]:
            questions.append("iznos komunala")
            if "utilities_eur" not in missing_to_ask:
                missing_to_ask.append("utilities_eur")
        elif item_name in ["собака", "кот", "животные", "pet friendly"]:
            if item_name == "собака":
                questions.append("da li je dozvoljeno sa psom, i da li postoji naknada za zivotinje")
            elif item_name == "кот":
                questions.append("da li je dozvoljeno sa mačkom, i da li postoji naknada za zivotinje")
            else:
                questions.append("da li je dozvoljeno sa psom i mackom, i da li postoji naknada za zivotinje")
            if "pet_fee_eur" not in missing_to_ask:
                missing_to_ask.append("pet_fee_eur")
        elif item_name in ["плита", "кухня"]:
            questions.append("da li postoji kuhinja i plin/sporet")
            if "appliances_info" not in missing_to_ask:
                missing_to_ask.append("appliances_info")
        elif item_name == "холодильник":
            questions.append("da li postoji frižider")
            if "appliances_info" not in missing_to_ask:
                missing_to_ask.append("appliances_info")
        elif item_name == "стиральная машина":
            questions.append("da li postoji veš mašina")
            if "appliances_info" not in missing_to_ask:
                missing_to_ask.append("appliances_info")
        elif item_name == "горячая вода":
            questions.append("da li postoji topla voda")
        elif item_name in ["wi-fi", "интернет"]:
            questions.append("da li postoji wi-fi ili internet")
        elif item_name == "посудомоечная машина":
            questions.append("da li postoji sudomašina")
            if "appliances_info" not in missing_to_ask:
                missing_to_ask.append("appliances_info")
        elif item_name in ["2 спальни", "спальни", "sobe", "bedrooms"]:
            questions.append("koliko spavaci sobe ima")
        elif item_name in ["3 кровати", "кровати", "beds", "лежај"]:
            questions.append("da li postoji lezaj ili krevet za sve osobe")
            if "beds_info" not in missing_to_ask:
                missing_to_ask.append("beds_info")

    if not questions:
        return "", [], []

    draft_message = (
        "Zdravo, interesuje me ovaj stan. Mozete li da odgovorite na par pitanja: "
        + ", ".join(questions)
        + "? Hvala unapred."
    )
    return draft_message, questions, missing_to_ask
