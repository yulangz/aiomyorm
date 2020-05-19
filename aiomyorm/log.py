"""Logging configuration."""
import logging

logging.debug('')
# Name the logger after the package.
logger = logging.getLogger(__package__)


def _logsql(sql, args=()):
    args = tuple(args)
    for arg in args:
        sql = str(sql).replace('?', str(arg), 1)
    logger.info(sql)
