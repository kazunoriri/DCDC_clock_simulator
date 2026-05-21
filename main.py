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
        self.pl_clk1_delay_ns = 0.0
        self.cds1_start_us = 1.0
        self.cds1_end_us = 15.0
        self.cds2_start_us = 30.0
        self.cds2_end_us = 40.0
        self.row_names = [
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

        self.cds1_start_edit = self.create_time_edit("1")
        self.cds1_end_edit = self.create_time_edit("15")
        self.cds2_start_edit = self.create_time_edit("30")
        self.cds2_end_edit = self.create_time_edit("40")
        self.divider_edit = QtWidgets.QLineEdit(str(self.clock_divider))
        self.divider_edit.setFixedWidth(64)
        self.divider_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.divider_edit.setValidator(QtGui.QIntValidator(1, 1000000, self.divider_edit))
        self.divider_edit.editingFinished.connect(self.apply_inputs)
        self.pl_clk1_delay_edit = self.create_delay_edit("0")
        self.frequency_label = QtWidgets.QLabel()
        self.frequency_label.setObjectName("result")
        self.update_frequency_label()
        self.dig_delta_labels: dict[str, QtWidgets.QLabel] = {}

        self.control_widgets_by_row = {
            "CDS1": self.create_pulse_editor(
                self.cds1_start_edit,
                self.cds1_end_edit,
                parent=panel,
            ),
            "CDS2": self.create_pulse_editor(
                self.cds2_start_edit,
                self.cds2_end_edit,
                parent=panel,
            ),
            "PL_DCDC_CLK1": self.create_clock_editor(parent=panel),
            "3.3V_DIG": self.create_dig_timing_editor(parent=panel),
        }
        return panel

    def create_pulse_editor(
        self,
        start_edit: QtWidgets.QLineEdit,
        end_edit: QtWidgets.QLineEdit,
        parent: QtWidgets.QWidget,
    ) -> QtWidgets.QWidget:
        editor = QtWidgets.QWidget(parent)
        layout = QtWidgets.QGridLayout(editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(4)

        up_label = QtWidgets.QLabel("↑")
        down_label = QtWidgets.QLabel("↓")
        for label in (up_label, down_label):
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(up_label, 0, 0)
        layout.addWidget(start_edit, 0, 1)
        layout.addWidget(down_label, 1, 0)
        layout.addWidget(end_edit, 1, 1)
        editor.adjustSize()
        return editor

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

        div_label = QtWidgets.QLabel("div")
        freq_label = QtWidgets.QLabel("freq")
        delay_label = QtWidgets.QLabel("delay ns")
        layout.addWidget(div_label, 0, 0)
        layout.addWidget(self.divider_edit, 0, 1)
        layout.addWidget(freq_label, 1, 0)
        layout.addWidget(self.frequency_label, 1, 1)
        layout.addWidget(delay_label, 2, 0)
        layout.addWidget(self.pl_clk1_delay_edit, 2, 1)
        editor.adjustSize()
        return editor

    def create_time_edit(self, text: str) -> QtWidgets.QLineEdit:
        edit = QtWidgets.QLineEdit(text)
        edit.setFixedWidth(64)
        edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        validator = QtGui.QDoubleValidator(0.0, 60.0, 6, edit)
        validator.setNotation(QtGui.QDoubleValidator.Notation.StandardNotation)
        edit.setValidator(validator)
        edit.editingFinished.connect(self.apply_inputs)
        return edit

    def create_delay_edit(self, text: str) -> QtWidgets.QLineEdit:
        edit = QtWidgets.QLineEdit(text)
        edit.setFixedWidth(64)
        edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        validator = QtGui.QDoubleValidator(0.0, 60000.0, 6, edit)
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
                60.0,
                base - half_amp,
                base + half_amp,
            )
            self.plot.plot(x, y, pen=waveform_pen)

        pl_base = baselines["PL_DCDC_CLK1"]
        pl_start_us = self.pl_clk1_delay_ns * US_PER_NS
        pl_x, pl_y = clock_steps(
            start_us=pl_start_us,
            end_us=60.0,
            period_us=clock_period_us,
            duty=0.5,
            low=pl_base - half_amp,
            high=pl_base + half_amp,
        )
        if pl_start_us > 0.0:
            pl_x = [0.0, pl_start_us] + pl_x
            pl_y = [pl_base - half_amp, pl_base - half_amp] + pl_y
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
        self.update_dig_delta_labels(clock_period_us)

        self.add_time_markers([0, self.cds1_end_us, self.cds2_end_us, 60], marker_pen)

        self.plot.setXRange(self.x_min_us, self.x_max_us, padding=0)
        self.plot.setYRange(
            min(baselines.values()) - 0.75,
            max(baselines.values()) + 0.75,
            padding=0,
        )
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
        dig_rise_start_us = 20.0 * US_PER_NS
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
        pl_clk1_delay_ns = self.parse_delay_edit()
        if pl_clk1_delay_ns is None:
            return

        self.cds1_start_us = start_us
        self.cds1_end_us = end_us
        self.cds2_start_us = cds2_start_us
        self.cds2_end_us = cds2_end_us
        self.clock_divider = divider
        self.pl_clk1_delay_ns = pl_clk1_delay_ns
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

    def parse_delay_edit(self) -> float | None:
        text = self.pl_clk1_delay_edit.text().strip()
        try:
            delay_ns = float(text)
        except ValueError:
            self.pl_clk1_delay_edit.setText(f"{self.pl_clk1_delay_ns:g}")
            return None

        if delay_ns < 0.0 or delay_ns > 60000.0:
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
