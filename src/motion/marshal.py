import json
import logging

log = logging.getLogger(__name__)


class MarshalFailure(Exception):
    """Failed to marshal a message to bytes or native"""
    def __init__(self, error, payload):
        super(MarshalFailure, self).__init__(error)
        self.payload = payload


class JSONMarshal(object):
    """Simple JSON Marshal"""
    JSONEncoder = None
    JSONDecoder = None
    
    def to_bytes(self, event_name, payload):
        try:
            return json.dumps({
                'event_name': event_name,
                'payload': payload
            }, cls=self.JSONEncoder)
        except ValueError:
            raise MarshalFailure("Could not convert payload to JSON", payload)

    def to_native(self, payload):
        try:
            native = json.loads(payload, cls=self.JSONDecoder)
        except ValueError:
            raise MarshalFailure("Could not load valid JSON from payload", payload)
        return native['event_name'], native['payload']
