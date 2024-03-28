from qtpy.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, QMainWindow
from qtpy.QtCore import QThread, Slot, Signal, QObject
import argparse
import queue
import time
from .kafka_table import kafka_table
from bluesky_widgets.qt.run_engine_client import QtReConsoleMonitor


class LiveTableWorker(QObject):
    finished = Signal()
    lineReady = Signal(str)

    def __init__(self, beamline_acronym, config_file, topic_string="bluesky.runengine.documents"):
        super().__init__()
        self.beamline_acronym = beamline_acronym
        self.config_file = config_file
        self.topic_string = topic_string

    @Slot()
    def run(self):
        print("Running KafkaTable")
        kafka_table(self.beamline_acronym, self.config_file, self.topic_string, self.lineEmitter)
        self.finished.emit()

    def lineEmitter(self, line):
        self.lineReady.emit(line)


class LiveTableModel(QObject):
    def __init__(self, beamline_acronym, config_file,
                 topic_string="bluesky.runengine.documents",
                 parent=None):
        super().__init__(parent)
        self.thread = QThread()
        self.msg_queue = queue.Queue()
        self.worker = LiveTableWorker(beamline_acronym, config_file, topic_string)

        self.worker.moveToThread(self.thread)
        self.worker.lineReady.connect(self.msg_queue.put)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def start_console_output_monitoring(self):
        self._stop_console_monitor = False
        # self._rco = ReceiveConsoleOutput(zmq_subscribe_addr=self._zmq_info_addr, timeout=200)

    def stop_console_output_monitoring(self):
        self._stop_console_monitor = True

    # def console_monitoring_thread(self, *, callback):
    def console_monitoring_thread(self):
        while True:
            try:
                msg = self.msg_queue.get()
                msg = msg.rstrip('\n') + '\n'
                msgtime = time.time()
                return msgtime, msg

            except queue.Empty:
                pass
            except Exception as ex:
                print(f"Exception occurred: {ex}")

            if self._stop_console_monitor:
                break


class QtKafkaTableTab(QWidget):
    name = "Live Table"

    def __init__(self, model, parent=None):
        super.__init__(parent)
        self.config = model.settings.gui_config
        bl_acronym = self.config.get("kafka", {}).get("bl_acronym", "")
        kafka_config = self.config.get("kafka", {}).get("config_file", "")
        self.kafkaTable = LiveTableModel(bl_acronym, kafka_config)


def main():
    parser = argparse.ArgumentParser(description="Kafka LiveTable Monitor")
    parser.add_argument("--bl", required=True, help="Beamline acronym used for kafka topic")
    parser.add_argument("--config-file", default="/etc/bluesky/kafka.yml", help="kafka config file location")
    parser.add_argument("--topic-string", default="bluesky.runengine.documents", help="string to be combined with acronym to create topic")

    args = parser.parse_args()
    app = QApplication([])

    main_window = QMainWindow()
    model = LiveTableModel(args.bl, args.config_file, topic_string=args.topic_string)
    central_widget = QtReConsoleMonitor(model)
    main_window.setCentralWidget(central_widget)
    main_window.show()
    app.exec_()


if __name__ == "__main__":
    main()
