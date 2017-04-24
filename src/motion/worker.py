import atexit
import logging
import Queue
import multiprocessing
import signal

log = logging.getLogger(__name__)


class MotionWorker(object):
    def __init__(self, queue, responders):
        self.queue = queue
        self.responders = responders
        self.process = None
        self.alive = True

        atexit.register(self.shutdown)
        self.process = multiprocessing.Process(target=self.run)
        self.process.start()

    def shutdown(self):
        if self.process:
            log.info("Worker shutting down")
            self.process.terminate()
            self.process.join()
            self.process = None

    def signal_handler(self, signum, frame):
        log.info("Caught signal %s", signum)
        self.alive = False

    def run(self):
        signal.signal(signal.SIGTERM, self.signal_handler)

        log.info("Worker starting")

        while self.alive:
            try:
                event_name, payload = self.queue.get(block=True, timeout=0.1)
            except Queue.Empty:
                continue
            except (SystemExit, KeyboardInterrupt):
                log.error("Exiting via interrupt")
                self.alive = False
                break
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
