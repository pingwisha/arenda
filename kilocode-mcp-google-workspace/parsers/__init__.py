from typing import Any, Dict
from .halooglasi import validate as validate_halooglasi

SITE_PARSERS = {
    "halooglasi.com": validate_halooglasi,
    "4zida.rs": None,
    "cityexpert.rs": None,
    "imovina.net": None,
    "nekretnine.rs": None,
    "oglasi.rs": None,
    "airbnb.com": None,
}


def detect_site(url: str) -> str:
    for domain in SITE_PARSERS:
        if domain in url:
            return domain
    return ""


def validate_listing(url: str) -> Dict[str, Any]:
    domain = detect_site(url)
    if not domain:
        return {"status": "unsupported_site", "url": url}
    parser = SITE_PARSERS[domain]
    if parser is None:
        return {"status": "parser_not_implemented", "site": domain, "url": url}
    return parser(url)
