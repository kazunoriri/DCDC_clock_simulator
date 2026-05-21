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

        pg.setConfigOptions(antialias=True, background="k", foreground="#b8c3d1")

        self.plot = pg.PlotWidget()
        self.setCentralWidget(self.plot)
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
        bottom_axis.setTickSpacing(major=10, minor=1)

        self.x_min_us = -2.0
        self.x_max_us = 62.0
        self.row_gap = 1.35
        self.amplitude = 0.74
        self.clock_period_us = 1.0

        self.draw()

    def draw(self) -> None:
        signals = [
            PulseSignal("SYNC", ((0.0, 100.0 * US_PER_NS),)),
            PulseSignal("CDS1", ((1.0, 15.0),)),
            PulseSignal("CDS2", ((30.0, 40.0),)),
        ]

        waveform_pen = pg.mkPen("#ffff00", width=1)
        marker_pen = pg.mkPen("#8a8a8a", width=1, style=QtCore.Qt.PenStyle.DashLine)

        row_names = ["SYNC", "CDS1", "CDS2", "PL_DCDC_CLK1", "3.3V_DIG"]
        baselines = {
            name: (len(row_names) - index - 1) * self.row_gap
            for index, name in enumerate(row_names)
        }
        half_amp = self.amplitude * 0.5

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
            period_us=self.clock_period_us,
            duty=0.5,
            low=pl_base - half_amp,
            high=pl_base + half_amp,
        )
        self.plot.plot(pl_x, pl_y, pen=waveform_pen)

        dig_base = baselines["3.3V_DIG"]
        dig_x, dig_y = clock_steps(
            start_us=20.0 * US_PER_NS,
            end_us=60.0,
            period_us=self.clock_period_us,
            duty=0.5,
            low=dig_base - half_amp,
            high=dig_base + half_amp,
        )
        self.plot.plot(dig_x, dig_y, pen=waveform_pen)

        self.add_time_markers([0, 1, 15, 30, 40, 60], marker_pen)

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


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = TimingDiagram()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
