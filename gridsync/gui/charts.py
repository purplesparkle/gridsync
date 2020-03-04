# -*- coding: utf-8 -*-

from PyQt5.QtChart import (
    QBarSet,
    QChart,
    QChartView,
    QHorizontalPercentBarSeries,
    QPieSeries,
)
from PyQt5.QtCore import QMargins, Qt
from PyQt5.QtGui import QColor, QPainter, QPen


class ZKAPPieChart(QChart):
    def __init__(self):
        super().__init__()

        series = QPieSeries()
        series.setPieSize(0.9)
        series.setHoleSize(0.6)
        series.append("", 123456)
        series.append("", 500000)

        self.slice_used = series.slices()[0]
        self.slice_used.setPen(QPen(Qt.red, 0))
        self.slice_used.setBrush(Qt.red)

        self.slice_available = series.slices()[1]
        self.slice_available.setPen(QPen(Qt.darkGreen, 0))
        self.slice_available.setBrush(Qt.darkGreen)

        self.addSeries(series)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.legend().hide()
        self.setBackgroundVisible(False)
        self.setMargins(QMargins(0, 0, 0, 0))

        self.update_tooltip()

    def update_tooltip(self):
        self.setToolTip(
            "ZKAPs used: {}\n"
            "ZKAPs available: {}\n\n"
            "Last purchase: 2019-06-20 12:34:56".format(
                round(self.slice_used.value()),
                round(self.slice_available.value()),
            )
        )


class ZKAPBarChart(QChart):
    def __init__(self):
        super().__init__()

        self.set_used = QBarSet("Used")
        color_used = QColor("#1F9FDE")
        self.set_used.setPen(QPen(color_used, 0))
        self.set_used.setBrush(color_used)
        self.set_used.insert(0, 0)

        self.set_cost = QBarSet("Monthly cost")
        color_cost = QColor("#EE9A1D")
        self.set_cost.setPen(QPen(color_cost, 0))
        self.set_cost.setBrush(color_cost)
        self.set_cost.insert(0, 0)

        self.set_available = QBarSet("Available")
        color_available = QColor("#99CA54")
        color_available = QColor("Light Grey")
        self.set_available.setPen(QPen(color_available, 0))
        self.set_available.setBrush(color_available)
        self.set_available.insert(0, 0)

        series = QHorizontalPercentBarSeries()
        series.append(self.set_used)
        series.append(self.set_cost)
        series.append(self.set_available)

        self.addSeries(series)
        self.setAnimationOptions(QChart.SeriesAnimations)
        self.setBackgroundVisible(False)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.legend().setAlignment(Qt.AlignBottom)
        # self.legend().hide()

        self.update(10, 30, 40)  # XXX

    def update(self, used: int = 0, cost: int = 0, available: int = 0) -> None:
        self.set_used.replace(0, used)
        self.set_cost.replace(0, cost)
        self.set_available.replace(0, available)
        self.setToolTip("")  # XXX


class ZKAPBarChartView(QChartView):
    def __init__(self):
        super().__init__()
        self.chart = ZKAPBarChart()
        self.setChart(self.chart)
        self.setRenderHint(QPainter.Antialiasing)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    chart = ZKAPBarChart()
    view = QChartView(chart)
    view.setRenderHint(QPainter.Antialiasing)
    window = QMainWindow()
    window.setCentralWidget(view)
    window.show()
    sys.exit(app.exec_())