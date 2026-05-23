from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import pyqtgraph as pg
from PyQt6 import QtCore, QtGui, QtWidgets


US_PER_NS = 0.001
POWER_MARGIN_RANGE_NS = 250.0
TITLE_FONT_SIZE_PT = 12
APP_FONT_SIZE_PT = 11
OUTER_MARGIN_PX = 12
GRAPH_SPACING_PX = 24
ROW_SPACING_PX = 14
CONTROL_ROW_HEIGHT_PX = 48
MAX_PL_DELAY_NS = 250.0
PLOT_BOTTOM_AXIS_HEIGHT_PX = 62
TIMING_LEFT_AXIS_WIDTH_PX = 120
MARGIN_LEFT_AXIS_WIDTH_PX = 75
SWEEP_LEFT_AXIS_WIDTH_PX = 75
MAX_POWER_TICK_LABEL_CHARS = 12
CONFIG_PATH = Path(__file__).with_name("timing_config.json")


@dataclass(frozen=True)
class PulseSignal:
    name: str
    pulses_us: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class PowerNet:
    name: str
    delay_ns: float
    duty_percent: float

    @property
    def duty(self) -> float:
        return self.duty_percent / 100.0


@dataclass(frozen=True)
class TimingConfig:
    pl_dcdc_clk_name: str = "PL_DCDC_CLK1"
    power_net_name_0: str = "3.3V_DIG"
    power_net_name_1: str = "3.3V_DIG_2"
    power_net_name_2: str = "3.3V_DIG_3"
    power_net_name_3: str = "3.3V_DIG_4"
    power_net_name_4: str = "3.3V_DIG_5"
    power_net_name_5: str = "3.3V_DIG_6"
    power_net_delay_ns_0: float | None = 0.0
    power_net_delay_ns_1: float | None = 10.0
    power_net_delay_ns_2: float | None = 20.0
    power_net_delay_ns_3: float | None = 30.0
    power_net_delay_ns_4: float | None = 40.0
    power_net_delay_ns_5: float | None = 50.0
    power_net_duty_percent_0: float | None = 35.0
    power_net_duty_percent_1: float | None = 42.5
    power_net_duty_percent_2: float | None = 50.0
    power_net_duty_percent_3: float | None = 57.5
    power_net_duty_percent_4: float | None = 65.0
    power_net_duty_percent_5: float | None = 72.5
    gate_period_us: float = 60.0
    cds1_rise_us: float = 1.0
    cds1_fall_us: float = 15.0
    cds2_rise_us: float = 30.0
    cds2_fall_us: float = 40.0
    clock_divider: int = 84


