from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path

import openpyxl


SOURCE_CLOCK_MHZ = 175.0
CONFIG_SHEET = "config"
POWER_NET_COUNT = 8
RESULT_CSV = Path("static_60us_measurement_comparison.csv")


MEASUREMENTS: tuple[tuple[str, str, int], ...] = (
    ("3.3V_DIG", "CDS1↓ to SW↑", -189),
    ("3.3V_DIG", "CDS1↓ to SW↓", 109),
    ("3.3V_DIG", "CDS2↓ to SW↑", -109),
    ("3.3V_DIG", "CDS2↓ to SW↓", 190),
    ("R2.5V_AMP", "CDS1↓ to SW↑", -202),
    ("R2.5V_AMP", "CDS1↓ to SW↓", 160),
    ("R2.5V_AMP", "CDS2↓ to SW↑", -122),
    ("R2.5V_AMP", "CDS2↓ to SW↓", -236),
    ("0.85V_PS", "CDS1↓ to SW↑", -211),
    ("0.85V_PS", "CDS1↓ to SW↓", -82),
    ("0.85V_PS", "CDS2↓ to SW↑", -130),
    ("0.85V_PS", "CDS2↓ to SW↓", -57),
    ("0.85V_PL", "CDS1↓ to SW↑", 42),
    ("0.85V_PL", "CDS1↓ to SW↓", 119),
    ("0.85V_PL", "CDS2↓ to SW↑", 122),
    ("0.85V_PL", "CDS2↓ to SW↓", 198),
    ("1.1V_DDRIO", "CDS1↓ to SW↑", -211),
    ("1.1V_DDRIO", "CDS1↓ to SW↓", -113),
    ("1.1V_DDRIO", "CDS2↓ to SW↑", -131),
    ("1.1V_DDRIO", "CDS2↓ to SW↓", -32),
    ("3.3V_WLAN", "CDS1↓ to SW↑", -192),
    ("3.3V_WLAN", "CDS1↓ to SW↓", 107),
    ("3.3V_WLAN", "CDS2↓ to SW↑", -112),
    ("3.3V_WLAN", "CDS2↓ to SW↓", 186),
    ("4.3V_CHG", "CDS1↓ to SW↑", -128),
    ("4.3V_CHG", "CDS1↓ to SW↓", 47),
    ("4.3V_CHG", "CDS2↓ to SW↑", -51),
    ("4.3V_CHG", "CDS2↓ to SW↓", 124),
    ("1.8V_DIG", "CDS1↓ to SW↑", -212),
    ("1.8V_DIG", "CDS1↓ to SW↓", -47),
    ("1.8V_DIG", "CDS2↓ to SW↑", -131),
    ("1.8V_DIG", "CDS2↓ to SW↓", 29),
    ("5.5V_CHG", "CDS1↓ to SW↑", 90),
    ("5.5V_CHG", "CDS1↓ to SW↓", -42),
    ("5.5V_CHG", "CDS2↓ to SW↑", 170),
    ("5.5V_CHG", "CDS2↓ to SW↓", 38),
    ("D5V_1", "CDS1↓ to SW↑", 50),
    ("D5V_1", "CDS1↓ to SW↓", -43),
    ("D5V_1", "CDS2↓ to SW↑", 131),
    ("D5V_1", "CDS2↓ to SW↓", 37),
    ("D5V_2", "CDS1↓ to SW↑", 55),
    ("D5V_2", "CDS1↓ to SW↓", -41),
    ("D5V_2", "CDS2↓ to SW↑", 135),
    ("D5V_2", "CDS2↓ to SW↓", 39),
    ("D5V_3", "CDS1↓ to SW↑", 61),
    ("D5V_3", "CDS1↓ to SW↓", -44),
    ("D5V_3", "CDS2↓ to SW↑", 142),
    ("D5V_3", "CDS2↓ to SW↓", 36),
    ("A6V", "CDS1↓ to SW↑", 103),
    ("A6V", "CDS1↓ to SW↓", -37),
    ("A6V", "CDS2↓ to SW↑", 183),
    ("A6V", "CDS2↓ to SW↓", 43),
    ("A3V", "CDS1↓ to SW↑", -26),
    ("A3V", "CDS1↓ to SW↓", -136),
    ("A3V", "CDS2↓ to SW↑", 53),
    ("A3V", "CDS2↓ to SW↓", -55),
    ("M15V", "CDS1↓ to SW↑", -118),
    ("M15V", "CDS1↓ to SW↓", 21),
    ("M15V", "CDS2↓ to SW↑", -40),
    ("M15V", "CDS2↓ to SW↓", 100),
    ("A20V", "CDS1↓ to SW↑", 221),
    ("A20V", "CDS1↓ to SW↓", -161),
    ("A20V", "CDS2↓ to SW↑", -180),
    ("A20V", "CDS2↓ to SW↓", -83),
)


@dataclass(frozen=True)
class NetConfig:
    workbook: str
    index: int
    name: str
    pl_delay_ns: float
    period_ns: float
    duty_percent: float
    delay_ns: float
    cds1_fall_us: float
    cds2_fall_us: float


