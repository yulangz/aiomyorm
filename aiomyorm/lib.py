class StringBuff(object):
    def __init__(self, init_string: str = ''):
        self._string_buff = [init_string]

    def __add__(self, other: str):
        self._string_buff.append(other)
        return self

    def __str__(self):
        return ''.join(self._string_buff)

    __repr__ = __str__

    def to_string(self, connector: str = ''):
        return connector.join(self._string_buff)


class classonlymethod(classmethod):
    """
    Convert a function to be a class only method.

    This has the same usage as classmethod, except that it can only be used in class.
    """

    def __get__(self, instance, owner):
        if instance is not None:
            raise AttributeError("Method %s() is only allowed in class." % self.__func__.__name__)
        return super().__get__(instance, owner)
