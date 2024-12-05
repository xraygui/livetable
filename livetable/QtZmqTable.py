from qtpy.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, QMainWindow
from qtpy.QtCore import QThread, Slot, Signal, QObject, Qt, QTimer
from qtpy.QtGui import QFontInfo, QFont

# import argparse
import queue
import time

# from .kafka_table import qt_kafka_table
from .zmq_table import qt_zmq_table

# from bluesky_widgets.qt.run_engine_client import QtReConsoleMonitor

from .simpleConsoleMonitor import QtReConsoleMonitor
import sys


class LiveTableModel(QWidget):
    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)
        self.msg_queue = queue.Queue()
        self.zmq_dispatcher = qt_zmq_table(self.newMsg)
        self.zmq_dispatcher.setParent(self)
        self.zmq_dispatcher.start()

        label = QLabel("Test")
        vbox = QVBoxLayout()
        vbox.addWidget(label)
        self.setLayout(vbox)
        self.destroyed.connect(lambda: self.stop_console_output_monitoring)

    def newMsg(self, msg):
        self.msg_queue.put(msg)
        # print(msg)

    def start_console_output_monitoring(self):
        print("Start Console Output Monitoring")
        self._stop_console_monitor = False

    def stop_console_output_monitoring(self):
        print("Stop Console Monitoring")
        self.zmq_dispatcher.stop()
        self._stop_console_monitor = True

    def continue_polling(self):
        return not self._stop_console_monitor

    # def console_monitoring_thread(self, *, callback):
    def console_monitoring_thread(self):
        # print("Monitoring")
        for n in range(5):
            try:
                msg = self.msg_queue.get(timeout=0.2)
                msg = msg.rstrip("\n") + "\n"
                msgtime = time.time()
                return msgtime, msg

            except queue.Empty:
                pass
            except Exception as ex:
                print(f"Exception occurred: {ex}")

            if self._stop_console_monitor:
                print("Stop monitoring!")
        return None, None


class QtZMQTableTab(QWidget):
    name = "Live Table"

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.config = model.settings.gui_config
        self.zmqTable = LiveTableModel(self)
        self.zmqMonitor = QtReConsoleMonitor(self.zmqTable, self)

        # Printing the font and font family used by self.zmqMonitor
        font = self.zmqMonitor._text_edit.font()
        font.setFamily("Monospace")
        font.setStyleHint(QFont.Monospace)
        self.zmqMonitor._text_edit.setFont(font)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("ZMQ Table Monitor"))
        vbox.addWidget(self.zmqMonitor)
        self.setLayout(vbox)

        font = self.zmqMonitor._text_edit.font()
        actual_font = QFontInfo(font)
        print(f"Font used: {actual_font.family()}, Font Desired: {font.family()}")


def main():
    app = QApplication([])

    main_window = QMainWindow()
    model = LiveTableModel()
    central_widget = QtReConsoleMonitor(model, main_window)
    # Ensure the font family is set to a monospace font that exists on the system
    font = central_widget._text_edit.font()
    font.setFamily("Monospace")
    font.setStyleHint(QFont.Monospace)
    central_widget._text_edit.setFont(font)
    font = central_widget._text_edit.font()
    actual_font = QFontInfo(font)
    print(f"Font used: {actual_font.family()}, Font Desired: {font.family()}")
    # model.setParent(central_widget)
    # central_widget.start_console_output_monitoring()
    main_window.setCentralWidget(central_widget)
    central_widget.destroyed.connect(lambda: model.stop_console_output_monitoring)
    main_window.show()
    app_ref = app.exec_()
    sys.exit(app_ref)


if __name__ == "__main__":
    main()