def evaluate_formula(value: object, cells: dict[str, object]) -> object:
    if not isinstance(value, str) or not value.startswith("="):
        return value
    formula = value.replace(" ", "").upper()
    match = re.fullmatch(r"=ROUND\(\(1/175\)\*([A-Z]+[1-9][0-9]*)\*10\^3,1\)", formula)
    if match:
        return round((1 / SOURCE_CLOCK_MHZ) * float(cells[match.group(1)]) * 10**3, 1)
    return value


def load_config(path: Path) -> dict[str, object]:
    wb = openpyxl.load_workbook(path, read_only=False, data_only=False)
    ws = wb[CONFIG_SHEET]
    rows = list(ws.iter_rows())
    headers = [str(cell.value).strip().lower() if cell.value is not None else "" for cell in rows[0]]
    parameter_col = headers.index("parameter")
    value_col = headers.index("value")
    raw: dict[str, object] = {}
    cells: dict[str, object] = {}
    for row in rows[1:]:
        key = row[parameter_col].value
        value_cell = row[value_col]
        if key is None or not str(key).strip():
            continue
        raw[str(key).strip()] = value_cell.value
        cells[value_cell.coordinate] = value_cell.value
    wb.close()
    return {key: evaluate_formula(value, cells) for key, value in raw.items()}


def load_net_configs() -> dict[str, NetConfig]:
    configs: dict[str, NetConfig] = {}
    for path in sorted(Path(".").glob("静止画_60us_CLK*.xlsx")):
        data = load_config(path)
        period_ns = float(data["clock_div_ratio"]) / SOURCE_CLOCK_MHZ * 1000.0
        for index in range(POWER_NET_COUNT):
            name = str(data.get(f"power_net_name_{index}") or "").strip()
            if not name:
                continue
            configs[name] = NetConfig(
                workbook=path.name,
                index=index,
                name=name,
                pl_delay_ns=float(data["pl_dcdc_clk_delay_ns"]),
                period_ns=period_ns,
                duty_percent=float(data[f"power_net_duty_percent_{index}"]),
                delay_ns=float(data[f"power_net_delay_ns_{index}"]),
                cds1_fall_us=float(data["cds1_fall_us"]),
                cds2_fall_us=float(data["cds2_fall_us"]),
            )
    return configs


def nearest_edge_delta_ns(target_us: float, first_edge_ns: float, period_ns: float) -> float:
    target_ns = target_us * 1000.0
    nearest_index = round((target_ns - first_edge_ns) / period_ns)
    candidates = [
        first_edge_ns + index * period_ns
        for index in (nearest_index - 1, nearest_index, nearest_index + 1)
        if index >= 0
    ]
    if not candidates:
        candidates.append(first_edge_ns)
    nearest = min(candidates, key=lambda edge_ns: abs(edge_ns - target_ns))
    return nearest - target_ns


def predictions(config: NetConfig) -> dict[str, float]:
    rise_ns = config.pl_delay_ns + config.delay_ns
    fall_ns = rise_ns + config.period_ns * config.duty_percent / 100.0
    return {
        "CDS1↓ to SW↑": nearest_edge_delta_ns(config.cds1_fall_us, rise_ns, config.period_ns),
        "CDS1↓ to SW↓": nearest_edge_delta_ns(config.cds1_fall_us, fall_ns, config.period_ns),
        "CDS2↓ to SW↑": nearest_edge_delta_ns(config.cds2_fall_us, rise_ns, config.period_ns),
        "CDS2↓ to SW↓": nearest_edge_delta_ns(config.cds2_fall_us, fall_ns, config.period_ns),
    }


def wrapped_diff_ns(calculated_ns: float, measured_ns: float, period_ns: float) -> float:
    return (calculated_ns - measured_ns + period_ns / 2.0) % period_ns - period_ns / 2.0


def main() -> None:
    configs = load_net_configs()
    rows: list[dict[str, object]] = []
    residuals: list[float] = []
    for net, edge, measured_ns in MEASUREMENTS:
        config = configs[net]
        calculated_ns = predictions(config)[edge]
        raw_diff_ns = calculated_ns - measured_ns
        diff_ns = wrapped_diff_ns(calculated_ns, measured_ns, config.period_ns)
        residuals.append(diff_ns)
        rows.append(
            {
                "workbook": config.workbook,
                "index": config.index,
                "net": net,
                "edge": edge,
                "measured_ns": measured_ns,
                "calculated_ns": round(calculated_ns, 2),
                "raw_diff_calc_minus_measured_ns": round(raw_diff_ns, 2),
                "wrapped_diff_calc_minus_measured_ns": round(diff_ns, 2),
            }
        )
    with RESULT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    by_net: dict[str, list[float]] = {}
    for row in rows:
        by_net.setdefault(str(row["net"]), []).append(
            float(row["wrapped_diff_calc_minus_measured_ns"])
        )

    print(f"Wrote {RESULT_CSV}")
    print(
        "Overall: "
        f"RMS={math.sqrt(sum(value * value for value in residuals) / len(residuals)):.2f} ns, "
        f"max_abs={max(abs(value) for value in residuals):.2f} ns"
    )
    for net, values in by_net.items():
        rms = math.sqrt(sum(value * value for value in values) / len(values))
        print(f"{net}: RMS={rms:.2f} ns, max_abs={max(abs(value) for value in values):.2f} ns")


if __name__ == "__main__":
    main()
