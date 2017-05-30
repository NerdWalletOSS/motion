import functools
import logging
import multiprocessing

import boto3

from kinesis.consumer import KinesisConsumer
from kinesis.producer import KinesisProducer

from .marshal import JSONMarshal, MarshalFailure
from .worker import MotionConsumer, MotionWorker

log = logging.getLogger(__name__)


class Motion(object):
    _INSTANCES = []

    def __new__(cls, *args, **kwargs):
        inst = super(Motion, cls).__new__(cls, *args, **kwargs)
        Motion._INSTANCES.append(inst)
        return inst

    def __init__(self, stream_name, marshal=None, concurrency=None, boto3_session=None):
        """Create a new motion application

        :param stream_name: the name of the kinesis stream to use
        :param marshal: a marshal object to use on messages
        :param concurrency: an integer specifying the number of workers to start, defaults to 1
        :param boto3_session: the boto3 Session object to use for our client, can also be a dict that will be passed to
                              the boto3 Session object as kwargs
        """
        if isinstance(boto3_session, dict):
            boto3_session = boto3.Session(**boto3_session)
        self.boto3_session = boto3_session

        self.stream_name = stream_name
        self.producer = KinesisProducer(stream_name, boto3_session=boto3_session)
        self.consumer = KinesisConsumer(stream_name, boto3_session=boto3_session)
        self.marshal = marshal or JSONMarshal()
        self.concurrency = concurrency or 1
        self.responder_queue = multiprocessing.Queue()
        self.responders = {}
        self.workers = {}

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return 'Motion on {0}'.format(self.stream_name)

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
                event_name, payload = self.marshal.to_native(message['Data'])
            except MarshalFailure:
                log.warn("Failed to marshal message to native objects, skipping")
                continue
            except Exception:
                log.exception("Unhandled exception while marshaling message to native: %s", message)
                continue

            if event_name not in self.responders:
                log.warn("No responder for event %s registered, skipping", event_name)
                continue

            self.responder_queue.put((event_name, payload))

    def dispatch(self, event_name, payload):
        self.producer.put(self.marshal.to_bytes(event_name, payload))

    def check_workers(self):
        """Check the consumer and task workers for this app, starting them if necessary"""
        def start_if_not_alive(key, new_worker):
            """Closure to check a worker, pass a key and lambda that creates the worker if needed"""
            try:
                worker = self.workers[key]
            except KeyError:
                log.info("Starting %s %s", self, key)
                worker = new_worker()
                self.workers[key] = worker

            if not worker.process.is_alive():
                log.error("%s %s is no longer alive!", self, key)
                worker.shutdown()
                del self.workers[key]

        log.debug("Checking %s consumer", self)
        start_if_not_alive("consumer", lambda: MotionConsumer(self))

        log.debug("Checking %s task workers", self)
        for idx in xrange(self.concurrency):
            start_if_not_alive(
                # for humans, we make our index 1 based
                'worker %d' % (idx + 1),
                lambda: MotionWorker(self.responder_queue, self.responders)
            )
