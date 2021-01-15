# :TODO support multi-table query, let __auto__ support sqlite
import logging
import asyncio
import datetime
import decimal
from types import MethodType
from typing import Union, Optional, Tuple, NoReturn, List, Dict
from .field import Field, _field_map, _integer_field, _varchar_field, _datetime_field, _decimal_field, _text_field, \
    _TableDefault, table_default
from .connection import select, execute, _create_connection, _Engine
from .set_config import _get_config, _get_loop
from .log import logger
from .lib import StringBuff
from .lib import classonlymethod


class ModelMetaClass(type):
    """Metaclass for Model class"""

    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        table_name = attrs.get('__table__', None) or name
        logger.debug('Find Model: %s (%s)' % (name, table_name))
        loop = _get_loop()
        if not loop:
            loop = asyncio.get_event_loop()
        if not _Engine._created:
            loop.run_until_complete(_create_connection(**_get_config()))
        auto = attrs.get('__auto__', False)
        if auto:
            # Get fields in table and insert into attrs with it's appropriate Field
            task = loop.create_task(select("""
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                COLUMN_COMMENT,
                COLUMN_DEFAULT,
                IS_NULLABLE,
                COLUMN_KEY,
                CHARACTER_MAXIMUM_LENGTH,
                CHARACTER_OCTET_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                EXTRA,
                COLUMN_TYPE
            FROM
                INFORMATION_SCHEMA.COLUMNS
            WHERE
                TABLE_SCHEMA = ? AND
                TABLE_NAME = ?""", (_get_config()['db'], table_name)))
            # method __new__ dose not allow await, and this method will only use once when create model class,
            # so blocking call with run_until_complete() will not cause blocking at run time.
            loop.run_until_complete(task)
            table_fields = task.result()
            for field in table_fields:
                # field : each field(column) in this table
                field_name = field['COLUMN_NAME']
                if field_name in attrs.keys():
                    continue
                else:
                    params = {}  # parameters to create field
                    field_type = field['DATA_TYPE']

                    params['primary_key'] = False
                    if field['COLUMN_KEY'] == 'PRI':
                        params['primary_key'] = True

                    params['null'] = False
                    if field['IS_NULLABLE'] == 'YES':
                        params['null'] = True

                    params['comment'] = field['COLUMN_COMMENT']
                    table_field_default = field['COLUMN_DEFAULT']
                    if table_field_default is None and params['null'] is True:
                        params['default'] = None

                    # Different parameters between different fields
                    if field_type in _integer_field:
                        if 'unsigned' in field['COLUMN_TYPE']:
                            params['unsigned'] = True
                        if table_field_default is not None:
                            params['default'] = int(table_field_default)
                    elif field_type in _varchar_field:
                        params['length'] = field['CHARACTER_MAXIMUM_LENGTH']
                        if table_field_default is not None:
                            params['default'] = str(table_field_default)
                    elif field_type in _text_field:
                        if table_field_default is not None:
                            params['default'] = str(table_field_default)
                    elif field_type in _decimal_field:
                        if table_field_default is not None:
                            if field_type == 'decimal':
                                params['default'] = decimal.Decimal(table_field_default)
                            else:
                                params['default'] = float(table_field_default)
                        params['total_digits'] = field['NUMERIC_PRECISION']
                        params['decimal_digits'] = field['NUMERIC_SCALE']
                    elif field_type in _datetime_field:
                        if table_field_default is not None:
                            if field_type == 'time':
                                params['default'] = datetime.datetime.strptime(table_field_default, '%H:%M:%S')
                            elif field_type == 'date':
                                params['default'] = datetime.datetime.strptime(table_field_default, '%Y-%m-%d')
                            else:
                                params['default'] = datetime.datetime.strptime(table_field_default, '%Y-%m-%d %H:%M:%S')
                    else:
                        params['column_type'] = field_type
                        params['default'] = None

                    table_extra = field['EXTRA']
                    if table_extra:  # to use table default, such as auto_increment
                        params['default'] = table_default(table_extra)
                    attrs[field_name] = _field_map.get(field_type, Field)(**params)  # Field class in _field_map
                    logger.debug('auto set field %s : %s', field_name, attrs[field_name])

        mapping = dict()
        fields = []
        primary_key = None
        # get field mapping
        for k, v in attrs.items():
            if isinstance(v, Field):
                logger.debug('Find mapping %s ==> %s' % (k, v))
                mapping[k] = v
                v._field_name = k
                if v.primary_key:
                    logger.debug('Find primary_key %s' % k)
                    if primary_key:
                        raise RuntimeError("Duplicated primary key")
                    primary_key = k
                fields.append(k)

        if not primary_key:
            raise RuntimeError("Can not find a primary key")

        attrs['_db'] = attrs['_current_db'] = _get_config()['db']
        attrs['__table__'] = table_name
        attrs['__auto__'] = auto
        attrs['_mapping'] = mapping
        attrs['_primary_key'] = primary_key
        attrs['_fields'] = fields
        attrs['_fields_without_pk'] = [f for f in fields if f != primary_key]
        attrs['_query_fields'] = ['`%s`.`%s`' % (table_name, f) for f in fields]
        attrs['_where'] = []
        attrs['_where_args'] = []
        attrs['_exclude'] = []
        attrs['_exclude_args'] = []
        attrs['_or_connect'] = False
        attrs['_distinct'] = False
        attrs['_order_by'] = []
        attrs['_limit'] = 0
        attrs['_conn'] = None
        attrs['_limit_offset'] = 0
        mod = type.__new__(cls, name, bases, attrs)
        # set belong model for each Field
        for k, v in attrs.items():
            if isinstance(v, Field):
                v._belong_model = mod
        return mod


