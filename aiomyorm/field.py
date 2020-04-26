# TODO: support json
import datetime


class Field(object):
    """
    A field is a mapping of a column in mysql table.

    Attributes:
        column_type(str) : Type of this column.
        primary_key(bool) : Whether is a primary key.
        default(any) : The default value of this column, it can be a real value or a function.
        belong_model(str) : The model(table) this field(column) belongs to.
        comment(str) : Comment of this field.
        null(bool) : Allow null value or not.
        unsigned(bool) : Whether unsigned. Only useful in Integer.
    """

    def __init__(self, column_type, default, primary_key=False, null=False, comment=None, unsigned=None):
        """
        Args:
            column_type(str) : Type of this column.
            primary_key(bool) : Whether is a primary key.
            default(any) : The default value of this column, it can be a real value or a function.
            comment(str) : Comment of this field.
            null(bool) : Allow null value or not. False by default.
            unsigned(bool) : Whether unsigned. Only useful in Integer.
        """
        self._column_type = column_type
        self._primary_key = primary_key
        self._default = default
        self._belong_model = None
        self._field_name = None
        self._null = null
        self._comment = comment
        self._unsigned = unsigned

    @property
    def unsigned(self):
        return self._unsigned

    @property
    def comment(self):
        return self._comment

    @property
    def column_type(self):
        return self._column_type

    @property
    def primary_key(self):
        return self._primary_key

    @property
    def default(self):
        return self._default

    @property
    def belong_model(self):
        return self._belong_model

    @property
    def null(self):
        return self._null

    def __str__(self):
        return '<%s %s>' % (self.__class__.__name__, self.column_type)

    __repr__ = __str__

    def __gt__(self, other):
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` > ?', other

    def __ge__(self, other):
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` >= ?', other

    def __eq__(self, other):
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` = ?', other

    def __le__(self, other):
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` <= ?', other

    def __lt__(self, other):
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` < ?', other

    def __ne__(self, other):
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` != ?', other

    def between(self, val1, val2):
        """Limit the value of this field between val1 and val2, Both sides of the border will be taken."""
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` BETWEEN ? AND ?', [val1, val2]

    def like(self, val):
        """Fuzzy query of a string field, the format is the same as MySQL"""
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` LIKE ?', val

    def start_with(self, val):
        """Constrain a string field start whit the val."""
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` LIKE ?', str(val) + '% '

    def end_with(self, val):
        """Constrain a string field end whit the val."""
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` LIKE ?', ' %' + str(val)

    def has(self, val):
        """Constrain Val in a string field."""
        return '`' + self.belong_model.__table__ + '`.`' + self._field_name + '` LIKE ?', ' %' + str(val) + '% '

    def _is_table_default(self):
        return isinstance(self.default, _TableDefault)


# ################### Integer ####################
_integer_field = ['tinyint', 'smallint', 'mediumint', 'int', 'bigint']


class BoolField(Field):
    """A bool field."""

    def __init__(self, primary_key=False, default=False, null=False, comment=''):
        super().__init__(column_type='tinyint', primary_key=primary_key, default=default,
                         null=null, comment=comment)


class SmallIntField(Field):
    """A smallint field."""

    def __init__(self, primary_key=False, default=0, null=False, comment='', unsigned=False):
        column_type = 'smallint' + (' UNSIGNED' if unsigned else '')
        super().__init__(column_type=column_type, primary_key=primary_key, default=default,
                         null=null, comment=comment, unsigned=unsigned)


class MediumIntField(Field):
    """A mediumint field."""

    def __init__(self, primary_key=False, default=0, null=False, comment='', unsigned=False):
        column_type = 'mediumint' + (' UNSIGNED' if unsigned else '')
        super().__init__(column_type=column_type, primary_key=primary_key, default=default, null=null,
                         comment=comment, unsigned=unsigned)


class IntField(Field):
    """A int field."""

    def __init__(self, primary_key=False, default=0, null=False, comment='', unsigned=False):
        column_type = 'int' + (' UNSIGNED' if unsigned else '')
        super().__init__(column_type=column_type, primary_key=primary_key, default=default, null=null,
                         comment=comment, unsigned=unsigned)


class BigIntField(Field):
    """A bigint field."""

    def __init__(self, primary_key=False, default=0, null=False, comment='', unsigned=False):
        column_type = 'bigint' + (' UNSIGNED' if unsigned else '')
        super().__init__(column_type=column_type, primary_key=primary_key, default=default, null=null,
                         comment=comment, unsigned=unsigned)


# ################################################################

# ####################### String #################################
_varchar_field = ['varchar', 'char']


class StringField(Field):
    """
    A string field.

    Args:
        length(int) : Maximum length of string in this field, default by 255.
    """

    def __init__(self, length: int = 255, primary_key=False, default='', null=False, comment=''):
        super().__init__(column_type='varchar(' + str(length) + ')', primary_key=primary_key,
                         default=default, null=null, comment=comment)


