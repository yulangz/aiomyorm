from typing import Optional, Union
from .set_config import _get_config


class _Engine(object):
    """Indicates the database engine that is currently in use."""
    ENGINE = 0
    MYSQL = 1
    SQLITE = 3
    _created = False  # Indicates whether the connection to the database has been created.

    @classmethod
    def set_engine(cls, this_engine: str):
        cls.ENGINE = getattr(cls, this_engine.upper())

    @classmethod
    def is_mysql(cls):
        return cls.ENGINE == cls.MYSQL

    @classmethod
    def is_sqlite(cls):
        return cls.ENGINE == cls.SQLITE


try:
    _engine = _get_config().pop('engine').lower()
except KeyError:
    _engine = 'sqlite'
except ModuleNotFoundError:
    _engine = ''
if _engine == 'mysql':
    _Engine.set_engine('mysql')
    from .engine.mysql import __create_connection, _close_db_connection, _select, _execute, _Connection, _Transaction
elif _engine == 'sqlite':
    _Engine.set_engine('sqlite')
    from .engine.sqlite import __create_connection, _close_db_connection, _select, _execute, _Connection, _Transaction


def _set_engine(new_engine: str):
    """Set a engine, import related modules, use in setconf.set_config."""
    global __create_connection, _close_db_connection, _select, _execute, _Connection, _Transaction
    engine = new_engine.lower()
    if engine == 'mysql':
        _Engine.set_engine('mysql')
        from .engine.mysql import __create_connection, _close_db_connection, _select, _execute, _Connection, \
            _Transaction
    elif engine == 'sqlite':
        _Engine.set_engine('sqlite')
        from .engine.sqlite import __create_connection, _close_db_connection, _select, _execute, _Connection, \
            _Transaction


def _create_connection(echo: bool = False, debug: bool = False, **kwargs):
    """
    Create a connection to databases.

    Args:
        See setconf's __doc__ .
    """
    return __create_connection(echo=echo, debug=debug, **kwargs)


async def close_db_connection():
    """Close connection with database.You may sometime need it."""
    return await _close_db_connection()


def Connection():
    """
    A async context manager to run a custom sql statement.

    Creates new connection.Returns a Connection instance.
    You can also use this connection in ORM by specifying the conn parameter.
    If you have not set autocommit=True, you should commit manual by use ``conn.commit()``.
    """
    return _Connection()


def Transaction():
    """
    Get a connection to do atomic transaction.

    This is a subclass of Connection and they have the same usage,
    and on exit, this connection will automatically commit or roll back on error.
    You can also use this connection in ORM by specifying the conn parameter.
    Example::

        async whit connection.Transaction() as conn:
            await Table(tl1='abc',tl2=123).save(conn=conn)
    """
    return _Transaction()


def select(sql: str,
           args: Optional[Union[list, tuple]] = (),
           conn: Optional[Connection] = None) -> list:
    """
    Execute a select query, and return a list of result.You can use this method
    when you encounter a query that ORM cannot complete

    Args:
        sql(str): a sql statement, use ? as placeholder.
        args(list or tuple): argument in placeholder.
        conn: use this parameter to specify a custom connection.

    Return:
         (list) a list of result.
    """
    return _select(sql, args, conn)


def execute(sql: str,
            args: Optional[Union[list, tuple]] = (),
            conn: Optional[Connection] = None) -> int:
    """
    Execute a insert,update or delete query, and return the number of affected rows.You can use this method
    when you encounter a query that ORM cannot complete.

    Args:
        sql(str): a sql statement, use ? as placeholder.
        args(list or tuple): argument in placeholder.
        conn: use this parameter to specify a custom connection.

    Return:
          (int) affected rows.
    """
    return _execute(sql, args, conn)