class Model(dict, metaclass=ModelMetaClass):
    """
    The basic model class.

    Attributes:
        __table__ : The table name of this model.If you do not set this attribute,
            class name will be used by default.
        __auto__ : If true, fields will automatically retrieved from the table, default False.
            **Warnings: __auto__ dose not support sqlite.**
        the field you define : All the fields you define. In class it will be field while in instance it is
            the value of this field.
    """

    def __init__(self, _new_created: bool = True, _pk_value=None, **kwargs):
        fields = self.get_fields()
        pk = self.get_primary_key()
        if _new_created is False and _pk_value is None:
            _pk_value = kwargs[pk]
        self._new_created = _new_created  # Used to distinguish INSERT statement from UPDATE statement in save() method.
        self._pk_value = _pk_value  # Implicitly save the primary key value
        for k, v in kwargs.items():
            if k in fields:
                self[k] = v
            else:
                self.k = v
        self._conn = None

        def use(self, conn):
            """Specify a connection."""
            self._conn = conn
            return self

        # The classmethod use() returns cls(class) here,this is right in class,
        # but in instance it should return self(instance). Since they have the
        # same performance, let them have the same name.
        super().__setattr__('use', MethodType(use, self))

    def __getattribute__(self, key):
        fields = super().__getattribute__('_fields')
        if key in fields:
            try:
                return self[key]
            except KeyError:
                raise AttributeError("field '%s' has no value " % (key))
        else:
            return super().__getattribute__(key)

    def __setattr__(self, key, value):
        fields = self.get_fields()
        if key in fields:
            self[key] = value
        else:
            super().__setattr__(key, value)

    def __str__(self):
        return "%s" % (', '.join(['%s:%s' % (k, v) for k, v in self.items()]))

    def __repr__(self):
        return '<%s: {%s}>' % (self.__class__.__name__, self)

    @classmethod
    def get_mapping(cls):
        """Get the fields mapping."""
        return cls._mapping

    @classmethod
    def get_fields(cls):
        """Get the names of all fields"""
        return cls._fields

    @classmethod
    def get_primary_key(cls):
        """Get the name of the primary key"""
        return cls._primary_key

    @classmethod
    def get_db(cls):
        """Get the database this model belongs to."""
        return cls._db

    @classonlymethod
    def change_db(cls, db: str):
        """
        Change the database this model belongs to.

        **Warnings: not support sqlite**
        """
        cls._db = cls._current_db = db
        return cls

    @classonlymethod
    def change_db_one_time(cls, db: str):
        """Change the database one time.

            You can use this method temporarily change the database this model
            belongs in the next query or modification.

            e.g.::

                r = await Model.change_db_one_time(newdb).find()

            This query will be performed in newdb.

            **Warnings: not support sqlite**
        """
        cls._current_db = db
        return cls

    def _get_value(self, key):
        """get field value, and not allow default value, use this when update and remove."""
        value = getattr(self, key, None)
        if value is None and key is self.get_primary_key():
            value = getattr(self, '_pk_value', None)
        return value

    def _get_value_or_default(self, key):
        """get field value, allow default value, use this when insert."""
        value = getattr(self, key, None)
        if value is None and key is self.get_primary_key():
            value = getattr(self, '_pk_value', None)
        if value is None:
            field = self.get_mapping()[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    @classonlymethod
    def _clear(cls):
        cls._query_fields = ['`%s`.`%s`' % (cls.__table__, f) for f in cls.get_fields()]
        cls._where.clear()
        cls._where_args.clear()
        cls._exclude.clear()
        cls._exclude_args.clear()
        cls._order_by.clear()
        cls._or_connect = False
        cls._limit = cls._limit_offset = 0
        cls._conn = None
        cls._distinct = False
        cls._current_db = cls._db

    @classmethod
    def _get_compatible_field_name(cls, field):
        """Check if parameter f is in the fields, then return it's name."""

        def _get_compatible_field_name(f):
            """Add ` ` to prevent conflicts with MySQL reserved words"""
            if _Engine.is_sqlite():
                return '`%s`' % f
            return '`%s`.`%s`' % (cls.__table__, f)

        if isinstance(field, str):
            fields = cls.get_fields()
            if field in fields:
                return _get_compatible_field_name(field)
            else:
                raise ValueError("%s has no field '%s' '" % (cls.__name__, field))
        elif isinstance(field, Field):
            if field._belong_model != cls.__name__:
                raise ValueError("field %s not blongs to '%s' '" % (field.name, cls.__name__))
            return _get_compatible_field_name(field.name)
        raise ValueError("query() argument must be str or Field")

    @classmethod
    def _get_compatible_table_name(cls):
        if _Engine.is_sqlite():
            return '`%s`' % cls.__table__
        return '`%s`.`%s`' % (cls._current_db, cls.__table__)

    @classonlymethod
    def query(cls, *args: Optional[Union[str, Field]]) -> None:
        """
        Choice the field you want to query.

        All the query method such as ``find()`` will query all the fields by default,
        so if you want to query all fields, just do not use this method.

        Args:
            args: The field you wang to query.You can use Model.Field or the name of field.

        e.g.::

            r = await User.query(User.id).findall()
            r = await User.query('id').findall()
        Raises:
            ValueError: An error occurred when argument is not a Field.
        """
        query_fields = list(map(cls._get_compatible_field_name, args))
        cls._query_fields = query_fields
        pk = cls.get_primary_key()
        if pk not in args:  # Implicitly look up the primary key to ensure the execution of the save() method
            cls._query_fields.append(cls._get_compatible_field_name(pk) + ' AS _pk_value')
        logger.debug('set query fields %s' % query_fields)
        return cls

    @classonlymethod
    def filter(cls, **kwargs) -> None:
        """
        Filter your query,correspond to where key=value in sql.

        Args:
            Kwargs: The field you wang to filter and it's value.

        Raises:
            ValueError: An error occurred when argument is not a Field.
        """
        fields = cls.get_fields()
        for k, v in kwargs.items():
            if k not in fields:
                raise ValueError("filter() argument must in field")
            cls._where.append(cls._get_compatible_field_name(k) + ' = ?')
            cls._where_args.append(v)
            logger.debug('set filter %s %s' % (cls._get_compatible_field_name(k) + '=', v))
        return cls

    @classonlymethod
    def flex_filter(cls, *conditions: Tuple):
        """
        Filter your query flexibly, such as '>' '<' and so on.

        Args:
            conditions: The field you wang to filter and it's value.
        You can use the following methods::

            flex_filter(Table.Field>100)               --in sql-->  where Table.Field>100
            flex_filter(Table.Field>=100)              --in sql-->  where Table.Field>=100
            flex_filter(Table.Field==100)              --in sql-->  where Table.Field=100
            flex_filter(Table.Field<=100)              --in sql-->  where Table.Field<=100
            flex_filter(Table.Field<100)               --in sql-->  where Table.Field<100
            flex_filter(Table.Field.like('%abc%'))     --in sql-->  where Table.Field LIKE '%abc%'
            flex_filter(Table.Field.start_with(abc))   --in sql-->  where Table.Field LIKE 'abc%'
            flex_filter(Table.Field.end_with(abc))     --in sql-->  where Table.Field LIKE '%abc'
            flex_filter(Table.Field.has('abc'))        --in sql-->  where Table.Field LIKE '%abc%'


        Raises:
            ValueError: An error occurred when you use it in the wrong way.
        """
        for condition in conditions:
            condition_expression, condition_args = condition
            cls._where.append(condition_expression)

            if isinstance(condition_args, list):
                cls._where_args += condition_args
            else:
                cls._where_args.append(condition_args)
            logger.debug('set filter %s %s' % (condition_expression.replace('?', ''), condition_args))
        return cls

    @classonlymethod
    def exclude(cls, **kwargs) -> None:
        """
        Exclude filter your query.

        Args:
            kwargs: the field you wang to exclude and it's value.

        Raises:
            ValueError: An error occurred when argument is not a Field.
        """
        fields = cls.get_fields()
        for k, v in kwargs.items():
            if k not in fields:
                raise ValueError("exclude() argument must in field")
            cls._exclude.append(cls._get_compatible_field_name(k) + ' = ?')
            cls._exclude_args.append(v)
            logger.debug('set exclute %s %s' % (cls._get_compatible_field_name(k) + '=', v))
        return cls

    @classonlymethod
    def flex_exclude(cls, *conditions: Tuple):
        """
        Exclude your query flexibly, such as '>' '<' and so on.

        Args:
            The field you wang to exclude and it's value.
        You can use the following methods:
            same as ``flex_filtter()``

        Raises:
            ValueError: An error occurred when you use it in the wrong way.
                """
        for condition in conditions:
            condition_expression, condition_args = condition
            cls._exclude.append(condition_expression)
            if isinstance(condition_args, list):
                cls._exclude_args += condition_args
            else:
                cls._exclude_args.append(condition_args)
            logger.debug('set exclude %s %s' % (condition_expression.replace('?', ''), condition_args))
        return cls

    @classonlymethod
    def or_connect(cls):
        """Connect your filter br 'OR' rather than 'AND'. """
        cls._or_connect = True
        logger.debug("Using 'OR' to connect filter")
        return cls

    @classonlymethod
    def distinct(cls):
        """Add DISTINCT condition for your query."""
        cls._distinct = True
        logger.debug("Set 'DISTINCT' condition")
        return cls

    @classonlymethod
    def order_by(cls, *args: Optional[str]):
        """
        Sort query results.

        By default, it will be sorted from small to large. You can sort it from large to small by adding '-'.

        Args:
            args: (str) The sorting basis you specified.

        Example::

            User.query('id').order_by('id').find()
            # will sort by id from small to large
            User.query('id').order_by('-id').find()
            # will sort by id from large to small
        """
        fields = cls.get_fields()
        for order_condition in args:
            if order_condition.startswith('-'):
                order_condition = order_condition[1:]
                if order_condition in fields:
                    cls._order_by.append(cls._get_compatible_field_name(order_condition) + ' DESC')
                    logger.debug('Sort from large to small by %s' % order_condition)
                else:
                    raise ValueError("%s has no field '%s' '" % (cls.__name__, order_condition))
            else:
                if order_condition in fields:
                    cls._order_by.append(cls._get_compatible_field_name(order_condition))
                    logger.debug('Sort from small to large by %s' % order_condition)
                else:
                    raise ValueError("%s has no field '%s' '" % (cls.__name__, order_condition))
        return cls

    @classonlymethod
    def limit(cls, num, offset: int = 0):
        cls._limit_offset = offset
        cls._limit = num
        return cls

    @classonlymethod
    def use(cls, conn=None):
        """Specify a connection."""
        cls._conn = conn
        return cls

    @classonlymethod
    def _add_where(cls, sql: StringBuff, args: List) -> NoReturn:
        """
        Add where condition.
        Args:
            sql: the sql buff now use
            args: the args list now use
        """
        if cls._exclude:
            excludes = 'NOT(%s)' % ' OR '.join(cls._exclude)
            cls._where.append(excludes)
        args += cls._where_args
        args += cls._exclude_args
        if cls._where:
            if cls._or_connect:
                sql += ' WHERE %s' % ' OR '.join(cls._where)
            else:
                sql += ' WHERE %s' % ' AND '.join(cls._where)

    @classonlymethod
    def _get_select_statement(cls) -> Tuple[StringBuff, List]:
        """
        Add condition for SELECT query.
        Returns: sql and args.
        """
        sql = StringBuff('SELECT ')
        args = []
        if cls._distinct:
            sql += ' DISTINCT '
        sql += ','.join(cls._query_fields)
        sql += ' FROM %s ' % cls._get_compatible_table_name()
        cls._add_where(sql, args)
        if cls._order_by:
            sql += ' ORDER BY '
            sql += '%s' % ','.join(cls._order_by)
        if cls._limit:
            sql += ' LIMIT ? OFFSET ?'
            args.append(cls._limit)
            args.append(cls._limit_offset)
        return sql, args

    @classonlymethod
    async def find(cls, conn=None):
        """
        Do select.This method will return a list of YourModel objects.

        Args:
            conn: custom connection (this parameter is optional)

        Return:
            (list) A list of YourModel objects.If no record can be found, will return an empty list.
        """
        sql, args = cls._get_select_statement()
        if conn:
            _conn = conn
        else:
            _conn = cls._conn
        cls._clear()
        rs = await select(str(sql), args, conn=_conn)
        return [cls(_new_created=False, **r) for r in rs]

    @classonlymethod
    async def find_first(cls, conn=None):
        """
        Do select.This method will directly return one YourModel object instead of a list.

        Args:
            conn: custom connection (this parameter is optional)

        Returns:
            (Model) One YourModel object.If no record can be found, will return None.
        """
        cls._limit = 1
        cls._limit_offset = 0
        sql, args = cls._get_select_statement()
        if conn:
            _conn = conn
        else:
            _conn = cls._conn
        cls._clear()
        rs = await select(str(sql), args, conn=_conn)
        if rs:
            return cls(_new_created=False, **rs[0])
        else:
            return None

    @classonlymethod
    async def pk_find(cls, pk_value, conn=None):
        """
        Get one object by primary key.

        You should specify the primary key in this method.
        All the restrictions you have made before, except "``query()``", will not take effect.
        This method will directly return one YourModel object.

        Args:
            pk_value : value of primary key.
            conn: custom connection (this parameter is optional)

        Return:
            (Model) One YourModel object.If no record can be found, will return None.
        """

        sql = StringBuff('SELECT ')
        sql += '%s FROM %s' % (','.join(cls._query_fields), cls._get_compatible_table_name())
        sql += " WHERE %s =?" % cls._get_compatible_field_name(cls.get_primary_key())
        args = [pk_value]
        if conn:
            _conn = conn
        else:
            _conn = cls._conn
        cls._clear()
        rs = await select(str(sql), args, conn=_conn)
        if rs:
            return cls(_new_created=False, **rs[0])
        else:
            return None

    @classonlymethod
    async def aggregate(cls, *args, group_by: Optional[Union[str, Field]] = None, conn=None, **kwargs) \
            -> Union[List[Dict], Dict, NoReturn]:
        """
        Aggregate query.

        Args:
            args: aggregate function, it's alias will be taken as ``(function)__(field name)``, e.g. ``MAX__age``.
             you can use the follow aggregate function::
                Max(), Min(), Count(), Avg(), Sum()
            group_by(str): Same as sql, and only allow one field.
            kwargs: key is the alias of this aggregate field,and value is the aggregate function.
            conn: custom connection (this parameter is optional)

        Returns:
            If the group_by parameter is not specified, will return a dict which key is it's alias and value is
            it's result.
            If the group_by parameter is specified, will return a dict which key is the result of the group_by field
            in each group, and value is a dict as same as the first situation.

        Sample:
            you can run this code::

                from model import Max,Count,Min,Avg
                async def run():
                    rs = await Test.filter(grade=3).aggregate(Max('age'), minage=Min('age'), avgage=Avg('age'),
                                                              groupnum=Count(), group_by='birth_place')
                    import pprint
                    pprint.pprint(rs)

                asyncio.get_event_loop().run_until_complete(run())

            you will get the result::

                {'someplace': {'MAX__age': 20, 'avgage': 20.0, 'groupnum': 1, 'minage': 20},
                 'someplace1': {'MAX__age': 23, 'avgage': 20.5, 'groupnum': 2, 'minage': 18},
                 'someplace3': {'MAX__age': 17, 'avgage': 17.0, 'groupnum': 1, 'minage': 17}}

        """
        if group_by:
            group_field = cls._get_compatible_field_name(group_by)
            sql = StringBuff('SELECT %s,' % group_field)
        else:
            sql = StringBuff('SELECT ')

        # Add aggregate fields and aliases
        query_field = []
        for agg_pair in args:
            if agg_pair[1] == '*':
                agg_field = '*'
            else:
                agg_field = cls._get_compatible_field_name(agg_pair[1])
            query_field.append(agg_pair[0] % agg_field + ' AS ' + agg_pair[0].replace('(%s)', '__' + agg_pair[1]))
        for alias, agg_pair in kwargs.items():
            if agg_pair[1] == '*':
                agg_field = '*'
            else:
                agg_field = cls._get_compatible_field_name(agg_pair[1])
            query_field.append(agg_pair[0] % agg_field + ' AS ' + alias)

        sql_args = []
        sql += ','.join(query_field)
        sql += ' FROM ' + cls._get_compatible_table_name()
        cls._add_where(sql, sql_args)
        if group_by:
            sql += ' GROUP BY %s' % group_field
        if conn:
            _conn = conn
        else:
            _conn = cls._conn
        cls._clear()
        rs = await select(str(sql), sql_args, conn=_conn)
        if rs:
            if group_by:
                r_dict = {}
                for r in rs:
                    group_key = r[group_by]
                    r.pop(group_by)
                    r_dict[group_key] = r
                return r_dict
            else:
                return rs[0]
        else:
            return None

    @classonlymethod
    async def select(cls,
                     sql: str,
                     args: Optional[Union[list, tuple]] = (),
                     conn=None) -> list:
        """
        Execute a select query, and turn the result into a model object.
        You can use this method when you encounter a query that ORM cannot complete

        Args:
            sql(str): a sql statement, use ? as placeholder.
            args(list or tuple): argument in placeholder.
            conn: use this parameter to specify a custom connection.

        Return:
             (list) a list of model objects.
        """
        if conn:
            _conn = conn
        else:
            _conn = cls._conn
        cls._clear()
        rs = await select(sql, args, conn=_conn)
        return [cls(**r) for r in rs]

    @classonlymethod
    async def execute(cls,
                      sql: str,
                      args: Optional[Union[list, tuple]] = (),
                      conn=None) -> int:
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
        if conn:
            _conn = conn
        else:
            _conn = cls._conn
        cls._clear()
        return execute(sql, args, _conn)

    @classonlymethod
    async def insert(cls, *insert_objects, conn=None) -> int:
        """
        Insert objects to database.

        This method can insert multiple objects and access the database only once.

        Args:
            insert_objects (Model): One or more object of this Model.They must have the same format.
            conn: custom connection (this parameter is optional)

        Raise:
            ValueError: An error occurred when argument is not the object of this model.
            RuntimeError: An error occurred when arguments do not have the same format.

        Return:
            (int) Affected rows.
        """
        multiple_args = []
        insert_field = []
        _object = insert_objects[0]
        if not isinstance(_object, cls):
            raise ValueError('argument of %s.insert() must be object of %s' % (cls.__name__, cls.__name__))
        # Determine the fields to insert by the first object
        for f in _object.get_fields():
            value = _object._get_value_or_default(f)
            if not isinstance(value, _TableDefault):
                insert_field.append(f)
            multiple_args.append(value)
        object_num = 1

        # Add data for remaining objects
        for _object in insert_objects[1:]:
            if not isinstance(_object, cls):
                raise ValueError('argument of %s.insert() must be object of %s' % (cls.__name__, cls.__name__))
            for f in _object.get_fields():
                if f not in insert_field:
                    raise RuntimeError('arguments must have same format.')
                multiple_args.append(_object._get_value_or_default(f))
            object_num += 1

        insert_field = [cls._get_compatible_field_name(f) for f in cls.get_fields()]
        sql = 'INSERT INTO ' + cls._get_compatible_table_name() + \
              ' (%s) VALUES %s' % (','.join(insert_field),
                                   ','.join(['(' + ','.join(['?'] * len(insert_field)) + ')'] * object_num))
        if conn:
            _conn = conn
        else:
            _conn = cls._conn
        cls._clear()
        rs = await execute(str(sql), multiple_args, conn=_conn)
        return rs

    @classonlymethod
    async def update(cls, conn=None, **kwargs) -> int:
        """
        Update objects to database.

        You can use ``filter()`` and other method to filter the objects that want to update,\
        just as you did in ``find()``.

        Args:
            conn: custom connection (this parameter is optional)

        Return:
            (int) Total number of objects updated.
        """
        change_field = []
        args = []
        for field_name, new_value in kwargs.items():
            change_field.append('%s=?' % cls._get_compatible_field_name(field_name))
            args.append(new_value)
        sql = StringBuff('UPDATE %s SET %s' % (cls._get_compatible_table_name(), ','.join(change_field)))
        if conn:
            _conn = conn
        else:
            _conn = cls._conn
        cls._clear()
        rs = await execute(str(sql), args, conn=_conn)
        return rs

    @classonlymethod
    async def delete(cls, conn=None) -> int:
        """Delete objects from database.

        You can use ``filter()`` and other method to filter the objects that want to delete,\
        just as you did in ``find()``.

        Args:
            conn: custom connection (this parameter is optional)

        Return:
            (int) Total number of objects deleted.
        """
        sql = StringBuff('DELETE FROM %s' % cls._get_compatible_table_name())
        args = []
        cls._add_where(sql, args)
        if conn:
            _conn = conn
        else:
            _conn = cls._conn
        cls._clear()
        rs = await execute(str(sql), args, conn=_conn)
        return rs

    @classonlymethod
    async def create_table(cls):
        """Create this table in current database."""

        # Check whether the table exists
        if _Engine.is_mysql():
            r = await select("""
            SELECT COUNT(*) AS num
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?""", [cls._current_db, cls.__table__])
        elif _Engine.is_sqlite():
            r = await select("""
            SELECT COUNT(*) AS num
            FROM sqlite_master
            WHERE tbl_name = ?""", [cls.__table__])
        to_create = True
        if r[0]['num'] == 1:
            to_create = input(
                """Warning: table %s already exists in database %s!!!\n""" % (cls.__table__, cls._current_db) +
                """do you want to delete it and recreate it?[Y/N]""") in ['y', 'Y']

        if to_create:
            print('to create table %s.' % cls.__table__)
            if _Engine.is_sqlite():
                columns = []
                args = []
                for f_name, f_field in cls._mapping.items():
                    if f_field.primary_key:
                        column_sql = ['`' + f_name + '`', 'INTEGER', 'PRIMARY KEY autoincrement']
                    else:
                        column_sql = ['`' + f_name + '`', f_field.column_type]
                    if not f_field.null:
                        column_sql.append("NOT NULL")
                    # else: don't set a default value in table
                    columns.append(' '.join(column_sql))  # one column sql
                    column_sql.clear()
                await execute("DROP TABLE IF EXISTS %s" % cls._get_compatible_table_name())
                sql = 'CREATE TABLE %s (%s)' % (cls._get_compatible_table_name(), ',\n'.join(columns))
                # sql += '(%s)' % ',\n'.join(columns)
                await execute(str(sql), args)
            else:  # to mysql
                columns = []
                args = []
                for f_name, f_field in cls._mapping.items():
                    column_sql = ['`' + f_name + '`', f_field.column_type]
                    if not f_field.null:
                        column_sql.append("NOT NULL")
                    if isinstance(f_field.default, _TableDefault):
                        column_sql.append(f_field.default.default_value)
                    # else: don't set a default value in table
                    column_sql.append('COMMENT ?')
                    args.append(f_field.comment)
                    columns.append(' '.join(column_sql))  # one column sql
                    column_sql.clear()
                sql = StringBuff('CREATE DATABASE IF NOT EXISTS `%s`;\n' % cls._current_db)
                sql += 'DROP TABLE IF EXISTS %s;\n' % cls._get_compatible_table_name()
                sql += 'CREATE TABLE %s\n' % cls._get_compatible_table_name()
                sql += '(%s,\nPRIMARY KEY (`%s`));\n' % (',\n'.join(columns), cls.get_primary_key())
                await execute(str(sql), args)
            logger.info('create table %s' % cls.__table__)
            cls._clear()
        else:
            print('not create.')

    async def save(self, conn=None) -> NoReturn:
        """
        Save this object to database.

        Args:
            conn: custom connection (this parameter is optional)

        Raise:
            RuntimeError: An error occurred when failed to save this object.
            AttributeError: An error occurred when primary key has been changed, which
            is not allowed in this method, use ``update()``.

        Return:
            None
        """
        if self._new_created:  # a new object to insert
            insert_field = []
            args = []
            # get insert filed and it's value
            for f in self.get_fields():
                value = self._get_value_or_default(f)
                if not isinstance(value, _TableDefault):
                    insert_field.append(self._get_compatible_field_name(f))
                    args.append(value)
            sql = 'INSERT INTO  %s (%s) VALUES (%s)' % (self._get_compatible_table_name(),
                                                        ','.join(insert_field), ','.join(['?'] * len(insert_field)))
        else:  # a changed object to update
            update_field = []
            args = []
            # get primary key
            pk = self.get_primary_key()
            pk_value = getattr(self, pk, None)
            if pk_value is not None and pk_value != self._pk_value:
                raise AttributeError('save failed: primary key has already changed.')
            # get remain field and it's value
            for f in self._fields_without_pk:
                value = self._get_value(f)
                if value is not None:
                    update_field.append(f)
                    args.append(value)
            sql = 'UPDATE %s SET %s WHERE %s=?' %(self._get_compatible_table_name(),
                                                  ','.join(['%s=?' % self._get_compatible_field_name(_)\
                                                            for _ in update_field]),
                                                  self._get_compatible_field_name(pk))
            args.append(self._pk_value)
        if conn:
            _conn = conn
        else:
            _conn = self._conn
        self._conn = None
        rs = await execute(str(sql), args, conn=_conn)
        if rs != 1:
            raise RuntimeError('Failed to save object %s' % self)

    async def remove(self, conn=None) -> NoReturn:
        """
        Remove this object from database.

        Args:
            conn: custom connection (this parameter is optional)

        Raise:
            RuntimeError: An error occurred when can not find a primary key of this object.
            since every object queried from the database will query primary key explicitly
            or implicitly, this error will only appear when the newly created object calls
            the ``remove()`` method, which itself is the wrong use. To delete an object without
            querying in advance, use ``delete()`` method.

        Return:
            None
        """
        if self._new_created:
            logger.warning('do not use remove() method in newly created object, consider delete()')
        pk = self.get_primary_key()
        pk_value = self._get_value(pk)
        if not pk_value:
            raise RuntimeError('Can not find a primary key, this may be due to a wrong call of this method.')
        sql = 'DELETE FROM %s WHERE %s=? ' % (self._get_compatible_table_name(), self._get_compatible_field_name(pk))
        args = [pk_value]
        if conn:
            _conn = conn
        else:
            _conn = self._conn
        self._conn = None
        rs = await execute(str(sql), args, conn=_conn)
        if rs == 0:
            logger.warning('object %s is not in the database' % self)


def Max(field: Field = None):
    if field is None:
        return 'MAX(%s)', '*'
    elif isinstance(field, str):
        return 'MAX(%s)', field
    elif isinstance(field, Field):
        return 'MAX(%S)', field._field_name


def Min(field: Field = None):
    if field is None:
        return 'MIN(%s)', '*'
    elif isinstance(field, str):
        return 'MIN(%s)', field
    elif isinstance(field, Field):
        return 'MIN(%S)', field._field_name


def Avg(field: Field = None):
    if field is None:
        return 'AVG(%s)', '*'
    elif isinstance(field, str):
        return 'AVG(%s)', field
    elif isinstance(field, Field):
        return 'AVG(%S)', field._field_name


def Sum(field: Field = None):
    if field is None:
        return 'SUM(%s)', '*'
    elif isinstance(field, str):
        return 'SUM(%s)', field
    elif isinstance(field, Field):
        return 'SUM(%S)', field._field_name


def Count(field=None):
    if field is None:
        return 'COUNT(%s)', '*'
    elif isinstance(field, str):
        return 'COUNT(%s)', field
    elif isinstance(field, Field):
        return 'COUNT(%S)', field._field_name
