import logging
import sys

try:
    from queue import Empty
except ImportError:
    from Queue import Empty

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

    def respond(self, responder, event_name, payload):
        if responder._motion_pass_event_name:
            return responder(payload, event_name=event_name)

        return responder(payload)

    def loop(self):
        try:
            responder_pattern, responder_index, event_name, payload = self.queue.get(block=True, timeout=0.25)
        except Empty:
            return 0
        except Exception:
            log.exception("Failed to get event payload from queue")
            return 0

        responder = self.responders[responder_pattern][responder_index]

        try:
            result = self.respond(responder, event_name, payload)
        except Exception:
            log.exception("Unhandled exception while processing payload for event %s", event_name)
            return 0

        log.debug("Processed event %s with payload %s, got result %s", event_name, payload, result)

        # XXX TODO: add result storage

        return 0
