import atexit
import logging
import Queue
import multiprocessing
import signal
import sys

from offspring import Subprocess, SubprocessLoop

log = logging.getLogger(__name__)


class MotionConsumer(Subprocess):
    def __init__(self, app):
        self.app = app
        self.start()

    def run(self):
        self.app.consume()

        # we should never reach this
        log.error("Failed to consume from Kinesis!")
        sys.exit(2)


class MotionWorker(SubprocessLoop):
    def __init__(self, queue, responders):
        self.queue = queue
        self.responders = responders
        self.start()

    def loop(self):
        try:
            event_name, payload = self.queue.get(block=True, timeout=0.25)
        except Queue.Empty:
            return
        except Exception:
            log.exception("Failed to get event & payload from queue")
            return

        responder = self.responders[event_name]

        try:
            result = responder(payload)
        except Exception:
            log.exception("Unhandled exception while processing payload for event %s", event_name)
            return

        log.debug("Processed event %s with payload %s, got result %s", event_name, payload, result)

        # XXX TODO: add result storage
