import logging

from motion import Motion

log = logging.getLogger(__name__)

tasks = Motion(
    stream_name='borgstrom-test'
)


@tasks.respond_to('simple')
def simple(payload):
    log.info("Simple task: %s", payload)
