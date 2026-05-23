from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pyqtgraph as pg
from PyQt6 import QtCore, QtGui, QtWidgets


US_PER_NS = 0.001
CONFIG_PATH = Path(__file__).with_name("timing_config.json")


@dataclass(frozen=True)
class PulseSignal:
    name: str
    pulses_us: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class TimingConfig:
    pl_dcdc_clk_name: str = "PL_DCDC_CLK1"
    power_net_name_0: str = "3.3V_DIG"
    power_net_name_1: str = "3.3V_DIG_2"
    power_net_name_2: str = "3.3V_DIG_3"
    power_net_name_3: str = "3.3V_DIG_4"
    power_net_name_4: str = "3.3V_DIG_5"
    power_net_name_5: str = "3.3V_DIG_6"
    power_net_delay_ns_0: float = 0.0
    power_net_delay_ns_1: float = 10.0
    power_net_delay_ns_2: float = 20.0
    power_net_delay_ns_3: float = 30.0
    power_net_delay_ns_4: float = 40.0
    power_net_delay_ns_5: float = 50.0
    gate_period_us: float = 60.0
    cds1_rise_us: float = 1.0
    cds1_fall_us: float = 15.0
    cds2_rise_us: float = 30.0
    cds2_fall_us: float = 40.0
    clock_divider: int = 84


