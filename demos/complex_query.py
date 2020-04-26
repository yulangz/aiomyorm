from aiomyorm import *
import asyncio

set_config(engine='sqlite',
           db='test.db')


class Test(Model):
    __table__ = 'test'
    pk = IntField(primary_key=True, default=auto_increment())
    id = StringField(50)
    age = IntField()
    birth_place = StringField(50, default='china')
    grade = SmallIntField()


async def go_select_1():
    rs = await Test.select('SELECT * FROM test WHERE age>(SELECT age FROM test WHERE pk=5002)')
    for r in rs:
        assert isinstance(r, Test)
    import pprint
    pprint.pprint(rs)


from aiomyorm import select


async def go_select_2():
    rs = await select('SELECT * FROM test WHERE age>(SELECT age FROM test WHERE pk=5002)')
    print(type(rs[0]))
    import pprint
    pprint.pprint(rs)


async def go_execute():
    rs = await execute('UPDATE test set id="little boy" WHERE age>(SELECT age FROM test WHERE pk=5002)')
    print(rs)


loop = asyncio.get_event_loop()
loop.run_until_complete(go_execute())
loop.run_until_complete(close_db_connection())
