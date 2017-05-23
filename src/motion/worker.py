import atexit
import logging
import Queue
import multiprocessing
import signal
import sys

log = logging.getLogger(__name__)


class MotionProcess(object):
    """Base class for forked workers via multiprocessing.Process"""
    def __init__(self):
        self.process = None
        self.alive = True

        atexit.register(self.shutdown)
        self.process = multiprocessing.Process(target=self._run)
        self.process.start()

    def shutdown(self):
        if self.process:
            log.info("%s shutting down", self.__class__.__name__)
            self.process.terminate()
            self.process.join()
            self.process = None

    def _signal_handler(self, signum, frame):
        log.info("Caught signal %s", signum)
        self.alive = False

    def _run(self):
        signal.signal(signal.SIGTERM, self._signal_handler)

        log.info("%s starting", self.__class__.__name__)

        while self.alive:
            try:
                self.work()
            except Exception:
                log.exception("Unhandled exception in base MotionProcess")
                self.alive = False
                return sys.exit(1)

    def work(self):
        raise NotImplementedError


class MotionConsumer(MotionProcess):
    def __init__(self, app):
        self.app = app
        super(MotionConsumer, self).__init__()

    def work(self):
        self.app.consume()

        # we should never reach this
        log.error("Failed to consume from Kinesis!")
        sys.exit(2)


class MotionWorker(MotionProcess):
    def __init__(self, queue, responders):
        self.queue = queue
        self.responders = responders
        super(MotionWorker, self).__init__()

    def work(self):
        try:
            event_name, payload = self.queue.get(block=True, timeout=0.1)
        except Queue.Empty:
            return
        except (SystemExit, KeyboardInterrupt):
            log.error("Exiting via interrupt")
            self.alive = False
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

        # XXX TODO: add result storage?
