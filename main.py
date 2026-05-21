from __future__ import annotations

import sys
from dataclasses import dataclass

import pyqtgraph as pg
from PyQt6 import QtCore, QtGui, QtWidgets


US_PER_NS = 0.001


@dataclass(frozen=True)
class PulseSignal:
    name: str
    pulses_us: tuple[tuple[float, float], ...]


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
        self.x_max_us = 62.0
        self.row_gap = 1.05
        self.amplitude = 0.74
        self.source_clock_mhz = 175.0
        self.clock_divider = 84
        self.cds1_start_us = 1.0
        self.cds1_end_us = 15.0
        self.cds2_start_us = 30.0
        self.cds2_end_us = 40.0

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

    def create_control_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(118)
        panel.setStyleSheet(
            """
            QLabel {
                color: #b8c3d1;
                font-family: Meiryo;
                font-size: 10pt;
            }
            QLineEdit {
                background: #111111;
                border: 1px solid #606060;
                color: #ffff00;
                padding: 4px 6px;
                selection-background-color: #1f6feb;
            }
            QLabel#result {
                color: #ffff00;
            }
            """
        )

        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 48, 0, 0)
        layout.setSpacing(6)

        title = QtWidgets.QLabel("CDS1 [us]")
        self.cds1_start_edit = self.create_time_edit("1")
        self.cds1_end_edit = self.create_time_edit("15")
        cds2_title = QtWidgets.QLabel("CDS2 [us]")
        self.cds2_start_edit = self.create_time_edit("30")
        self.cds2_end_edit = self.create_time_edit("40")
        divider_title = QtWidgets.QLabel("DIV")
        self.divider_edit = QtWidgets.QLineEdit(str(self.clock_divider))
        self.divider_edit.setValidator(QtGui.QIntValidator(1, 1000000, self.divider_edit))
        self.divider_edit.editingFinished.connect(self.apply_inputs)
        self.frequency_label = QtWidgets.QLabel()
        self.frequency_label.setObjectName("result")
        self.update_frequency_label()

        layout.addWidget(title)
        layout.addWidget(self.cds1_start_edit)
        layout.addWidget(self.cds1_end_edit)
        layout.addSpacing(14)
        layout.addWidget(cds2_title)
        layout.addWidget(self.cds2_start_edit)
        layout.addWidget(self.cds2_end_edit)
        layout.addSpacing(14)
        layout.addWidget(divider_title)
        layout.addWidget(self.divider_edit)
        layout.addWidget(self.frequency_label)
        layout.addStretch()
        return panel

    def create_time_edit(self, text: str) -> QtWidgets.QLineEdit:
        edit = QtWidgets.QLineEdit(text)
        validator = QtGui.QDoubleValidator(0.0, 60.0, 6, edit)
        validator.setNotation(QtGui.QDoubleValidator.Notation.StandardNotation)
        edit.setValidator(validator)
        edit.editingFinished.connect(self.apply_inputs)
        return edit

    def draw(self) -> None:
        self.plot.clear()

        signals = [
            PulseSignal("CDS1", ((self.cds1_start_us, self.cds1_end_us),)),
            PulseSignal("CDS2", ((self.cds2_start_us, self.cds2_end_us),)),
        ]

        waveform_pen = pg.mkPen("#ffff00", width=1)
        marker_pen = pg.mkPen("#8a8a8a", width=1, style=QtCore.Qt.PenStyle.DashLine)

        row_names = [
            "CDS1",
            "CDS2",
            "PL_DCDC_CLK1",
            "3.3V_DIG",
            "3.3V_DIG_2",
            "3.3V_DIG_3",
            "3.3V_DIG_4",
            "3.3V_DIG_5",
            "3.3V_DIG_6",
        ]
        baselines = {
            name: (len(row_names) - index - 1) * self.row_gap
            for index, name in enumerate(row_names)
        }
        half_amp = self.amplitude * 0.5
        clock_period_us = self.clock_divider / self.source_clock_mhz

        self.plot.getAxis("left").setTicks(
            [[(baselines[name], name) for name in row_names]]
        )

        for signal in signals:
            base = baselines[signal.name]
            x, y = pulse_steps(
                signal.pulses_us,
                0.0,
                60.0,
                base - half_amp,
                base + half_amp,
            )
            self.plot.plot(x, y, pen=waveform_pen)

        pl_base = baselines["PL_DCDC_CLK1"]
        pl_x, pl_y = clock_steps(
            start_us=0.0,
            end_us=60.0,
            period_us=clock_period_us,
            duty=0.5,
            low=pl_base - half_amp,
            high=pl_base + half_amp,
        )
        self.plot.plot(pl_x, pl_y, pen=waveform_pen)

        dig_base = baselines["3.3V_DIG"]
        dig_x, dig_y = clock_steps(
            start_us=20.0 * US_PER_NS,
            end_us=60.0,
            period_us=clock_period_us,
            duty=0.5,
            low=dig_base - half_amp,
            high=dig_base + half_amp,
        )
        self.plot.plot(dig_x, dig_y, pen=waveform_pen)

        self.add_time_markers([0, self.cds1_end_us, self.cds2_end_us, 60], marker_pen)

        self.plot.setXRange(self.x_min_us, self.x_max_us, padding=0)
        self.plot.setYRange(
            min(baselines.values()) - 0.75,
            max(baselines.values()) + 0.75,
            padding=0,
        )

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

    def apply_inputs(self) -> None:
        start_us = self.parse_time_edit(self.cds1_start_edit, self.cds1_start_us)
        end_us = self.parse_time_edit(self.cds1_end_edit, self.cds1_end_us)
        if start_us >= end_us:
            self.cds1_start_edit.setText(f"{self.cds1_start_us:g}")
            self.cds1_end_edit.setText(f"{self.cds1_end_us:g}")
            return

        cds2_start_us = self.parse_time_edit(self.cds2_start_edit, self.cds2_start_us)
        cds2_end_us = self.parse_time_edit(self.cds2_end_edit, self.cds2_end_us)
        if cds2_start_us >= cds2_end_us:
            self.cds2_start_edit.setText(f"{self.cds2_start_us:g}")
            self.cds2_end_edit.setText(f"{self.cds2_end_us:g}")
            return

        divider = self.parse_divider_edit()
        if divider is None:
            return

        self.cds1_start_us = start_us
        self.cds1_end_us = end_us
        self.cds2_start_us = cds2_start_us
        self.cds2_end_us = cds2_end_us
        self.clock_divider = divider
        self.update_frequency_label()
        self.draw()

    def parse_time_edit(self, edit: QtWidgets.QLineEdit, fallback: float) -> float:
        text = edit.text().strip()
        try:
            return float(text)
        except ValueError:
            edit.setText(f"{fallback:g}")
            return fallback

    def parse_divider_edit(self) -> int | None:
        text = self.divider_edit.text().strip()
        try:
            divider = int(text)
        except ValueError:
            self.divider_edit.setText(str(self.clock_divider))
            return None

        if divider < 1:
            self.divider_edit.setText(str(self.clock_divider))
            return None

        return divider

    def update_frequency_label(self) -> None:
        frequency_mhz = self.source_clock_mhz / self.clock_divider
        self.frequency_label.setText(f"{frequency_mhz:.6g} MHz")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = TimingDiagram()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
