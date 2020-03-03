import collections
import fnmatch
import functools
import logging
import multiprocessing

import boto3
import six
import six.moves

from kinesis.consumer import KinesisConsumer
from kinesis.producer import KinesisProducer
from kinesis.state import DynamoDB

from .marshal import JSONMarshal, MarshalFailure
from .worker import MotionConsumer, MotionWorker

log = logging.getLogger(__name__)


def cached_property(func):
    attr = '_{0}'.format(func.__name__)

    @property
    @functools.wraps(func)
    def _cached_property(self):
        try:
            return getattr(self, attr)
        except AttributeError:
            res = func(self)
            setattr(self, attr, res)
            return res

    return _cached_property


@six.python_2_unicode_compatible
class Motion(object):
    _INSTANCES = []

    def __new__(cls, *args, **kwargs):
        if six.PY2:
            inst = super(Motion, cls).__new__(cls, *args, **kwargs)
        else:
            inst = super(Motion, cls).__new__(cls)
        Motion._INSTANCES.append(inst)
        return inst

    def __init__(self, stream_name, marshal=None, concurrency=None, boto3_session=None, state_table_name=None, worker_class=None):
        """Create a new motion application

        :param stream_name: the name of the kinesis stream to use
        :param marshal: a marshal object to use on messages
        :param concurrency: an integer specifying the number of workers to start, defaults to 1
        :param boto3_session: the boto3 Session object to use for our client, can also be a dict that will be passed to
                              the boto3 Session object as kwargs
        :param state_table_name: the name of the DynamoDB table name used to store state in
        :param worker_class: The class to use for workers, defaults to MotionWorker
        """
        if isinstance(boto3_session, dict):
            boto3_session = boto3.Session(**boto3_session)
        self.boto3_session = boto3_session

        self.stream_name = stream_name
        self.state_table_name = state_table_name
        self.marshal = marshal or JSONMarshal()
        self.concurrency = concurrency or 1
        self.responder_queue = multiprocessing.Queue()
        self.responders = collections.defaultdict(list)
        self.worker_class = worker_class or MotionWorker
        self.workers = {}

    def __str__(self):
        return 'Motion on {0}'.format(self.stream_name)

    @cached_property
    def consumer_state(self):
        if self.state_table_name:
            return DynamoDB(self.state_table_name, boto3_session=self.boto3_session)

    @cached_property
    def producer(self):
        return KinesisProducer(self.stream_name, boto3_session=self.boto3_session)

    @cached_property
    def consumer(self):
        return KinesisConsumer(self.stream_name, boto3_session=self.boto3_session, state=self.consumer_state)

    def respond_to(self, pattern, pass_event_name=False):
        def decorator(func):
            self.responders[pattern].append(func)
            func._motion_pass_event_name = pass_event_name
            return func
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

            for responder_pattern in self.responders:
                if fnmatch.fnmatch(event_name, responder_pattern):
                    log.debug("Matched responder pattern %s against event name %s", responder_pattern, event_name)
                    for index in six.moves.range(len(self.responders[responder_pattern])):
                        self.responder_queue.put((responder_pattern, index, event_name, payload))

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
        for idx in six.moves.range(self.concurrency):
            start_if_not_alive(
                # for humans, we make our index 1 based
                'worker %d' % (idx + 1),
                lambda: self.worker_class(self.responder_queue, self.responders)
            )
