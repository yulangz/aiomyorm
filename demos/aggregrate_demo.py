from aiomyorm.model import Model, Max, Min, Count, Sum, Avg
import asyncio
from aiomyorm.field import IntField, auto_increment, StringField, SmallIntField
from aiomyorm.set_config import set_config
from aiomyorm.connection import close_db_connection, execute

set_config(engine='sqlite',
           db='test.db')


class Test(Model):
    __table__ = 'test'
    pk = IntField(primary_key=True, default=auto_increment())
    id = StringField(50)
    age = IntField()
    birth_place = StringField(50, default='china')
    grade = SmallIntField()


async def run():
    rs = await Test.filter(grade=3).aggregate(Max('age'), minage=Min('age'), avgage=Avg('age'),
                                              groupnum=Count(), group_by='birth_place')
    import pprint
    pprint.pprint(rs)


loop = asyncio.get_event_loop()
loop.run_until_complete(run())
loop.run_until_complete(close_db_connection())