def load_timing_config(path: Path | None = None) -> TimingConfig:
    if path is None:
        path = CONFIG_PATH

    defaults = TimingConfig()
    if not path.exists():
        return defaults

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults

    def parse_str(key: str, default: str) -> str:
        value = data.get(key, default)
        return str(value) if value is not None else ""

    def parse_positive_float(key: str) -> float | None:
        if key not in data:
            return None
        try:
            value = float(data[key])
        except (TypeError, ValueError):
            return None
        return value if math.isfinite(value) and value >= 0.0 else None

    def parse_duty_percent(key: str) -> float | None:
        if key not in data:
            return None
        try:
            value = float(data[key])
        except (TypeError, ValueError):
            return None
        return value if math.isfinite(value) and 0.0 < value <= 100.0 else None

    try:
        values = {
            "pl_dcdc_clk_name": parse_str(
                "pl_dcdc_clk_name", defaults.pl_dcdc_clk_name
            ),
            "gate_period_us": float(data.get("gate_period_us", defaults.gate_period_us)),
            "cds1_rise_us": float(data.get("cds1_rise_us", defaults.cds1_rise_us)),
            "cds1_fall_us": float(data.get("cds1_fall_us", defaults.cds1_fall_us)),
            "cds2_rise_us": float(data.get("cds2_rise_us", defaults.cds2_rise_us)),
            "cds2_fall_us": float(data.get("cds2_fall_us", defaults.cds2_fall_us)),
            "clock_divider": int(data.get("clock_divider", defaults.clock_divider)),
        }
        for index in range(6):
            values[f"power_net_name_{index}"] = parse_str(
                f"power_net_name_{index}", getattr(defaults, f"power_net_name_{index}")
            )
            values[f"power_net_delay_ns_{index}"] = parse_positive_float(
                f"power_net_delay_ns_{index}"
            )
            values[f"power_net_duty_percent_{index}"] = parse_duty_percent(
                f"power_net_duty_percent_{index}"
            )
    except (TypeError, ValueError):
        return defaults

    if not values["pl_dcdc_clk_name"].strip():
        values["pl_dcdc_clk_name"] = defaults.pl_dcdc_clk_name
    if values["gate_period_us"] <= 0.0:
        values["gate_period_us"] = defaults.gate_period_us
    if values["cds1_rise_us"] >= values["cds1_fall_us"]:
        values["cds1_rise_us"] = defaults.cds1_rise_us
        values["cds1_fall_us"] = defaults.cds1_fall_us
    if values["cds2_rise_us"] >= values["cds2_fall_us"]:
        values["cds2_rise_us"] = defaults.cds2_rise_us
        values["cds2_fall_us"] = defaults.cds2_fall_us
    if values["clock_divider"] < 1:
        values["clock_divider"] = defaults.clock_divider

    return TimingConfig(**values)


def get_preferred_font_family() -> str:
    app = QtWidgets.QApplication.instance()
    if app is None:
        return "Sans Serif"

    families = set(QtGui.QFontDatabase.families())
    for family in (
        "Yu Gothic UI",
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Arial Unicode MS",
        "Meiryo",
    ):
        if family in families:
            return family
    return app.font().family()


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):  # noqa: N802
        if spacing >= 1:
            digits = 0
        elif spacing >= 0.1:
            digits = 1
        elif spacing >= 0.01:
            digits = 2
        elif spacing >= 0.001:
            digits = 3
        else:
            digits = 6

        labels = []
        for value in values:
            text = f"{value * scale:.{digits}f}"
            labels.append(text.rstrip("0").rstrip(".") if "." in text else text)
        return labels


