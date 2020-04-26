"""Config your database.

    The best way is to include a config.py file in your project, and then a dict
    named aiomyorm, which contains your database configuration, as follow::

        aiomyorm = {
                'maxsize': 3,
                'user': 'root',
                'password': '123456',
                'db': 'test',
                'engine': 'mysql'
            }

    By default, you need to include the config.py file in the same level directory
    of your main file. You can call the set_config_model() method to specify the
    location of the config file again, as follow::
        set_config_model('myconfigdirectory.myconfig')

    If you don't want to configure the config.py file, you can also call the set_config()
    method to configure your database connection, as follow::

        set_config(engine='sqlite',
           db='test.db')

    configuration options:
        common:
            * engine (str) : database engine (``'mysql', 'sqlite'``)
        for sqlite:
            * db (str) : the database file for sqlite.
            * other options : same as sqlite3.
        for mysql:
            * db (str) :	database to use, None to not use a particular one.
            * minsize (int) : minimum sizes of the pool.
            * maxsize (int) : maximum sizes of the pool.
            * echo (bool) : executed log SQL queryes default : False.
            * debug (bool) : echo the debug log default : False.
            * host (str) :	host where the database server is located, default : localhost.
            * port (str) :	MySQL port to use, default : 3306.
            * user (str) :	username to log in as.
            * password (str) : password to use.
            * unix_socket (str) :optionally, you can use a unix socket rather than TCP/IP.
            * charset (str) : charset you want to use, for example ‘utf8’.
            * sql_mode:	default sql-mode to use, like ‘NO_BACKSLASH_ESCAPES’
            * read_default_file : specifies my.cnf file to read these parameters\
                from under the [client] section.See aiomysql.
            * conv : decoders dictionary to use instead of the default one.\
                This is used to provide custom marshalling of types. See pymysql.converters.
            * client_flag : custom flags to send to MySQL. Find potential values in pymysql.constants.CLIENT.
            * use_unicode : whether or not to default to unicode strings.
            * connect_timeout : Timeout in seconds before throwing an exception when connecting.
            * autocommit : Autocommit mode. None means use server default. (default: False)
            * ssl : Optional SSL Context to force SSL
            * server_public_key : SHA256 authenticaiton plugin public key value.
            * read_default_group (str) : Group to read from in the configuration file.
            * no_delay (bool) : disable Nagle’s algorithm on the socket
            * auth_plugin: String to manually specify the authentication plugin to use, i.e you will want to use
            * mysql_clear_password when using IAM authentication with Amazon RDS. (default: Server Default)
            * program_name: Program name string to provide when handshaking with MySQL. (default: sys.argv[0])
            * server_public_key: SHA256 authenticaiton plugin public key value.
            * loop : is an optional event loop instance, asyncio.get_event_loop() is used if loop is not specified.
            * init_command (str) : initial SQL statement to run when connection is established.
    default::

            minsize=1,
            maxsize=10,
            echo=False,
            debug=False,
            host="localhost",
            port=3306,
            user=None,
            password="",
            db=None,
            unix_socket=None,
            charset='',
            sql_mode=None,use_unicode=None,
            read_default_file=None,
            connect_timeout=None,
            autocommit=False,
            ssl=None,
            server_public_key=None,
            loop=None,
            auth_plugin='',
            program_name='',
            read_default_group=None,
            no_delay=False,
            init_command=None
    """

import importlib

CONFIG_DICT = {}
CONFIG_MODEL = 'config'
_LOOP = None


def _get_loop():
    return _LOOP


def _get_config():
    if CONFIG_DICT:
        return CONFIG_DICT
    else:
        return importlib.import_module(CONFIG_MODEL).aiomyorm


def set_config_model(config_model):
    """Set a custom model as config model."""
    global CONFIG_MODEL
    CONFIG_MODEL = config_model


def set_config(**kwargs):
    """Set configs manually.

        Args:
            kwargs: see module's __doc__ configuration options.
    """
    from .connection import _set_engine
    engine = kwargs.pop('engine')
    _set_engine(engine)
    global CONFIG_DICT
    CONFIG_DICT = kwargs


def set_loop(loop):
    """set a event loop."""
    global _LOOP
    _LOOP = loop


def unset_loop(loop):
    """unset the event loop."""
    global _LOOP
    _LOOP = None
