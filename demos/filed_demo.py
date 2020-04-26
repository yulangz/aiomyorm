from aiomyorm import *


class JsonField(Field):
    """A json field."""
    def __init__(self, primary_key=False, default="{}", null=False, comment=''):
        super().__init__(column_type='json', primary_key=primary_key, default=default, null=null,
                         comment=comment)