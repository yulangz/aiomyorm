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


async def go_remove():
    t = await Test.pk_find(5000)
    await t.remove()


async def go_delete():
    r = await Test.flex_filter(Test.age >= 20).delete()
    print(r)


async def go_save_update():
    await Test(pk=3333, id='old_data', age=20).save()
    r = await Test.pk_find(3333)
    print('old data: ', r)
    r.id = 'new data'
    r.age = 10
    await r.save()
    r_new = await Test.pk_find(3333)
    print('new data: ', r_new)


async def go_update():
    r = await Test.find()
    import pprint
    print('old values:')
    pprint.pprint(r)
    rows = await Test.filter(grade=0).update(age=18)
    r = await Test.find()
    print('update affect %d rows, new value is:' % rows)
    pprint.pprint(r)


loop = asyncio.get_event_loop()
loop.run_until_complete(go_update())
loop.run_until_complete(close_db_connection())
