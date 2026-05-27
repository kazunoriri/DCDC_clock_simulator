from __future__ import annotations

import copy
import posixpath
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


CONFIG_DIR = Path("設定ファイル")
BACKUP_DIR = CONFIG_DIR / "バックアップ"
CONFIG_SHEET_XML = "xl/worksheets/sheet1.xml"
STYLES_XML = "xl/styles.xml"
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

MEASURED_DELAYS_NS: dict[str, float] = {
    "3.3V_DIG": 44.0,
    "R2.5V_AMP": 30.0,
    "0.85V_PS": 24.0,
    "0.85V_PL": 274.0,
    "1.1V_DDRIO": 24.0,
    "3.3V_WLAN": 24.0,
    "4.3V_CHG": 42.0,
    "1.8V_DIG": 24.0,
    "5.5V_CHG": 170.0,
    "D5V_1": 130.0,
    "D5V_2": 138.0,
    "D5V_3": 142.0,
    "A6V": 186.0,
    "A3V": 62.0,
    "M15V": 330.0,
    "A20V": 306.0,
}

ET.register_namespace("", MAIN_NS)
NS = {"x": MAIN_NS}


def qname(tag: str) -> str:
    return f"{{{MAIN_NS}}}{tag}"


def cell_ref(column: str, row_index: int) -> str:
    return f"{column}{row_index}"


def row_number(cell_reference: str) -> int:
    match = re.fullmatch(r"[A-Z]+([0-9]+)", cell_reference)
    if match is None:
        raise ValueError(f"Invalid cell reference: {cell_reference}")
    return int(match.group(1))


def cell_text(cell: ET.Element | None) -> str:
    if cell is None:
        return ""
    inline_text = cell.find("x:is/x:t", NS)
    if inline_text is not None and inline_text.text is not None:
        return inline_text.text
    value = cell.find("x:v", NS)
    return value.text if value is not None and value.text is not None else ""


def numeric_text(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


def ensure_value_cell(row: ET.Element, reference: str) -> ET.Element:
    for cell in row.findall("x:c", NS):
        if cell.get("r") == reference:
            return cell

    cell = ET.Element(qname("c"), {"r": reference})
    cells = row.findall("x:c", NS)
    row_index = row_number(reference)
    inserted = False
    for index, existing in enumerate(cells):
        existing_ref = existing.get("r", "")
        if row_number(existing_ref) == row_index and existing_ref > reference:
            row.insert(list(row).index(existing), cell)
            inserted = True
            break
    if not inserted:
        row.append(cell)
    return cell


def set_numeric_cell(cell: ET.Element, value: float) -> None:
    for child in list(cell):
        cell.remove(child)
    cell.set("t", "n")
    value_element = ET.SubElement(cell, qname("v"))
    value_element.text = numeric_text(value)


def centered_style_map(styles_root: ET.Element) -> dict[int, int]:
    cell_xfs = styles_root.find("x:cellXfs", NS)
    if cell_xfs is None:
        raise ValueError("styles.xml does not contain cellXfs")

    original_xfs = list(cell_xfs.findall("x:xf", NS))
    style_map: dict[int, int] = {}
    for style_index, xf in enumerate(original_xfs):
        centered_xf = copy.deepcopy(xf)
        centered_xf.set("applyAlignment", "1")
        alignment = centered_xf.find("x:alignment", NS)
        if alignment is None:
            alignment = ET.SubElement(centered_xf, qname("alignment"))
        alignment.set("horizontal", "center")
        cell_xfs.append(centered_xf)
        style_map[style_index] = len(cell_xfs.findall("x:xf", NS)) - 1

    cell_xfs.set("count", str(len(cell_xfs.findall("x:xf", NS))))
    return style_map


def center_b_column(sheet_root: ET.Element, style_map: dict[int, int]) -> None:
    sheet_data = sheet_root.find("x:sheetData", NS)
    if sheet_data is None:
        raise ValueError("sheet1.xml does not contain sheetData")

    for row in sheet_data.findall("x:row", NS):
        row_index = int(row.get("r", "0"))
        if row_index <= 0:
            continue
        cell = ensure_value_cell(row, cell_ref("B", row_index))
        current_style = int(cell.get("s", "0"))
        cell.set("s", str(style_map[current_style]))


def update_measured_delays(sheet_root: ET.Element) -> None:
    sheet_data = sheet_root.find("x:sheetData", NS)
    if sheet_data is None:
        raise ValueError("sheet1.xml does not contain sheetData")

    parameters: dict[str, ET.Element] = {}
    values_by_key: dict[str, str] = {}
    for row in sheet_data.findall("x:row", NS):
        row_index = int(row.get("r", "0"))
        key = cell_text(row.find("x:c[@r='A{}']".format(row_index), NS))
        if not key:
            continue
        value_cell = ensure_value_cell(row, cell_ref("B", row_index))
        parameters[key] = value_cell
        values_by_key[key] = cell_text(value_cell)

    for index in range(8):
        name = values_by_key.get(f"power_net_name_{index}", "").strip()
        delay_key = f"power_net_delay_ns_{index}"
        if name in MEASURED_DELAYS_NS and delay_key in parameters:
            set_numeric_cell(parameters[delay_key], MEASURED_DELAYS_NS[name])


def patch_workbook(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(source, "r") as zin:
        styles_root = ET.fromstring(zin.read(STYLES_XML))
        sheet_root = ET.fromstring(zin.read(CONFIG_SHEET_XML))
        style_map = centered_style_map(styles_root)
        update_measured_delays(sheet_root)
        center_b_column(sheet_root, style_map)

        temporary = destination.with_suffix(destination.suffix + ".tmp")
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == STYLES_XML:
                    data = ET.tostring(styles_root, encoding="utf-8", xml_declaration=False)
                elif item.filename == CONFIG_SHEET_XML:
                    data = ET.tostring(sheet_root, encoding="utf-8", xml_declaration=False)
                zout.writestr(item, data)
        shutil.move(temporary, destination)


def target_paths() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for source in sorted(BACKUP_DIR.glob("*/*.xlsx")):
        relative = source.relative_to(BACKUP_DIR)
        destination = CONFIG_DIR / relative
        pairs.append((source, destination))
    return pairs


def main() -> None:
    pairs = target_paths()
    if not pairs:
        raise SystemExit(f"No backup Excel files found under {BACKUP_DIR}")

    for source, destination in pairs:
        destination.parent.mkdir(parents=True, exist_ok=True)
        patch_workbook(source, destination)
        print(f"patched {posixpath.join(*destination.parts[-2:])}")


if __name__ == "__main__":
    main()
