import logging
import aiomysql
from typing import Optional, Union
from ..log import logger, _logsql
from ..connection import _Engine


async def __create_connection(echo=False, debug=False, **kwargs):
    """Create a connection pool to mysql databases.

    Args:
        See setconf's __doc__ .
    """
    logger.setLevel(logging.WARNING)
    if echo:
        logger.setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
    # engine = _create_engine(engine)
    kwargs['cursorclass'] = aiomysql.DictCursor
    db = kwargs.pop('db')
    __pool = await aiomysql.create_pool(**kwargs)
    _Engine._created = True
    logger.debug('*** create database connection pool with %s ***' % db)
    _Connection._set_pool(__pool)
    _Transaction._set_pool(__pool)
    await _execute('CREATE DATABASE IF NOT EXISTS `%s`;\nUSE %s;' % (db, db))


async def _close_db_connection():
    """Close connection with database."""
    await _Connection._close_pool()  # the _Connection and Aton_Transaction use the same pool
    _Connection._set_pool(None)
    _Transaction._set_pool(None)


class _Connection(object):
    """A async context manager to run a custom sql statement.

    Creates new connection size of pool is less than maxsize.
    Returns a engine._Connection instance.
    You can also use this connection in ORM by specifying the conn parameter.
    If you have not set autocommit=True, you should commit manual by use conn.commit().
    """

    @classmethod
    def _set_pool(cls, pool):
        cls._pool = pool

    @classmethod
    async def _close_pool(cls):
        """Close the connection pool"""
        cls._pool.close()
        await cls._pool.wait_closed()

    def __init__(self):
        self._conn = None

    async def __aenter__(self):
        self._conn = await self._pool.acquire()
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        try:
            await self._pool.release(self._conn)
        finally:
            self._conn = None


class _Transaction(_Connection):
    """Get a connection to do atomic transaction.

     This is a subclass of _Connection and they have the same usage,
     and on exit, this connection will automatically commit or roll back on error.
     You can also use this connection in ORM by specifying the conn parameter.
     Example:
        async whit connection.Transaction() as conn:
            Table(tl1='abc',tl2=123).save(conn=conn)
    """

    @classmethod
    def _set_pool(cls, pool):
        cls._pool = pool

    def __init__(self):
        self._conn = None

    async def __aenter__(self):
        self._conn = await self._pool.acquire()
        await self._conn.begin()
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self._conn.rollback()
        else:
            await self._conn.commit()
        try:
            await self._pool.release(self._conn)
        finally:
            self._conn = None


async def _select(sql: str,
                  args: Optional[Union[list, tuple]] = (),
                  conn: Optional[_Connection] = None) -> list:
    """execute a select query, and return a list of result.

        Args:
            sql(str): a sql statement, use ? as placeholder as same as pyMySql.
            args(list or tuple): argument in placeholder.
            conn: use this parameter to specify a custom connection.

        Return:
             (list) a list of result.
    """
    _logsql(sql, args)
    sql = sql.replace('?', '%s')
    if not conn:
        async with _Transaction() as conn:
            cur = await conn.cursor()
            await cur.execute(sql, args)
            rs = await cur.fetchall()
            await cur.close()
            logger.info('select return %s rows' % len(rs))
            return rs
    else:
        cur = await conn.cursor()
        await cur.execute(sql, args or ())
        rs = await cur.fetchall()
        await cur.close()
        logger.info('select return %s rows' % len(rs))
        return rs


async def _execute(sql: str,
                   args: Optional[Union[list, tuple]] = (),
                   conn: Optional[_Connection] = None) -> int:
    """execute a insert,update or delete query, and return the number of affected rows.

        Args:
            sql(str): a sql statement, use ? as placeholder as same as pyMySql.
            args(list or tuple): argument in placeholder.
            conn: use this parameter to specify a custom connection.

        Return:
              (int) affected rows.
    """
    _logsql(sql, args)
    sql = sql.replace('?', '%s')
    if not conn:
        async with _Transaction() as conn:
            cur = await conn.cursor()
            await cur.execute(sql, args)
            rs = cur.rowcount
            logger.info('%s rows affected' % rs)
            return rs
    else:
        cur = await conn.cursor()
        await cur.execute(sql, args or ())
        rs = cur.rowcount
        logger.info('%s rows affected' % rs)
        return rs
