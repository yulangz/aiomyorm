from aiomyorm import Model, IntField, StringField, SmallIntField, auto_increment
from aiomyorm import set_config, close_db_connection
import asyncio

set_config(engine='sqlite',
           db='test.db')


class Test(Model):
    __table__ = 'test'
    pk = IntField(primary_key=True, default=auto_increment())
    id = StringField(50)
    age = IntField(comment='the age of student.')
    birth_place = StringField(50, default='china')
    grade = SmallIntField()


async def go():
    insert_rows = await Test.insert(Test(pk=5000, age=18, birth_place='place1'),
                                    Test(pk=5001, age=21, birth_place='place2'),
                                    Test(pk=5002, age=19, birth_place='place3'))
    all = await Test.find()
    print('insert rows: ', insert_rows)
    for r in all:
        print(r)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(Test.create_table())
    loop.run_until_complete(go())
    loop.run_until_complete(close_db_connection())
