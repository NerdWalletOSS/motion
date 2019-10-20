import multiprocessing
import signal

from motion import Motion, MotionWorker

try:
    from unittest.mock import PropertyMock, call
except ImportError:
    from mock import PropertyMock, call


def test_basic():
    tasks = Motion(stream_name='test')

    # Replace the _consumer attr, which is what consume() will iterate over
    tasks._consumer = [
        {"Data": '{"event_name": "simple", "payload": "expected payload"}'},
    ]

    # Create a queue to ensure that our simple task is run
    # Since the code inside simple will run in a separate process (the worker)
    # we need to use a queue to pass the value back for us to assert on
    success = multiprocessing.Queue()

    @tasks.respond_to('simple')
    def simple(payload):
        assert payload == "expected payload"
        success.put(True)

    # Setup an alarm to make sure our test has a hard timeout
    signal.alarm(5)

    # Start the worker
    worker = MotionWorker(tasks.responder_queue, tasks.responders)

    # Consume the message
    tasks.consume()

    # Ensure our task was called
    assert success.get(block=True, timeout=1) is True

    # Shutdown
    worker.shutdown()
    signal.alarm(0)
