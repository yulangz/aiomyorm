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


async def go_save():
    await Test(pk=9999, age=20).save()


async def go_insert():
    r = await Test.insert(Test(pk=5000, age=19, birth_place='place1'),
                          Test(pk=5001, age=21, birth_place='place2'),
                          Test(pk=5002, age=19, birth_place='place3'))
    assert r == 3


loop = asyncio.get_event_loop()
loop.run_until_complete(go_save())
loop.run_until_complete(close_db_connection())
