from bluesky.callbacks.zmq import RemoteDispatcher
from bluesky_widgets.qt.zmq_dispatcher import RemoteDispatcher as QtRemoteDispatcher
from bluesky.callbacks.best_effort import BestEffortCallback
from .lessEffortCallback import LessEffortCallback


def zmq_table(out=print, continue_polling=None, hostname="localhost", port=5578):
    callback = LessEffortCallback(out=out)
    # bec = BestEffortCallback()

    zmq_dispatcher = RemoteDispatcher(f"{hostname}:{port}")

    zmq_dispatcher.subscribe(callback)
    zmq_dispatcher.start()


def qt_zmq_table(out=print, hostname="localhost", port=5578):
    callback = LessEffortCallback(out=out)
    # bec = BestEffortCallback()

    zmq_dispatcher = QtRemoteDispatcher(f"{hostname}:{port}")

    zmq_dispatcher.subscribe(callback)

    return zmq_dispatcher, callback


def main():

    zmq_table()


if __name__ == "__main__":

    main()