def load_timing_config(path: Path = CONFIG_PATH) -> TimingConfig:
    defaults = TimingConfig()
    if not path.exists():
        return defaults

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults

    try:
        values = {
            "pl_dcdc_clk_name": str(
                data.get("pl_dcdc_clk_name", defaults.pl_dcdc_clk_name)
            ),
            "power_net_name_0": str(
                data.get("power_net_name_0", defaults.power_net_name_0)
            ),
            "power_net_name_1": str(
                data.get("power_net_name_1", defaults.power_net_name_1)
            ),
            "power_net_name_2": str(
                data.get("power_net_name_2", defaults.power_net_name_2)
            ),
            "power_net_name_3": str(
                data.get("power_net_name_3", defaults.power_net_name_3)
            ),
            "power_net_name_4": str(
                data.get("power_net_name_4", defaults.power_net_name_4)
            ),
            "power_net_name_5": str(
                data.get("power_net_name_5", defaults.power_net_name_5)
            ),
            "power_net_delay_ns_0": float(
                data.get("power_net_delay_ns_0", defaults.power_net_delay_ns_0)
            ),
            "power_net_delay_ns_1": float(
                data.get("power_net_delay_ns_1", defaults.power_net_delay_ns_1)
            ),
            "power_net_delay_ns_2": float(
                data.get("power_net_delay_ns_2", defaults.power_net_delay_ns_2)
            ),
            "power_net_delay_ns_3": float(
                data.get("power_net_delay_ns_3", defaults.power_net_delay_ns_3)
            ),
            "power_net_delay_ns_4": float(
                data.get("power_net_delay_ns_4", defaults.power_net_delay_ns_4)
            ),
            "power_net_delay_ns_5": float(
                data.get("power_net_delay_ns_5", defaults.power_net_delay_ns_5)
            ),
            "gate_period_us": float(data.get("gate_period_us", defaults.gate_period_us)),
            "cds1_rise_us": float(data.get("cds1_rise_us", defaults.cds1_rise_us)),
            "cds1_fall_us": float(data.get("cds1_fall_us", defaults.cds1_fall_us)),
            "cds2_rise_us": float(data.get("cds2_rise_us", defaults.cds2_rise_us)),
            "cds2_fall_us": float(data.get("cds2_fall_us", defaults.cds2_fall_us)),
            "clock_divider": int(data.get("clock_divider", defaults.clock_divider)),
        }
    except (TypeError, ValueError):
        return defaults

    if not values["pl_dcdc_clk_name"].strip():
        values["pl_dcdc_clk_name"] = defaults.pl_dcdc_clk_name
    for index in range(6):
        key = f"power_net_name_{index}"
        if not values[key].strip():
            values[key] = getattr(defaults, key)
        delay_key = f"power_net_delay_ns_{index}"
        if values[delay_key] < 0.0:
            values[delay_key] = getattr(defaults, delay_key)
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
        self.resize(760, 650)

        self.x_min_us = -2.0
        self.row_gap = 1.05
        self.amplitude = 0.74
        self.source_clock_mhz = 175.0
        self.config = load_timing_config()
        self.gate_period_us = self.config.gate_period_us
        self.x_max_us = self.gate_period_us + 2.0
        self.pl_dcdc_clk_name = self.config.pl_dcdc_clk_name
        self.power_net_names = [
            self.config.power_net_name_0,
            self.config.power_net_name_1,
            self.config.power_net_name_2,
            self.config.power_net_name_3,
            self.config.power_net_name_4,
            self.config.power_net_name_5,
        ]
        self.power_net_delays_ns = [
            self.config.power_net_delay_ns_0,
            self.config.power_net_delay_ns_1,
            self.config.power_net_delay_ns_2,
            self.config.power_net_delay_ns_3,
            self.config.power_net_delay_ns_4,
            self.config.power_net_delay_ns_5,
        ]
        self.power_net_name_0 = self.power_net_names[0]
        self.clock_divider = self.config.clock_divider
        self.pl_clk1_delay_ns = 0.0
        self.cds1_start_us = self.config.cds1_rise_us
        self.cds1_end_us = self.config.cds1_fall_us
        self.cds2_start_us = self.config.cds2_rise_us
        self.cds2_end_us = self.config.cds2_fall_us
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
        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.plot = pg.PlotWidget(axisItems={"bottom": TimeAxisItem(orientation="bottom")})
        layout.addWidget(self.plot, stretch=1)
        layout.addWidget(self.create_control_panel())
        self.setCentralWidget(central)

        self.plot.setBackground("#000000")
        self.plot.showGrid(x=True, y=True, alpha=0.34)
        self.plot.setLabel("bottom", "time [us]", color="#b8c3d1")
        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.setMenuEnabled(False)
        self.plot.getPlotItem().getViewBox().setBorder(pg.mkPen("#606060", width=1))

        bottom_axis = self.plot.getAxis("bottom")
        left_axis = self.plot.getAxis("left")
        for axis in (bottom_axis, left_axis):
            axis.setPen(pg.mkPen("#808080"))
            axis.setTextPen(pg.mkPen("#b8c3d1"))
            axis.setStyle(tickFont=QtGui.QFont("Meiryo", 9), autoExpandTextSpace=True)

        self.draw()
        QtCore.QTimer.singleShot(0, self.align_control_panel)

    def create_control_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(190)
        panel.setStyleSheet(
            """
            QLabel {
                color: #b8c3d1;
                font-family: Meiryo;
                font-size: 9pt;
            }
            QLineEdit {
                background: #555555;
                border: 1px solid #606060;
                color: #f1f5f9;
                font-family: Meiryo;
                font-size: 9pt;
                padding: 2px 6px;
                selection-background-color: #1f6feb;
            }
            QLabel#result {
                color: #b8c3d1;
            }
            """
        )
        self.control_panel = panel

        self.pl_clk1_delay_edit = self.create_delay_edit("0")
        self.frequency_label = QtWidgets.QLabel()
        self.frequency_label.setObjectName("result")
        self.update_frequency_label()
        self.dig_delta_labels: dict[str, QtWidgets.QLabel] = {}

        self.control_widgets_by_row = {
            self.pl_dcdc_clk_name: self.create_clock_editor(parent=panel),
            self.power_net_name_0: self.create_dig_timing_editor(parent=panel),
        }
        return panel

    def create_dig_timing_editor(self, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
        editor = QtWidgets.QWidget(parent)
        layout = QtWidgets.QGridLayout(editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(2)

        title = QtWidgets.QLabel("from CDS↓")
        title.setObjectName("result")
        layout.addWidget(title, 0, 0, 1, 2)

        rows = [
            ("cds1_rise", "CDS1→↑"),
            ("cds1_fall", "CDS1→↓"),
            ("cds2_rise", "CDS2→↑"),
            ("cds2_fall", "CDS2→↓"),
        ]
        for row_index, (key, label_text) in enumerate(rows, start=1):
            label = QtWidgets.QLabel(label_text)
            value = QtWidgets.QLabel()
            value.setObjectName("result")
            value.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            self.dig_delta_labels[key] = value
            layout.addWidget(label, row_index, 0)
            layout.addWidget(value, row_index, 1)

        editor.adjustSize()
        return editor

    def create_clock_editor(self, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
        editor = QtWidgets.QWidget(parent)
        layout = QtWidgets.QGridLayout(editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(8)

        freq_label = QtWidgets.QLabel("freq")
        delay_label = QtWidgets.QLabel("delay ns")
        layout.addWidget(freq_label, 0, 0)
        layout.addWidget(self.frequency_label, 0, 1)
        layout.addWidget(delay_label, 1, 0)
        layout.addWidget(self.pl_clk1_delay_edit, 1, 1)
        editor.adjustSize()
        return editor

    def create_delay_edit(self, text: str) -> QtWidgets.QLineEdit:
        edit = QtWidgets.QLineEdit(text)
        edit.setFixedWidth(64)
        edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        validator = QtGui.QDoubleValidator(0.0, self.gate_period_us / US_PER_NS, 6, edit)
        validator.setNotation(QtGui.QDoubleValidator.Notation.StandardNotation)
        edit.setValidator(validator)
        edit.editingFinished.connect(self.apply_inputs)
        return edit

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

        for power_net_name, power_net_delay_ns in zip(
            self.power_net_names,
            self.power_net_delays_ns,
            strict=True,
        ):
            dig_base = baselines[power_net_name]
            dig_start_us = (self.pl_clk1_delay_ns + power_net_delay_ns) * US_PER_NS
            dig_x, dig_y = clock_steps(
                start_us=dig_start_us,
                end_us=self.gate_period_us,
                period_us=clock_period_us,
                duty=0.5,
                low=dig_base - half_amp,
                high=dig_base + half_amp,
            )
            if dig_start_us > 0.0:
                dig_x = [0.0, dig_start_us] + dig_x
                dig_y = [dig_base - half_amp, dig_base - half_amp] + dig_y
            self.plot.plot(dig_x, dig_y, pen=waveform_pen)
        self.update_dig_delta_labels(clock_period_us)

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
        QtCore.QTimer.singleShot(0, self.align_control_panel)

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
            text.setFont(QtGui.QFont("Meiryo", 9))
            text.setPos(value_us, -0.66)
            self.plot.addItem(text)

    def update_dig_delta_labels(self, clock_period_us: float) -> None:
        dig_rise_start_us = (
            self.pl_clk1_delay_ns + self.power_net_delays_ns[0]
        ) * US_PER_NS
        dig_fall_start_us = dig_rise_start_us + clock_period_us * 0.5

        values = {
            "cds1_rise": self.nearest_clock_edge_delta_ns(
                self.cds1_end_us,
                dig_rise_start_us,
                clock_period_us,
            ),
            "cds1_fall": self.nearest_clock_edge_delta_ns(
                self.cds1_end_us,
                dig_fall_start_us,
                clock_period_us,
            ),
            "cds2_rise": self.nearest_clock_edge_delta_ns(
                self.cds2_end_us,
                dig_rise_start_us,
                clock_period_us,
            ),
            "cds2_fall": self.nearest_clock_edge_delta_ns(
                self.cds2_end_us,
                dig_fall_start_us,
                clock_period_us,
            ),
        }

        for key, delta_ns in values.items():
            self.dig_delta_labels[key].setText(f"{delta_ns:+.1f} ns")

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
        text = self.pl_clk1_delay_edit.text().strip()
        try:
            delay_ns = float(text)
        except ValueError:
            self.pl_clk1_delay_edit.setText(f"{self.pl_clk1_delay_ns:g}")
            return None

        if delay_ns < 0.0 or delay_ns > self.gate_period_us / US_PER_NS:
            self.pl_clk1_delay_edit.setText(f"{self.pl_clk1_delay_ns:g}")
            return None

        return delay_ns

    def update_frequency_label(self) -> None:
        frequency_mhz = self.source_clock_mhz / self.clock_divider
        self.frequency_label.setText(f"{frequency_mhz:.2f} MHz")

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
