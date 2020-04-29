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


async def go_transaction():
    rs_old = await Test.find()
    rs_trans = None
    try:
        async with Transaction() as conn:
            r = await execute('insert into test (id,age,birth_place,grade) values ("00020",18,"北京",1)', conn=conn)
            rs_trans = await Test.use(conn).find()
            100 / 0  # make error
    except ZeroDivisionError:
        pass
    assert r == 1
    rs_new = await Test.find()

    import pprint
    print('old:')
    pprint.pprint(rs_old)
    print('in transaction:')
    pprint.pprint(rs_trans)
    print('new:')
    pprint.pprint(rs_new)

    assert rs_old == rs_new
    assert rs_old != rs_trans


loop = asyncio.get_event_loop()
loop.run_until_complete(go_transaction())
loop.run_until_complete(close_db_connection())
