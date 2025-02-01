from bluesky.callbacks.zmq import RemoteDispatcher
from bluesky_widgets.qt.zmq_dispatcher import RemoteDispatcher as QtRemoteDispatcher
from bluesky.callbacks.best_effort import BestEffortCallback
from .lessEffortCallback import LessEffortCallback


def zmq_table(out=print, continue_polling=None):
    callback = LessEffortCallback(out=out)
    # bec = BestEffortCallback()

    zmq_dispatcher = RemoteDispatcher("localhost:5578")

    zmq_dispatcher.subscribe(callback)
    zmq_dispatcher.start()


def qt_zmq_table(out=print):
    callback = LessEffortCallback(out=out)
    # bec = BestEffortCallback()

    zmq_dispatcher = QtRemoteDispatcher("localhost:5578")

    zmq_dispatcher.subscribe(callback)

    return zmq_dispatcher, callback


def main():

    zmq_table()


if __name__ == "__main__":

    main()
