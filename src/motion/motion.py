import functools
import logging

from kinesis.consumer import KinesisConsumer
from kinesis.producer import KinesisProducer

from motion.marshal import JSONMarshal, MarshalFailure
from motion.workers import MotionWorker

log = logging.getLogger(__name__)


class Motion(object):
    def __init__(self, stream_name, marshal=None):
        self.stream_name = stream_name
        self.producer = KinesisProducer(stream_name)
        self.consumer = KinesisConsumer(stream_name)
        self.marshal = marshal or JSONMarshal()
        self.responder_queue = multiprocessing.Queue()
        self.responders = {}
        self.workers = {}

    def respond_to(self, event_name):
        def decorator(func):
            assert event_name not in self.responders, "Event %s already registered to %s" % (
                event_name,
                self.responders[event_name]
            )

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            self.responders[event_name] = wrapper
            return wrapper
        return decorator

    def consume(self):
        for message in self.consumer:
            log.debug("Consumed message: %s", message)
            try:
                event_name, payload = self.marshal.to_native(message)
            except MarshalFailure:
                log.warn("Failed to marshal message to native objects, skipping")
                continue
            except Exception:
                log.exception("Unhandled exception while marshaling message to native: %s", message)
                continue

            if event_name not in self.responders:
                log.warn("No responder for event %s registered, skipping", event_name)
                continue

            self.responder_queue.put_nowait((event_name, payload))

    def dispatch(self, event_name, payload):
        self.producer.put(self.marshal.to_bytes(event_name, payload))

    def start_workers(self, concurrency):
        for idx in xrange(concurrency):
            self.workers[idx] = MotionWorker(self.responder_queue, self.responders)
            self.workers[idx].start()
