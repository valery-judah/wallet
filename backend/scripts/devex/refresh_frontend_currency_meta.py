from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen

LIST_ONE_XML_URL = (
    "https://www.six-group.com/dam/download/financial-information/"
    "data-center/iso-currrency/lists/list-one.xml"
)
REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = REPO_ROOT / "frontend/src/lib/generated-currency-meta.ts"

EXCLUDED_ENTITY_NAMES = {
    "ARAB MONETARY FUND",
    "INTERNATIONAL MONETARY FUND (IMF)",
    "MEMBER COUNTRIES OF THE AFRICAN DEVELOPMENT BANK GROUP",
    'SISTEMA UNITARIO DE COMPENSACION REGIONAL DE PAGOS "SUCRE"',
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the frontend ISO 4217 currency precision catalog."
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the generated file instead of writing it to disk.",
    )
    return parser.parse_args()


def _fetch_xml(url: str) -> bytes:
    with urlopen(url) as response:
        return response.read()


def _normalize_entity_name(value: str | None) -> str:
    if value is None:
        return ""
    return value.replace("\xa0", " ").strip()


def _extract_minor_units(xml_payload: bytes) -> dict[str, int]:
    root = ET.fromstring(xml_payload)
    rows_by_code: dict[str, int] = {}

    for entry in root.findall(".//CcyNtry"):
        code = entry.findtext("Ccy")
        if code is None:
            continue

        entity_name = _normalize_entity_name(entry.findtext("CtryNm"))
        currency_name_node = entry.find("CcyNm")
        minor_unit_text = entry.findtext("CcyMnrUnts")
        is_fund = (
            currency_name_node is not None and currency_name_node.attrib.get("IsFund") == "true"
        )

        if (
            is_fund
            or entity_name in EXCLUDED_ENTITY_NAMES
            or minor_unit_text is None
            or not minor_unit_text.isdigit()
        ):
            continue

        rows_by_code.setdefault(code, int(minor_unit_text))

    return dict(sorted(rows_by_code.items()))


def _render_module(minor_units: dict[str, int]) -> str:
    lines = [
        "/*",
        " * Generated from the SIX ISO 4217 List One XML snapshot.",
        " * Refresh with:",
        " * `uv --directory backend run python scripts/devex/refresh_frontend_currency_meta.py`",
        " */",
        "",
        "export const CURRENCY_MINOR_UNIT_BY_CODE: Record<string, number> = {",
    ]

    for code, minor_unit in minor_units.items():
        lines.append(f"  {code}: {minor_unit},")

    lines.extend(
        [
            "}",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    minor_units = _extract_minor_units(_fetch_xml(LIST_ONE_XML_URL))
    module_text = _render_module(minor_units)

    if args.stdout:
        print(module_text)
        return 0

    OUTPUT_PATH.write_text(module_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
