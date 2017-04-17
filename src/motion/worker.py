import logging
import multiprocessing
import signal

log = logging.getLogger(__name__)


class MotionWorker(object):
    def __init__(self, queue, responders):
        self.queue = queue
        self.responders = responders
        self.process = None
        self.alive = True

    def start(self):
        assert self.process is None, "Already started"
        self.process = multiprocessing.Process(target=self.run)
        self.process.start()

    def run(self):
        while self.alive:
            try:
                event_name, payload = self.queue.get()
            except Exception:
                log.exception("Failed to get event & payload from queue")
                continue

            responder = self.responders[event_name]

            try:
                result = responder(payload)
            except Exception:
                log.exception("Unhandled exception while processing payload for event %s", event_name)
                continue

            log.debug("Processed event %s with payload %s, got result %s", event_name, payload, result)

            # XXX TODO: add result storage?