class FixedStringField(Field):
    """A fixed length string field."""

    def __init__(self, length: int = 255, primary_key=False, default='', null=False, comment=''):
        """Args:
                length(int) : Maximum length of string in this field, default by 255.
        """
        super().__init__(column_type='char(' + str(length) + ')', primary_key=primary_key,
                         default=default, null=null, comment=comment)


_text_field = ['text', 'mediumtext', 'longtext']


class TextField(Field):
    """A text field."""

    def __init__(self, primary_key=False, default='', null=False, comment=''):
        super().__init__(column_type='text', primary_key=primary_key, default=default, null=null, comment=comment)


class MediumTextField(Field):
    """A medium text field."""

    def __init__(self, primary_key=False, default='', null=False, comment=''):
        super().__init__(column_type='mediumtext', primary_key=primary_key, default=default, null=null, comment=comment)


class LongTextField(Field):
    """A long text field."""

    def __init__(self, primary_key=False, default='', null=False, comment=''):
        super().__init__(column_type='longtext', primary_key=primary_key, default=default, null=null, comment=comment)


# ######################################################################

# ####################### decimal ########################################
_decimal_field = ['float', 'double', 'decimal']


class FloatField(Field):  # 255,30
    """
    A float field.

    Args:
        total_digits(int) : total digit for this float, default by 255.
        decimal_digits(int) : total decimal digit, default by 30.
    """

    def __init__(self, total_digits: int = 255, decimal_digits: int = 30,
                 primary_key=False, default=0.0, null=False, comment=''):
        super().__init__(column_type='float(%s,%s)' % (total_digits, decimal_digits),
                         primary_key=primary_key, default=default, null=null, comment=comment)


class DoubleField(Field):  # 255,30
    """
    A double field.

    Args:
        total_digits(int) : total digit for this float, default by 255.
        decimal_digits(int) : total decimal digit, default by 30.
    """

    def __init__(self, total_digits: int = 255, decimal_digits: int = 30,
                 primary_key=False, default=0.0, null=False, comment=''):
        super().__init__(column_type='double(%s,%s)' % (total_digits, decimal_digits),
                         primary_key=primary_key, default=default, null=null, comment=comment)


class DecimalField(Field):  # 255,30
    """
    A decimal field which is more precise than float or double.

    Args:
        total_digits(int) : total digit for this float, default by 65.
        decimal_digits(int) : total decimal digit, default by 30.
    """

    def __init__(self, total_digits: int = 65, decimal_digits: int = 30,
                 primary_key=False, default=0.0, null=False, comment=''):
        super().__init__(column_type='decimal(%s,%s)' % (total_digits, decimal_digits),
                         primary_key=primary_key, default=default, null=null, comment=comment)


# ##################################################################################################

# ################################ datetime ########################################################
_datetime_field = ['datetime', 'date', 'time', 'timestamp']


class DatetimeField(Field):
    """A datetime field, default value is now."""

    def __init__(self, primary_key=False, default=datetime.datetime.now().replace(microsecond=0),
                 null=False, comment=''):
        super().__init__(column_type='datetime', primary_key=primary_key, default=default, null=null, comment=comment)


class DateField(Field):
    """A datetime field, default value is today."""

    def __init__(self, primary_key=False, default=datetime.date.today(), null=False, comment=''):
        super().__init__(column_type='date', primary_key=primary_key, default=default, null=null, comment=comment)


def _now_time():
    t = datetime.datetime.now()
    return datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)


class TimeField(Field):
    """A time field, default value is now time."""

    def __init__(self, primary_key=False, default=_now_time(), null=False, comment=''):
        super().__init__(column_type='time', primary_key=primary_key, default=default, null=null, comment=comment)


class TimestampField(Field):
    """A timestamp field, default value is now."""

    def __init__(self, primary_key=False, default=datetime.datetime.now().replace(microsecond=0),
                 null=False, comment=''):
        super().__init__(column_type='timestamp', primary_key=primary_key, default=default, null=null, comment=comment)


# ##################################################################################################
_field_map = {
    'tinyint': BoolField,
    'smallint': SmallIntField,
    'mediumint': MediumIntField,
    'int': IntField,
    'bigint': BigIntField,
    'varchar': StringField,
    'char': FixedStringField,
    'text': TextField,
    'mediumtext': MediumTextField,
    'longtext': LongTextField,
    'float': FloatField,
    'double': DoubleField,
    'decimal': DecimalField,
    'datetime': DatetimeField,
    'date': DateField,
    'time': TimeField,
    'timestamp': TimestampField
}


class _TableDefault(object):
    """Indicates that the field uses the default values in the table."""

    def __init__(self, default_value):
        self.default_value = default_value

    def __str__(self):
        return '<Table Default: %s>' % self.default_value

    __repr__ = __str__


def table_default(val: str = None):
    """
    Let default as same as table.

    Args:
        val(str): default value in table.
        e.g. : 'ON UPDATE CURRENT_TIMESTAMP(0)'
    """
    return _TableDefault(val)


def auto_increment():
    """
    Set default value to auto increment.

    If you use this as default value, you should make sure this field in your
    database has a auto increment constrain.
    If you use aiomyorm to create table, auto increment constrain will be set
    to database.
    """
    return _TableDefault('auto_increment')
