field
**********************


Basic Field
=========================================
This is the most basic ``Field`` class, and all the common properties of all ``Field`` are given here,
but I do not recommend you to use this class. I provide a more customized class later.

..  autoclass:: aiomyorm.field.Field



Integer Field
=======================================

..  automodule:: aiomyorm.field
    :members: BoolField, SmallIntField, MediumIntField, IntField, BigIntField
    :show-inheritance:

String Field
======================

..  automodule:: aiomyorm.field
    :members: StringField, FixedStringField
    :show-inheritance:

Text Field
======================

..  automodule:: aiomyorm.field
    :members: TextField, MediumTextField, LongTextField
    :show-inheritance:

Decimal Field
================

..  automodule:: aiomyorm.field
    :members: FloatField, DoubleField, DecimalField
    :show-inheritance:

DateTime Field
=================

..  automodule:: aiomyorm.field
    :members: DatetimeField, DateField, TimeField, TimestampField
    :show-inheritance:

More Field
===============

You can customize your field class based on the ``Field``, such as::

    class JsonField(Field):
        """A json field."""
        def __init__(self, primary_key=False, default="{}", null=False, comment=''):
            super().__init__(column_type='json', primary_key=primary_key, default=default, null=null,
                             comment=comment)