def shorten_tick_label(text: str, max_chars: int = MAX_POWER_TICK_LABEL_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[: max_chars - 1] + "…"


def pulse_steps(
    pulses_us: tuple[tuple[float, float], ...],
    x_min_us: float,
    x_max_us: float,
    low: float,
    high: float,
) -> tuple[list[float], list[float]]:
    points: list[tuple[float, float]] = [(x_min_us, low)]
    for start_us, end_us in sorted(pulses_us):
        points.extend(
            [
                (start_us, low),
                (start_us, high),
                (end_us, high),
                (end_us, low),
            ]
        )
    points.append((x_max_us, low))
    x, y = zip(*points)
    return list(x), list(y)


def clock_steps(
    start_us: float,
    end_us: float,
    period_us: float,
    duty: float,
    low: float,
    high: float,
) -> tuple[list[float], list[float]]:
    x = [start_us]
    y = [low]
    t = start_us
    high_width = period_us * duty

    while t < end_us:
        rise = t
        fall = min(t + high_width, end_us)
        next_rise = min(t + period_us, end_us)
        x.extend([rise, rise, fall, fall, next_rise])
        y.extend([low, high, high, low, low])
        t += period_us

    return x, y


class TimingDiagram(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DCDC Clock Timing")
        self.resize(1760, 720)
        self.move(0, 0)

        self.x_min_us = -2.0
        self.row_gap = 1.05
        self.amplitude = 0.74
        self.source_clock_mhz = 175.0
        self.config = load_timing_config()
        self.gate_period_us = self.config.gate_period_us
        self.x_max_us = self.gate_period_us + 2.0
        self.pl_dcdc_clk_name = self.config.pl_dcdc_clk_name
        power_net_names = [
            self.config.power_net_name_0,
            self.config.power_net_name_1,
            self.config.power_net_name_2,
            self.config.power_net_name_3,
            self.config.power_net_name_4,
            self.config.power_net_name_5,
        ]
        power_net_delays_ns = [
            self.config.power_net_delay_ns_0,
            self.config.power_net_delay_ns_1,
            self.config.power_net_delay_ns_2,
            self.config.power_net_delay_ns_3,
            self.config.power_net_delay_ns_4,
            self.config.power_net_delay_ns_5,
        ]
        power_net_duty_percents = [
            self.config.power_net_duty_percent_0,
            self.config.power_net_duty_percent_1,
            self.config.power_net_duty_percent_2,
            self.config.power_net_duty_percent_3,
            self.config.power_net_duty_percent_4,
            self.config.power_net_duty_percent_5,
        ]
        self.power_nets = [
            PowerNet(name.strip(), delay_ns, duty_percent)
            for name, delay_ns, duty_percent in zip(
                power_net_names,
                power_net_delays_ns,
                power_net_duty_percents,
                strict=True,
            )
            if name.strip() and delay_ns is not None and duty_percent is not None
        ]
        self.power_net_names = [power_net.name for power_net in self.power_nets]
        self.power_net_name_0 = self.power_net_names[0] if self.power_net_names else ""
        self.clock_divider = self.config.clock_divider
        self.pl_clk1_delay_ns = 0.0
        self.cds1_start_us = self.config.cds1_rise_us
        self.cds1_end_us = self.config.cds1_fall_us
        self.cds2_start_us = self.config.cds2_rise_us
        self.cds2_end_us = self.config.cds2_fall_us
        self.font_family = get_preferred_font_family()
        self.app_font = QtGui.QFont(self.font_family, APP_FONT_SIZE_PT)
        self.pl_delay_candidates_ns = self.create_pl_delay_candidates_ns()
        self.row_names = [
            "CDS1",
            "CDS2",
            self.pl_dcdc_clk_name,
            *self.power_net_names,
        ]
        self.baselines: dict[str, float] = {}

        pg.setConfigOptions(antialias=True, background="k", foreground="#b8c3d1")

        central = QtWidgets.QWidget()
        central.setStyleSheet("background: #000000; color: #b8c3d1;")
        layout = QtWidgets.QGridLayout(central)
        layout.setContentsMargins(
            OUTER_MARGIN_PX,
            OUTER_MARGIN_PX,
            OUTER_MARGIN_PX,
            OUTER_MARGIN_PX,
        )
        layout.setHorizontalSpacing(GRAPH_SPACING_PX)
        layout.setVerticalSpacing(ROW_SPACING_PX)
        layout.setColumnStretch(0, 100)
        layout.setColumnStretch(1, 100)
        layout.setColumnStretch(2, 100)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 0)
        layout.setRowMinimumHeight(1, CONTROL_ROW_HEIGHT_PX)

        self.plot = pg.PlotWidget(axisItems={"bottom": TimeAxisItem(orientation="bottom")})
        self.margin_plot = pg.PlotWidget()
        self.delay_sweep_plot = pg.PlotWidget()
        layout.addWidget(self.plot, 0, 0)
        layout.addWidget(self.margin_plot, 0, 1)
        layout.addWidget(self.delay_sweep_plot, 0, 2)
        layout.addWidget(self.create_control_panel(), 1, 0)
        layout.addWidget(self.create_margin_legend(), 1, 1)
        layout.addWidget(QtWidgets.QWidget(), 1, 2)
        self.setCentralWidget(central)

        self.plot.setBackground("#000000")
        self.plot.showGrid(x=True, y=True, alpha=0.34)
        self.plot.setTitle(
            "Timing waveform",
            color="#b8c3d1",
            size=f"{TITLE_FONT_SIZE_PT}pt",
        )
        self.plot.setLabel(
            "bottom",
            "time [us]",
            **self.axis_label_style(),
        )
        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.setMenuEnabled(False)
        self.plot.getPlotItem().getViewBox().setBorder(pg.mkPen("#606060", width=1))

        bottom_axis = self.plot.getAxis("bottom")
        left_axis = self.plot.getAxis("left")
        for axis in (bottom_axis, left_axis):
            axis.setPen(pg.mkPen("#808080"))
            axis.setTextPen(pg.mkPen("#b8c3d1"))
            axis.setStyle(
                tickFont=self.app_font,
                tickTextOffset=8,
                autoExpandTextSpace=True,
            )
        bottom_axis.setHeight(PLOT_BOTTOM_AXIS_HEIGHT_PX)
        left_axis.setWidth(TIMING_LEFT_AXIS_WIDTH_PX)

        self.margin_plot.setBackground("#000000")
        self.margin_plot.showGrid(x=False, y=True, alpha=0.34)
        self.margin_plot.setLabel(
            "left",
            "delta [ns]",
            **self.axis_label_style(),
        )
        self.margin_plot.setLabel(
            "bottom",
            "電源名",
            **self.axis_label_style(),
        )
        self.margin_plot.setTitle(
            "CDS1,2↓ to switching edge delta",
            color="#b8c3d1",
            size=f"{TITLE_FONT_SIZE_PT}pt",
        )
        self.margin_plot.setMouseEnabled(x=False, y=False)
        self.margin_plot.setMenuEnabled(False)
        self.margin_plot.getPlotItem().getViewBox().setBorder(pg.mkPen("#606060", width=1))
        margin_bottom_axis = self.margin_plot.getAxis("bottom")
        margin_left_axis = self.margin_plot.getAxis("left")
        for axis in (margin_bottom_axis, margin_left_axis):
            axis.setPen(pg.mkPen("#808080"))
            axis.setTextPen(pg.mkPen("#b8c3d1"))
            axis.setStyle(
                tickFont=self.app_font,
                tickTextOffset=6,
                autoExpandTextSpace=True,
            )
        margin_bottom_axis.setHeight(PLOT_BOTTOM_AXIS_HEIGHT_PX)
        margin_left_axis.setWidth(MARGIN_LEFT_AXIS_WIDTH_PX)

        self.delay_sweep_plot.setBackground("#000000")
        self.delay_sweep_plot.showGrid(x=True, y=True, alpha=0.34)
        self.delay_sweep_plot.setLabel(
            "left",
            "delta [ns]",
            **self.axis_label_style(),
        )
        self.delay_sweep_plot.setLabel(
            "bottom",
            f"{self.pl_dcdc_clk_name} delay [ns]",
            **self.axis_label_style(),
        )
        self.delay_sweep_plot.setTitle(
            "delta vs delay",
            color="#b8c3d1",
            size=f"{TITLE_FONT_SIZE_PT}pt",
        )
        self.delay_sweep_plot.setMouseEnabled(x=True, y=False)
        self.delay_sweep_plot.setMenuEnabled(False)
        self.delay_sweep_plot.getPlotItem().getViewBox().setBorder(
            pg.mkPen("#606060", width=1)
        )
        sweep_bottom_axis = self.delay_sweep_plot.getAxis("bottom")
        sweep_left_axis = self.delay_sweep_plot.getAxis("left")
        for axis in (sweep_bottom_axis, sweep_left_axis):
            axis.setPen(pg.mkPen("#808080"))
            axis.setTextPen(pg.mkPen("#b8c3d1"))
            axis.setStyle(
                tickFont=self.app_font,
                tickTextOffset=6,
                autoExpandTextSpace=True,
            )
        sweep_bottom_axis.setHeight(PLOT_BOTTOM_AXIS_HEIGHT_PX)
        sweep_left_axis.setWidth(SWEEP_LEFT_AXIS_WIDTH_PX)

        self.draw()

    def axis_label_style(self) -> dict[str, str]:
        return {
            "color": "#b8c3d1",
            "font-size": f"{APP_FONT_SIZE_PT}pt",
            "font-family": self.font_family,
        }

    def create_control_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"""
            QLabel {{
                color: #b8c3d1;
                font-family: "{self.font_family}";
                font-size: {APP_FONT_SIZE_PT}pt;
            }}
            QLineEdit {{
                background: #555555;
                border: 1px solid #606060;
                color: #f1f5f9;
                font-family: "{self.font_family}";
                font-size: {APP_FONT_SIZE_PT}pt;
                padding: 2px 6px;
                selection-background-color: #1f6feb;
            }}
            QComboBox {{
                background: #555555;
                border: 1px solid #606060;
                color: #f1f5f9;
                font-family: "{self.font_family}";
                font-size: {APP_FONT_SIZE_PT}pt;
                padding: 2px 6px;
                selection-background-color: #1f6feb;
            }}
            QLabel#result {{
                color: #b8c3d1;
            }}
            """
        )
        self.control_panel = panel
        layout = QtWidgets.QHBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(12)

        self.frequency_label = QtWidgets.QLabel()
        self.frequency_label.setObjectName("result")
        self.update_frequency_label()
        self.pl_clk1_delay_combo = self.create_delay_combo()
        self.control_widgets_by_row: dict[str, QtWidgets.QWidget] = {}

        layout.addWidget(self.create_clock_editor(parent=panel))
        layout.addStretch(1)
        return panel

    def create_clock_editor(self, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
        editor = QtWidgets.QWidget(parent)
        layout = QtWidgets.QHBoxLayout(editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        status_label = QtWidgets.QLabel(f"{self.pl_dcdc_clk_name}: delay [ns]")
        layout.addWidget(status_label)
        layout.addWidget(self.pl_clk1_delay_combo)
        editor.adjustSize()
        return editor

    def create_margin_legend(self) -> QtWidgets.QWidget:
        legend = QtWidgets.QWidget()
        legend.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        layout = QtWidgets.QHBoxLayout(legend)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(18)

        entries = [
            ("△", "CDS1↓ to SW↑", "#58a6ff"),
            ("▽", "CDS1↓ to SW↓", "#58a6ff"),
            ("▲", "CDS2↓ to SW↑", "#f0883e"),
            ("▼", "CDS2↓ to SW↓", "#f0883e"),
        ]
        for marker, text, color in entries:
            label = QtWidgets.QLabel(f"{marker} {text}")
            label.setStyleSheet(
                f'color: {color}; font-family: "{self.font_family}"; '
                f"font-size: {APP_FONT_SIZE_PT}pt;"
            )
            layout.addWidget(label)
        layout.insertStretch(0, 1)
        layout.addStretch(1)
        return legend

    def create_pl_delay_candidates_ns(self) -> list[float]:
        candidates: list[float] = []
        source_period_ns = 1000.0 / self.source_clock_mhz
        step = 0
        while True:
            delay_ns = step * source_period_ns
            if delay_ns > MAX_PL_DELAY_NS + 1e-9:
                break
            candidates.append(delay_ns)
            step += 1
        return candidates

    def create_delay_combo(self) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        combo.setFixedWidth(86)
        for delay_ns in self.pl_delay_candidates_ns:
            combo.addItem(f"{delay_ns:.1f}", delay_ns)
        combo.currentIndexChanged.connect(self.apply_inputs)
        return combo

    @staticmethod
    def triangle_symbol(up: bool) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        if up:
            points = [
                QtCore.QPointF(0.0, -0.55),
                QtCore.QPointF(0.55, 0.55),
                QtCore.QPointF(-0.55, 0.55),
            ]
        else:
            points = [
                QtCore.QPointF(0.0, 0.55),
                QtCore.QPointF(0.55, -0.55),
                QtCore.QPointF(-0.55, -0.55),
            ]
        path.moveTo(points[0])
        path.lineTo(points[1])
        path.lineTo(points[2])
        path.closeSubpath()
        return path

    def draw(self) -> None:
        previous_x_range: list[float] | None = None
        previous_y_range: list[float] | None = None
        if self.baselines:
            previous_x_range, previous_y_range = self.plot.viewRange()

        self.plot.clear()

        signals = [
            PulseSignal("CDS1", ((self.cds1_start_us, self.cds1_end_us),)),
            PulseSignal("CDS2", ((self.cds2_start_us, self.cds2_end_us),)),
        ]

        waveform_pen = pg.mkPen("#ffff00", width=1)
        marker_pen = pg.mkPen("#8a8a8a", width=1, style=QtCore.Qt.PenStyle.DashLine)

        baselines = {
            name: (len(self.row_names) - index - 1) * self.row_gap
            for index, name in enumerate(self.row_names)
        }
        self.baselines = baselines
        half_amp = self.amplitude * 0.5
        clock_period_us = self.clock_divider / self.source_clock_mhz

        self.plot.getAxis("left").setTicks(
            [[(baselines[name], name) for name in self.row_names]]
        )

        for signal in signals:
            base = baselines[signal.name]
            x, y = pulse_steps(
                signal.pulses_us,
                0.0,
                self.gate_period_us,
                base - half_amp,
                base + half_amp,
            )
            self.plot.plot(x, y, pen=waveform_pen)

        pl_base = baselines[self.pl_dcdc_clk_name]
        pl_start_us = self.pl_clk1_delay_ns * US_PER_NS
        pl_x, pl_y = clock_steps(
            start_us=pl_start_us,
            end_us=self.gate_period_us,
            period_us=clock_period_us,
            duty=0.5,
            low=pl_base - half_amp,
            high=pl_base + half_amp,
        )
        if pl_start_us > 0.0:
            pl_x = [0.0, pl_start_us] + pl_x
            pl_y = [pl_base - half_amp, pl_base - half_amp] + pl_y
        self.plot.plot(pl_x, pl_y, pen=waveform_pen)

        for power_net in self.power_nets:
            dig_base = baselines[power_net.name]
            dig_start_us = (self.pl_clk1_delay_ns + power_net.delay_ns) * US_PER_NS
            dig_x, dig_y = clock_steps(
                start_us=dig_start_us,
                end_us=self.gate_period_us,
                period_us=clock_period_us,
                duty=power_net.duty,
                low=dig_base - half_amp,
                high=dig_base + half_amp,
            )
            if dig_start_us > 0.0:
                dig_x = [0.0, dig_start_us] + dig_x
                dig_y = [dig_base - half_amp, dig_base - half_amp] + dig_y
            self.plot.plot(dig_x, dig_y, pen=waveform_pen)
        self.draw_margin_plot(clock_period_us)
        self.draw_delay_sweep_plot(clock_period_us)

        self.add_time_markers(
            [0, self.cds1_end_us, self.cds2_end_us, self.gate_period_us],
            marker_pen,
        )

        if previous_x_range is None or previous_y_range is None:
            self.plot.setXRange(self.x_min_us, self.x_max_us, padding=0)
            self.plot.setYRange(
                min(baselines.values()) - 0.75,
                max(baselines.values()) + 0.75,
                padding=0,
            )
        else:
            self.plot.setXRange(previous_x_range[0], previous_x_range[1], padding=0)
            self.plot.setYRange(previous_y_range[0], previous_y_range[1], padding=0)

    def draw_margin_plot(self, clock_period_us: float) -> None:
        self.margin_plot.clear()
        self.margin_plot.getAxis("bottom").setTicks(
            [
                [
                    (index, shorten_tick_label(power_net.name))
                    for index, power_net in enumerate(self.power_nets)
                ]
            ]
        )
        power_net_count = len(self.power_nets)
        self.margin_plot.setXRange(
            -0.5,
            max(power_net_count - 0.5, 0.5),
            padding=0,
        )
        self.margin_plot.setYRange(
            -POWER_MARGIN_RANGE_NS,
            POWER_MARGIN_RANGE_NS,
            padding=0,
        )

        self.margin_plot.addItem(
            pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen("#d0d7de", width=2))
        )
        for value_ns in (-POWER_MARGIN_RANGE_NS, POWER_MARGIN_RANGE_NS):
            self.margin_plot.addItem(
                pg.InfiniteLine(
                    pos=value_ns,
                    angle=0,
                    pen=pg.mkPen("#8a8a8a", width=1, style=QtCore.Qt.PenStyle.DashLine),
                )
            )

        deltas = self.calculate_power_edge_deltas_ns(clock_period_us)
        series = [
            ("cds1_rise", -0.18, self.triangle_symbol(up=True), "#58a6ff", None),
            ("cds1_fall", -0.06, self.triangle_symbol(up=False), "#58a6ff", None),
            (
                "cds2_rise",
                0.06,
                self.triangle_symbol(up=True),
                "#f0883e",
                "#f0883e",
            ),
            (
                "cds2_fall",
                0.18,
                self.triangle_symbol(up=False),
                "#f0883e",
                "#f0883e",
            ),
        ]
        for key, x_offset, symbol, color, brush_color in series:
            x_values = [index + x_offset for index in range(len(deltas))]
            y_values = [entry[key] for entry in deltas]
            self.margin_plot.plot(
                x_values,
                y_values,
                pen=None,
                symbol=symbol,
                symbolSize=9,
                symbolPen=pg.mkPen(color, width=1.5),
                symbolBrush=pg.mkBrush(brush_color) if brush_color else None,
            )

    def draw_delay_sweep_plot(self, clock_period_us: float) -> None:
        self.delay_sweep_plot.clear()
        self.delay_sweep_plot.setXRange(-1.0, MAX_PL_DELAY_NS + 1.0, padding=0)
        self.delay_sweep_plot.setYRange(
            -POWER_MARGIN_RANGE_NS,
            POWER_MARGIN_RANGE_NS,
            padding=0,
        )
        self.delay_sweep_plot.addItem(
            pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen("#d0d7de", width=2))
        )
        for value_ns in (-POWER_MARGIN_RANGE_NS, POWER_MARGIN_RANGE_NS):
            self.delay_sweep_plot.addItem(
                pg.InfiniteLine(
                    pos=value_ns,
                    angle=0,
                    pen=pg.mkPen("#8a8a8a", width=1, style=QtCore.Qt.PenStyle.DashLine),
                )
            )

        series = [
            ("cds1_rise", -0.18, self.triangle_symbol(up=True), "#58a6ff", None),
            ("cds1_fall", -0.06, self.triangle_symbol(up=False), "#58a6ff", None),
            (
                "cds2_rise",
                0.06,
                self.triangle_symbol(up=True),
                "#f0883e",
                "#f0883e",
            ),
            (
                "cds2_fall",
                0.18,
                self.triangle_symbol(up=False),
                "#f0883e",
                "#f0883e",
            ),
        ]
        power_offsets = [
            (index - (len(self.power_nets) - 1) * 0.5) * 0.16
            for index in range(len(self.power_nets))
        ]

        for key, series_offset, symbol, color, brush_color in series:
            x_values: list[float] = []
            y_values: list[float] = []
            for delay_ns in self.pl_delay_candidates_ns:
                deltas = self.calculate_power_edge_deltas_ns(
                    clock_period_us,
                    pl_delay_ns=delay_ns,
                )
                for power_index, entry in enumerate(deltas):
                    x_values.append(
                        delay_ns + series_offset + power_offsets[power_index]
                    )
                    y_values.append(entry[key])

            self.delay_sweep_plot.plot(
                x_values,
                y_values,
                pen=None,
                symbol=symbol,
                symbolSize=7,
                symbolPen=pg.mkPen(color, width=1.2),
                symbolBrush=pg.mkBrush(brush_color) if brush_color else None,
            )

    def calculate_power_edge_deltas_ns(
        self,
        clock_period_us: float,
        pl_delay_ns: float | None = None,
    ) -> list[dict[str, float]]:
        if pl_delay_ns is None:
            pl_delay_ns = self.pl_clk1_delay_ns

        deltas: list[dict[str, float]] = []
        for power_net in self.power_nets:
            rise_start_us = (pl_delay_ns + power_net.delay_ns) * US_PER_NS
            fall_start_us = rise_start_us + clock_period_us * power_net.duty
            deltas.append(
                {
                    "cds1_rise": self.nearest_clock_edge_delta_ns(
                        self.cds1_end_us,
                        rise_start_us,
                        clock_period_us,
                    ),
                    "cds1_fall": self.nearest_clock_edge_delta_ns(
                        self.cds1_end_us,
                        fall_start_us,
                        clock_period_us,
                    ),
                    "cds2_rise": self.nearest_clock_edge_delta_ns(
                        self.cds2_end_us,
                        rise_start_us,
                        clock_period_us,
                    ),
                    "cds2_fall": self.nearest_clock_edge_delta_ns(
                        self.cds2_end_us,
                        fall_start_us,
                        clock_period_us,
                    ),
                }
            )
        return deltas

    def align_control_panel(self) -> None:
        if not self.baselines:
            return

        view_box = self.plot.getPlotItem().getViewBox()
        for row_name, widget in self.control_widgets_by_row.items():
            scene_pos = view_box.mapViewToScene(
                QtCore.QPointF(self.x_min_us, self.baselines[row_name])
            )
            plot_pos = self.plot.mapFromScene(scene_pos)
            widget.adjustSize()
            y = int(plot_pos.y() - widget.height() / 2)
            widget.move(0, y)

    def add_time_markers(self, values_us: list[float], marker_pen: QtGui.QPen) -> None:
        for value_us in values_us:
            line = pg.InfiniteLine(
                pos=value_us,
                angle=90,
                pen=marker_pen,
            )
            self.plot.addItem(line)

            text = pg.TextItem(f"{value_us:g} us", color="#b8c3d1", anchor=(0.5, 0))
            text.setFont(self.app_font)
            text.setPos(value_us, -0.66)
            self.plot.addItem(text)

    def nearest_clock_edge_delta_ns(
        self,
        target_us: float,
        first_edge_us: float,
        period_us: float,
    ) -> float:
        nearest_index = round((target_us - first_edge_us) / period_us)
        candidates = []
        for index in (nearest_index - 1, nearest_index, nearest_index + 1):
            if index >= 0:
                candidates.append(first_edge_us + index * period_us)

        if not candidates:
            candidates.append(first_edge_us)

        nearest_edge_us = min(candidates, key=lambda edge_us: abs(edge_us - target_us))
        return (nearest_edge_us - target_us) / US_PER_NS

    def apply_inputs(self) -> None:
        pl_clk1_delay_ns = self.parse_delay_edit()
        if pl_clk1_delay_ns is None:
            return

        self.pl_clk1_delay_ns = pl_clk1_delay_ns
        self.draw()

    def parse_delay_edit(self) -> float | None:
        delay_ns = self.pl_clk1_delay_combo.currentData()
        if delay_ns is None:
            return None
        return float(delay_ns)

    def update_frequency_label(self) -> None:
        frequency_mhz = self.source_clock_mhz / self.clock_divider
        self.frequency_label.setText(f"{frequency_mhz:.2f} [MHz]")

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        QtCore.QTimer.singleShot(0, self.align_control_panel)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = TimingDiagram()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
