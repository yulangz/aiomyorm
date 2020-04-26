import logging
import aiosqlite
from typing import Optional, Union
from ..log import logger, _logsql
from ..connection import _Engine


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class _ConnManager(object):
    _conn = None

    @classmethod
    async def init_conn(cls, db, **kwargs):
        cls._conn = await aiosqlite.connect(db, **kwargs)
        cls._conn.row_factory = dict_factory


async def __create_connection(echo=False, debug=False, **kwargs):
    """Create a connection to sqlite database.

    Args:
        See setconf's __doc__ .
    """
    logger.setLevel(logging.WARNING)
    if echo:
        logger.setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
    _Engine._created = True
    # engine = _create_engine(engine)
    # kwargs['cursorclass'] = engine.DictCursor
    # __pool = await _create_pool(**kwargs)
    db = kwargs.pop('db')
    logger.debug('*** create database connection with %s ***' % db)
    await _ConnManager.init_conn(db, **kwargs)


async def _close_db_connection():
    """Close connection with database."""
    await _ConnManager._conn.close()
    _ConnManager._conn = None


class _Connection(object):
    """A async contextmanager to run a custom sql statement.

    Get the connection with database.
    You can also use this connection in ORM by specifying the conn parameter.
    This method will not commit, so you should commit manually.
    """

    def __init__(self):
        self._conn = None

    async def __aenter__(self):
        self._conn = _ConnManager._conn
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        self._conn = None


class _Transaction(_Connection):
    """Get a connection to do atomic transaction.

     This is a subclass of Connection and they have the same usage,
     and on exit, this connection will automatically commit or roll back on error.
     You can also use this connection in ORM by specifying the conn parameter.
     Example:
        async whit connection.Tansaction() as conn:
            Table(tl1='abc',tl2=123).save(conn=conn)
    """

    def __init__(self):
        self._conn = None

    async def __aenter__(self):
        self._conn = _ConnManager._conn
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self._conn.rollback()
        else:
            await self._conn.commit()
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
