from qtpy.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, QMainWindow
from qtpy.QtCore import QThread, Slot, Signal, QObject, Qt, QTimer
import argparse
import queue
import time
from .kafka_table import qt_kafka_table
from bluesky_widgets.qt.run_engine_client import QtReConsoleMonitor
#from .QtReConsoleMonitor import QtReConsoleMonitor
import sys


class LiveTableWorker(QObject):
    finished = Signal()
    lineReady = Signal(str)

    def __init__(
        self, beamline_acronym, config_file, topic_string="bluesky.runengine.documents"
    ):
        super().__init__()
        self.beamline_acronym = beamline_acronym
        self.config_file = config_file
        self.topic_string = topic_string
        self._polling = True
        self.destroyed.connect(lambda: print("LiveTableWorker Destroyed Signal"))

    @Slot()
    def run(self):
        print("Running KafkaTable")
        kafka_dispatcher = qt_kafka_table(
            self.beamline_acronym,
            self.config_file,
            self.topic_string,
            self.lineEmitter,
        )
        kafka_dispatcher.setParent(self)
        kafka_dispatcher.start(self.keepPolling)
        print("Done with kafka_table")
        self.finished.emit()

    def lineEmitter(self, line):
        self.lineReady.emit(line)

    def stop(self):
        self._polling = False

    def keepPolling(self):
        print(f"Keep Polling called! {self._polling}")
        return self._polling

    @Slot()
    def aboutToQuit(self):
        print("About To Quit")
        self.stop()


class LiveTableModel(QWidget):
    def __init__(
        self,
        beamline_acronym,
        config_file,
        topic_string="bluesky.runengine.documents",
        parent=None,
    ):
        super().__init__(parent)
        self.thread = QThread()
        self.msg_queue = queue.Queue()
        self.worker = LiveTableWorker(beamline_acronym, config_file, topic_string)

        self.destroyed.connect(lambda: self.stop_console_output_monitoring)
        self.worker.moveToThread(self.thread)
        self.worker.lineReady.connect(self.msg_queue.put)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def start_console_output_monitoring(self):
        self._stop_console_monitor = False
        self.thread.quit()
        self.thread.wait()

        # self._rco = ReceiveConsoleOutput(zmq_subscribe_addr=self._zmq_info_addr, timeout=200)

    def stop_console_output_monitoring(self):
        print("Stop Console Monitoring")
        self._stop_console_monitor = True
        self.worker.stop()

    # def console_monitoring_thread(self, *, callback):
    def console_monitoring_thread(self):
        while True:
            print("Monitoring")
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
                break

class LiveTableModel2(QWidget):
    def __init__(
        self,
        beamline_acronym,
        config_file,
        topic_string="bluesky.runengine.documents",
        parent=None,
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.msg_queue = queue.Queue()
        #self.qtDispatcher = qt_kafka_table(beamline_acronym, config_file, topic_string, self.msg_queue.put)
        #self.qtDispatcher.setParent(self)
        label = QLabel("Test")
        vbox = QVBoxLayout()
        vbox.addWidget(label)
        self.setLayout(vbox)
        self.destroyed.connect(lambda: print("Destroying LiveTableModel2"))
        self.start_console_output_monitoring()

    @Slot()
    def closeEvent(self, event):
        print("Close event LiveTableModel2")

    def start_console_output_monitoring(self):
        print("Start Console Output Monitoring")
        self._stop_console_monitor = False
        self.console_monitoring_thread()
        QTimer.singleShot(195, self.console_monitoring_thread)
        #self.qtDispatcher.start(continue_polling=self.continue_polling)
        # self._rco = ReceiveConsoleOutput(zmq_subscribe_addr=self._zmq_info_addr, timeout=200)

    def stop_console_output_monitoring(self):
        print("Stop Console Monitoring")
        self._stop_console_monitor = True

    def continue_polling(self):
        return not self._stop_console_monitor

    # def console_monitoring_thread(self, *, callback):
    def console_monitoring_thread(self):
        while True:
            print("Monitoring")
            try:
                msg = self.msg_queue.get(timeout=0.2)
                msg = msg.rstrip("\n") + "\n"
                msgtime = time.time()
                QTimer.singleShot(195, self.console_monitoring_thread)
                return msgtime, msg

            except queue.Empty:
                pass
            except Exception as ex:
                print(f"Exception occurred: {ex}")

            if self._stop_console_monitor:
                print("Stop monitoring!")
                break

class TestWorker(QObject):
    finished = Signal()

    @Slot()
    def run(self):
        self._go = True
        QTimer.singleShot(1000, self.hello)

    def hello(self):
        print("Hello!")
        if self._go:
            QTimer.singleShot(1000, self.hello)
        else:
            self.finished.emit()


class LiveTableModel3(QWidget):
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
        print(msg)

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
        #print("Monitoring")
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
        self.kafkaTable = LiveTableModel3(bl_acronym, kafka_config)
        self.kafkaMonitor = QtReConsoleMonitor(self.kafkaTable, self)
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Kafka Table Monitor"))
        vbox.addWidget(self.kafkaMonitor)
        self.setLayout(vbox)

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
    #model = LiveTableModel(args.bl, args.config_file, topic_string=args.topic_string)
    #central_widget = LiveTableModel2(args.bl, args.config_file, topic_string=args.topic_string)
    model = LiveTableModel3(args.bl, args.config_file, topic_string=args.topic_string)
    #central_widget = LiveTableModel3(args.bl, args.config_file, topic_string=args.topic_string)
    central_widget = QtReConsoleMonitor(model, main_window)
    #model.setParent(central_widget)
    #central_widget.start_console_output_monitoring()
    main_window.setCentralWidget(central_widget)
    central_widget.destroyed.connect(lambda: model.stop_console_output_monitoring)
    main_window.show()
    app_ref = app.exec_()
    sys.exit(app_ref)


if __name__ == "__main__":
    main()
