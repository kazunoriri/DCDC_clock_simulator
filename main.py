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
        self.resize(1180, 720)

        pg.setConfigOptions(antialias=True, background="w", foreground="k")

        self.plot = pg.PlotWidget()
        self.setCentralWidget(self.plot)
        self.plot.showGrid(x=True, y=True, alpha=0.22)
        self.plot.setLabel("bottom", "Time", units="us")
        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.setMenuEnabled(False)
        self.plot.hideAxis("left")

        self.x_min_us = -2.0
        self.x_max_us = 62.0
        self.row_gap = 1.15
        self.amplitude = 0.58

        self.draw()

    def draw(self) -> None:
        signals = [
            PulseSignal("SYNC", ((0.0, 60.0),)),
            PulseSignal("CDS1", ((1.0, 15.0),)),
            PulseSignal("CDS2", ((30.0, 40.0),)),
        ]

        pen = pg.mkPen("#1f2937", width=2)
        accent_pen = pg.mkPen("#0f766e", width=2)
        clock_pen = pg.mkPen("#2563eb", width=2)

        row_names = ["SYNC", "CDS1", "CDS2", "PL_DCDC_CLK1", "3.3V_DIG"]
        baselines = {
            name: (len(row_names) - index - 1) * self.row_gap
            for index, name in enumerate(row_names)
        }

        for signal in signals:
            base = baselines[signal.name]
            x, y = pulse_steps(
                signal.pulses_us,
                0.0,
                60.0,
                base,
                base + self.amplitude,
            )
            self.plot.plot(x, y, pen=pen)

        pl_base = baselines["PL_DCDC_CLK1"]
        pl_x, pl_y = clock_steps(
            start_us=0.0,
            end_us=60.0,
            period_us=1.0,
            duty=0.5,
            low=pl_base,
            high=pl_base + self.amplitude,
        )
        self.plot.plot(pl_x, pl_y, pen=accent_pen)

        dig_base = baselines["3.3V_DIG"]
        dig_x, dig_y = clock_steps(
            start_us=20.0 * US_PER_NS,
            end_us=60.0,
            period_us=0.5,
            duty=0.5,
            low=dig_base,
            high=dig_base + self.amplitude,
        )
        self.plot.plot(dig_x, dig_y, pen=clock_pen)

        for name in row_names:
            base = baselines[name]
            label = pg.TextItem(name, color="#111827", anchor=(1, 0.5))
            label.setFont(QtGui.QFont("Meiryo", 10))
            label.setPos(-0.8, base + self.amplitude * 0.5)
            self.plot.addItem(label)

        self.add_time_markers([0, 1, 15, 30, 40, 60])
        self.add_notes(baselines)

        self.plot.setXRange(self.x_min_us, self.x_max_us, padding=0)
        self.plot.setYRange(-0.45, max(baselines.values()) + 1.15, padding=0)

    def add_time_markers(self, values_us: list[float]) -> None:
        for value_us in values_us:
            line = pg.InfiniteLine(
                pos=value_us,
                angle=90,
                pen=pg.mkPen("#9ca3af", width=1, style=QtCore.Qt.PenStyle.DashLine),
            )
            self.plot.addItem(line)

            text = pg.TextItem(f"{value_us:g} us", color="#374151", anchor=(0.5, 0))
            text.setFont(QtGui.QFont("Meiryo", 9))
            text.setPos(value_us, -0.34)
            self.plot.addItem(text)

    def add_notes(self, baselines: dict[str, float]) -> None:
        self.add_text("DUTY 50% / 2 MHz", 22.0, baselines["3.3V_DIG"] + 0.74)
        self.add_text("20 ns delay", 0.02, baselines["3.3V_DIG"] - 0.26)
        self.add_text("250 ns delay", 0.25, baselines["3.3V_DIG"] - 0.52)
        self.add_text("continuous pulses", 9.0, baselines["PL_DCDC_CLK1"] + 0.76)

    def add_text(self, text: str, x_us: float, y: float) -> None:
        item = pg.TextItem(text, color="#111827", anchor=(0, 0.5))
        item.setFont(QtGui.QFont("Meiryo", 9))
        item.setPos(x_us, y)
        self.plot.addItem(item)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = TimingDiagram()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
