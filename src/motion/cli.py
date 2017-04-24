import importlib
import logging
import os
import sys
import time

import click

from .motion import Motion

log = logging.getLogger(__name__)


@click.group()
@click.option('-I', '--import', 'imports', required=True, multiple=True)
@click.option('-D', '--debug', is_flag=True, default=False)
def main(imports, debug):
    """Motion.
    """
    if debug:
        log_level = logging.DEBUG
        log_format = '%(levelname)s %(process)d %(name)s:%(lineno)d %(message)s'
    else:
        log_level = logging.INFO
        log_format = '%(message)s  [pid:%(process)d]'

        # turn down chatty loggers
        logging.getLogger('botocore.vendored.requests.packages.urllib3').level = logging.WARN

    logging.basicConfig(level=log_level, format=log_format)

    # before we import we put the cwd into the path so that we can do relative imports
    sys.path.insert(0, os.getcwd())

    log.info("Motion starting up")

    for import_name in imports:
        try:
            log.debug("Trying to import %s", import_name)
            importlib.import_module(import_name)
        except ImportError:
            raise click.BadParameter("Invalid import specified -- '%s' did not import" % import_name)

    if len(Motion._INSTANCES) == 0:
        log.critical("No Motion instances found in imports")
        sys.exit(1)


@main.command()
def worker():
    """Run Motion workers"""
    try:
        while True:
            for motion in Motion._INSTANCES:
                motion.check_workers()
            time.sleep(1)
    except KeyboardInterrupt:
        pass
