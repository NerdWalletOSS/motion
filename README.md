# Motion

![Build Status](https://img.shields.io/travis/NerdWalletOSS/motion.svg)
![CodeCov](https://img.shields.io/codecov/c/github/NerdWalletOSS/motion.svg)
![PyPI - Version](https://img.shields.io/pypi/v/motion.svg)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/motion.svg)

Motion is a high-level task dispatch & response framework for Amazon Kinesis. It is built on top of the low-level
kinesis-python library and inspired by the task definition of Celery.

**Motion is still under heavy development.  Things here may change**

## Usage

Create a `Motion` object:

```
from motion import Motion

tasks = Motion(stream_name='my-kinesis-stream')
```

### Responding to tasks

```
@tasks.respond_to('my-event')
def my_event_handler(payload):
    # do something with payload...
```

### Dispatching tasks

```
# dispatch an event 'my-event' with the specified payload
tasks.dispatch('my-event', {'foo': 'bar'})
```

### Running workers

## Marshalling

Events and Payloads are converted into byte streams suitable for transport on a Kinesis stream via the process of
Marshalling.  Motion ships with a default JSON Marshalling class that simply converts a Python object into its JSON
equivalent, wrapped with the event name, but the Marshalling operations can be extended to support any type of
serialization that is desired (i.e. protobuf, avro, etc)

To implement a custom Marshal you must satisfy the following method signature:

```
class MyMarshal(object):
    def to_native(self, payload):
        # de-serialize payload
        return event_name, event_payload

    def to_bytes(self, event_name, payload):
        # serialize payload
        return serialized_payload
```

Then pass an instance of your marshalling class when you create your `Motion` instance via the `marshal=` keyword.

### Event names

In the basic example the `.respond_to` decorator is used with a string, since that's what the default JSON Marshal
returns, but since custom marshalling can return anything for the event_name during the `.to_native` call then you
can use whatever symbol you choose in the `.respond_to` decorator.
