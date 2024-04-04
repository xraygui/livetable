from qtpy.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, QMainWindow
from qtpy.QtCore import QThread, Slot, Signal, QObject, Qt, QTimer
from qtpy.QtGui import QFontInfo, QFont
import argparse
import queue
import time
from .kafka_table import qt_kafka_table

from bluesky_widgets.qt.run_engine_client import QtReConsoleMonitor

# from .QtReConsoleMonitor import QtReConsoleMonitor
import sys


class LiveTableModel(QWidget):
    def __init__(
        self,
        beamline_acronym,
        config_file,
        topic_string="bluesky.runengine.documents",
        parent=None,
    ):
        super().__init__(parent)
        self.msg_queue = queue.Queue()
        self.kafka_dispatcher = qt_kafka_table(
            beamline_acronym,
            config_file,
            topic_string,
            self.newMsg,
        )
        self.kafka_dispatcher.setParent(self)
        self.kafka_dispatcher.start()

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
        self.kafka_dispatcher.stop()
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


class QtKafkaTableTab(QWidget):
    name = "Live Table"

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.config = model.settings.gui_config
        bl_acronym = self.config.get("kafka", {}).get("bl_acronym", "")
        kafka_config = self.config.get("kafka", {}).get("config_file", "")
        self.kafkaTable = LiveTableModel(bl_acronym, kafka_config)
        self.kafkaMonitor = QtReConsoleMonitor(self.kafkaTable, self)
        # self.kafkaMonitor._text_edit.setFontFamily("monospace")

        # Printing the font and font family used by self.kafkaMonitor
        font = self.kafkaMonitor._text_edit.font()
        font.setFamily("Monospace")
        font.setStyleHint(QFont.Monospace)
        self.kafkaMonitor._text_edit.setFont(font)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Kafka Table Monitor"))
        vbox.addWidget(self.kafkaMonitor)
        self.setLayout(vbox)

        font = self.kafkaMonitor._text_edit.font()
        actual_font = QFontInfo(font)
        print(f"Font used: {actual_font.family()}, Font Desired: {font.family()}")


def main():
    parser = argparse.ArgumentParser(description="Kafka LiveTable Monitor")
    parser.add_argument(
        "--bl", required=True, help="Beamline acronym used for kafka topic"
    )
    parser.add_argument(
        "--config-file",
        default="/etc/bluesky/kafka.yml",
        help="kafka config file location",
    )
    parser.add_argument(
        "--topic-string",
        default="bluesky.runengine.documents",
        help="string to be combined with acronym to create topic",
    )

    args = parser.parse_args()
    app = QApplication([])

    main_window = QMainWindow()
    # model = LiveTableModel(args.bl, args.config_file, topic_string=args.topic_string)
    # central_widget = LiveTableModel2(args.bl, args.config_file, topic_string=args.topic_string)
    model = LiveTableModel(args.bl, args.config_file, topic_string=args.topic_string)
    # central_widget = LiveTableModel3(args.bl, args.config_file, topic_string=args.topic_string)
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
