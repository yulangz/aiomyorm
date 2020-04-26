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


async def go_find():
    r = await Test.find()
    import pprint
    pprint.pprint(r)


async def go_filter():
    r = await Test.query('pk', 'age').filter(age=19).find()
    import pprint
    pprint.pprint(r)


async def go_flex_filter():
    r = await Test.query('pk', 'age').flex_filter(Test.age > 19).find()
    import pprint
    pprint.pprint(r)


async def go_aggregate():
    r = await Test.aggregate(Count('age'), maxage=Max('age'))
    import pprint
    pprint.pprint(r)


async def go_group():
    r = await Test.aggregate(Count('age'), maxage=Max('age'), group_by='age')
    import pprint
    pprint.pprint(r)


async def go_pk_find():
    r = await Test.pk_find(5000)
    print(r)
    print(isinstance(r, Test))


async def go_find_first():
    r = await Test.flex_filter(Test.pk>5000).find_first()
    print(r)
    print(isinstance(r, Test))

loop = asyncio.get_event_loop()
loop.run_until_complete(go_find_first())
loop.run_until_complete(close_db_connection())
