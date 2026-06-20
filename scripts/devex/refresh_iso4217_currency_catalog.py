from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

LIST_ONE_XML_URL = (
    "https://www.six-group.com/dam/download/financial-information/"
    "data-center/iso-currrency/lists/list-one.xml"
)
OUTPUT_PATH = Path("src/wallet/domain/_iso4217_snapshot.py")

# Product scope: keep active end-user currencies only and exclude current ISO fund,
# metal, testing, and supranational-unit style codes from the runtime catalog.
EXCLUDED_ENTITY_NAMES = {
    "ARAB MONETARY FUND",
    "INTERNATIONAL MONETARY FUND (IMF)",
    "MEMBER COUNTRIES OF THE AFRICAN DEVELOPMENT BANK GROUP",
    'SISTEMA UNITARIO DE COMPENSACION REGIONAL DE PAGOS "SUCRE"',
}


@dataclass(frozen=True, slots=True)
class CurrencyRow:
    code: str
    numeric_code: str
    name: str
    minor_unit: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the checked-in ISO 4217 currency snapshot."
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the generated module instead of writing it to disk.",
    )
    return parser.parse_args()


def _fetch_xml(url: str) -> bytes:
    with urlopen(url) as response:
        return response.read()


def _normalize_entity_name(value: str | None) -> str:
    if value is None:
        return ""
    return value.replace("\xa0", " ").strip()


def _extract_rows(xml_payload: bytes) -> tuple[str, tuple[CurrencyRow, ...]]:
    root = ET.fromstring(xml_payload)
    published = root.attrib["Pblshd"]
    rows_by_code: dict[str, CurrencyRow] = {}

    for entry in root.findall(".//CcyNtry"):
        code = entry.findtext("Ccy")
        if code is None:
            continue

        entity_name = _normalize_entity_name(entry.findtext("CtryNm"))
        currency_name_node = entry.find("CcyNm")
        currency_name = currency_name_node.text if currency_name_node is not None else None
        numeric_code = entry.findtext("CcyNbr")
        minor_unit_text = entry.findtext("CcyMnrUnts")
        is_fund = (
            currency_name_node is not None and currency_name_node.attrib.get("IsFund") == "true"
        )

        if (
            is_fund
            or entity_name in EXCLUDED_ENTITY_NAMES
            or currency_name is None
            or numeric_code is None
            or minor_unit_text is None
            or not minor_unit_text.isdigit()
        ):
            continue

        rows_by_code.setdefault(
            code,
            CurrencyRow(
                code=code,
                numeric_code=numeric_code,
                name=currency_name,
                minor_unit=int(minor_unit_text),
            ),
        )

    rows = tuple(sorted(rows_by_code.values(), key=lambda row: row.code))
    return published, rows


def _render_module(published: str, rows: tuple[CurrencyRow, ...]) -> str:
    lines = [
        '"""Generated from the SIX ISO 4217 List One XML snapshot."""',
        "",
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True, slots=True)",
        "class Iso4217CurrencyRow:",
        "    code: str",
        "    numeric_code: str",
        "    name: str",
        "    minor_unit: int",
        "",
        f'ISO4217_PUBLISHED = "{published}"',
        "_ISO4217_ACTIVE_CURRENCY_ROW_VALUES = (",
    ]
    for row in rows:
        lines.append(f'    ("{row.code}", "{row.numeric_code}", "{row.name}", {row.minor_unit}),')
    lines.append(")")
    lines.append("")
    lines.append("ISO4217_ACTIVE_CURRENCIES = tuple(")
    lines.append("    Iso4217CurrencyRow(code, numeric_code, name, minor_unit)")
    lines.append(
        "    for code, numeric_code, name, minor_unit in _ISO4217_ACTIVE_CURRENCY_ROW_VALUES"
    )
    lines.append(")")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    published, rows = _extract_rows(_fetch_xml(LIST_ONE_XML_URL))
    module_text = _render_module(published, rows)

    if args.stdout:
        print(module_text)
        return 0

    OUTPUT_PATH.write_text(module_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
