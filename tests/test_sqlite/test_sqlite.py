import aiounittest
import unittest
import logging
import asyncio
import os
from sqlite3 import OperationalError
from aiomyorm.model import Model, Max, Count, Min, Avg, Sum
from aiomyorm.field import (
    SmallIntField,
    MediumIntField,
    IntField,
    BigIntField,
    BoolField,

    StringField,
    FixedStringField,
    TextField,
    MediumTextField,
    LongTextField,

    FloatField,
    DoubleField,
    DecimalField,

    DateField,
    DatetimeField,
    TimeField,
    TimestampField,
    auto_increment,
    table_default
)
from aiomyorm.connection import Connection, Transaction
from aiomyorm.connection import select, execute, close_db_connection
from aiomyorm.log import logger
from aiomyorm.set_config import set_config

set_config(engine='sqlite',
           db='test.db')


class Set_All_Field(Model):
    __table__ = 'all_field'
    small = SmallIntField(primary_key=True, default=auto_increment())
    med = MediumIntField()
    mint = IntField()
    bgint = BigIntField()
    mbool = BoolField()

    mstr = StringField()
    fixstr = FixedStringField()
    text = TextField()
    medtext = MediumTextField()
    longtext = LongTextField()

    mfloat = FloatField()
    mdouble = DoubleField()
    mdecimal = DecimalField()

    date = DateField()
    dt = DatetimeField()
    time = TimeField()
    tmstamp = TimestampField(default=table_default('ON UPDATE CURRENT_TIMESTAMP'))


class Test(Model):
    __table__ = 'test'
    pk = IntField(primary_key=True, default=auto_increment())
    id = StringField(50)
    age = IntField()
    birth_place = StringField(50, default='china')
    grade = SmallIntField()


class SyntaxTest(unittest.TestCase):
    def test_classonlymethod(self):
        with self.assertRaises(AttributeError):
            t = Test()
            t.filter()


class ReadTest(aiounittest.AsyncTestCase):

    @classmethod
    def get_event_loop(cls):
        cls.my_loop = asyncio.get_event_loop()
        return cls.my_loop

    @classmethod
    def setUpClass(cls) -> None:
        async def set_up_run():
            await execute("delete from `test`")
            await execute("""INSERT INTO `test` ( `pk`, `id`, `age`, `birth_place`, `grade` )
                                        VALUES
                                            ( 1,'00000', 18, 'someplace1', 3 ),
                                            ( 2,'00001', 23, 'someplace1', 3 ),
                                            ( 3,'00002', 19, 'someplace', 4 ),
                                            ( 4,'00003', 20, 'someplace', 3 ),
                                            ( 5,'00004', 21, 'someplace3', 4 ),
                                            ( 6,'00005', 17, 'someplace3', 3 ),
                                            ( 7,'00006', 22, 'someplace', 5 ),
                                            ( 8,'00007', 20, 'someplace3', 2 ),
                                            ( 9,'00008', 21, 'someplace3', 1 ),
                                            ( 10,'00009', 17, 'someplace3', 2 ),
                                            ( 0,'00010', 22, 'someplace', 1 )""")

        loop = cls.my_loop
        loop.run_until_complete(set_up_run())

    @classmethod
    def tearDownClass(cls) -> None:
        async def tear_down__run():
            await execute("delete from `test`")

        cls.my_loop.run_until_complete(tear_down__run())

    async def test_find_all(self):
        rs1 = await Test.find()
        rs2 = await select('select * from test')
        self.assertListEqual(rs1, rs2)

    async def test_filter(self):
        rs1 = await Test.filter(age=18).find()
        rs2 = await select('select * from test where age=18')
        self.assertListEqual(rs1, rs2)

    async def test_query(self):
        rs1 = await select('select age,grade from test')
        rs2 = await Test.query('age', 'grade').find()
        self.assertListEqual(rs1, rs2)

    async def test_flex_filter(self):
        rs = await select('select * from test where age>19')
        rso = await Test.flex_filter(Test.age > 19).find()
        self.assertListEqual(rs, rso)

    async def test_exclude(self):
        rs = await select('select * from test where not(age=18)')
        rso = await Test.exclude(age=18).find()
        self.assertListEqual(rs, rso)

    async def test_flex_exclude(self):
        rs = await select('select * from test where not(age>19)')
        rso = await Test.flex_exclude(Test.age > 19).find()
        self.assertListEqual(rs, rso)

    async def test_exclude_mult(self):
        rs = await select('select * from test where not(age>19 or grade<2)')
        rso = await Test.flex_exclude(Test.age > 19, Test.grade < 2).find()
        self.assertListEqual(rs, rso)

    async def test_filter_mult(self):
        rs = await select('select * from test where age>19 and grade>2')
        rso = await Test.flex_filter(Test.age > 19, Test.grade > 2).find()
        self.assertListEqual(rs, rso)

    async def test_filter_exclude(self):
        rs = await select('select * from test where grade<3 and not(age>19)')
        rso = await Test.flex_exclude(Test.age > 19).flex_filter(Test.grade < 3).find()
        self.assertListEqual(rs, rso)

    async def test_or_connect(self):
        rs = await select('select * from test where age>19 or grade>2')
        rso = await Test.flex_filter(Test.age > 19, Test.grade > 2).or_connect().find()
        self.assertListEqual(rs, rso)

    async def test_distinct(self):
        rs = await select('select distinct age from test where grade>2')
        rso = await Test.distinct().query('age').flex_filter(Test.grade > 2).find()
        self.assertListEqual(rs, rso)

    async def test_order_by(self):
        rs = await select('select * from test where grade>2 order by grade,age')
        rso = await Test.flex_filter(Test.grade > 2).order_by('grade', 'age').find()
        self.assertListEqual(rs, rso)

    async def test_limit(self):
        rs = await select('select * from test where grade>2 order by grade,age limit 3 offset 2')
        rso = await Test.flex_filter(Test.grade > 2).order_by('grade', 'age').limit(3, offset=2).find()
        self.assertListEqual(list(rs), rso)

    async def test_find_first(self):
        rs = await select('select id,age from test where grade>2 order by grade,age limit 1')
        rso = await Test.query('id', 'age').flex_filter(Test.grade > 2).order_by('grade', 'age').find_first()
        self.assertDictEqual(rs[0], rso)

    async def test_pk_find(self):
        rs = await select('select * from test where pk=0')
        rso = await Test.pk_find(0)
        self.assertDictEqual(rs[0], rso)

    async def test_aggregate(self):
        rs = await select('select count(age),max(age) from test')
        rso = await Test.aggregate(Count('age'), maxage=Max('age'))
        self.assertEqual(rs[0]['count(age)'], rso['COUNT__age'])
        self.assertEqual(rs[0]['max(age)'], rso['maxage'])

    async def test_aggregate2(self):
        rs = await select('select min(age) as minage,avg(age) as avgage,sum(age) as sumage from test')
        rso = await Test.aggregate(minage=Min('age'), avgage=Avg('age'), sumage=Sum('age'))
        self.assertDictEqual(rs[0], rso)

    async def test_group_by(self):
        rs = await select('select grade,count(age),max(age) from test group by grade')
        rso = await Test.aggregate(Count('age'), maxage=Max('age'), group_by='grade')
        for r in rs:
            group_key = r['grade']
            r.pop('grade')
            ormres = rso[group_key]
            self.assertEqual(r['count(age)'], ormres['COUNT__age'])
            self.assertEqual(r['max(age)'], ormres['maxage'])

    async def test_conn(self):
        rsselect = await select('select * from test')
        async with Connection() as conn:
            rs_orm = await Test.use(conn).find()
            cur = await conn.cursor()
            await cur.execute('select * from test')
            rs = await cur.fetchall()
            await cur.close()
        self.assertListEqual(rs, rs_orm)
        self.assertListEqual(rs, rsselect)

    async def test_transaction(self):
        rs_old = await select('select * from test')
        try:
            async with Transaction() as conn:
                r = await execute('insert into test (id,age,birth_place,grade) values ("00020",18,"ppp",1)', conn=conn)
                100 / 0  # make error
        except Exception:
            pass
        self.assertEqual(r, 1)
        rs_new = await select('select * from test')
        self.assertListEqual(rs_old, rs_new)

    async def test_class_execute(self):
        r1 = await Test.select('select * from test')
        r2 = await Test.find()
        self.assertListEqual(r1, r2)


class WriteTest(aiounittest.AsyncTestCase):

    @classmethod
    def get_event_loop(cls):
        cls.my_loop = asyncio.get_event_loop()
        return cls.my_loop

    @classmethod
    def setUpClass(cls) -> None:
        async def set_up_run():
            await execute("delete from `test`")
            await execute("""INSERT INTO `test` ( `pk`, `id`, `age`, `birth_place`, `grade` )
                                        VALUES
                                            ( 1,'00000', 18, 'someplace1', 3 ),
                                            ( 2,'00001', 23, 'someplace1', 3 ),
                                            ( 3,'00002', 19, 'someplace', 4 ),
                                            ( 4,'00003', 20, 'someplace', 3 ),
                                            ( 5,'00004', 21, 'someplace3', 4 ),
                                            ( 6,'00005', 17, 'someplace3', 3 ),
                                            ( 7,'00006', 22, 'someplace', 5 ),
                                            ( 8,'00007', 20, 'someplace3', 2 ),
                                            ( 9,'00008', 21, 'someplace3', 1 ),
                                            ( 10,'00009', 17, 'someplace3', 2 ),
                                            ( 0,'00010', 22, 'someplace', 1 )""")

        loop = cls.my_loop
        loop.run_until_complete(set_up_run())

    @classmethod
    def tearDownClass(cls) -> None:
        async def tear_down__run():
            await execute("delete from `test`")

        cls.my_loop.run_until_complete(tear_down__run())

    async def test_save_new_object(self):
        await execute("delete from test where pk=9999")
        await Test(pk=9999, age=20).save()
        rs = await Test.pk_find(9999)
        self.assertEqual(rs.age, 20)
        await execute("delete from test where pk=9999")

    async def test_save_changed_object_raise(self):
        await execute("delete from test where pk=9999")
        await Test(pk=9999, age=20).save()
        with self.assertRaises(AttributeError):
            obj = await Test.pk_find(9999)
            obj.pk = 100
            await obj.save()
        await execute("delete from test where pk=9999")

    async def test_save_changed_object(self):
        await execute("delete from test where pk=9999")
        await execute(
            "INSERT INTO `test` (`pk`, `id`, `age`, `birth_place`, `grade`) VALUES (9999, '123', 20, 'no', 1)")
        obj = await Test.pk_find(9999)
        self.assertEqual(obj.age, 20)
        obj.age = 18
        await obj.save()
        r = await select("select * from test where pk=9999")
        self.assertEqual(r[0]['age'], 18)
        await execute("delete from test where pk=9999")

    async def test_save_changed_object_with_value_0(self):
        await execute("delete from test where pk=9999")
        await execute(
            "INSERT INTO `test` (`pk`, `id`, `age`, `birth_place`, `grade`) VALUES (9999, '123', 20, 'no', 1)")
        obj = await Test.pk_find(9999)
        self.assertEqual(obj.age, 20)
        obj.age = 0
        await obj.save()
        r = await select("select * from test where pk=9999")
        self.assertEqual(r[0]['age'], 0)
        await execute("delete from test where pk=9999")

    async def test_auto_increment(self):
        await execute("delete from test where id='6666'")
        async with Transaction() as conn:
            await Test(id='6666').use(conn).save()
            await Test(id='6666').use(conn).save()
        r = await Test.filter(id='6666').find()
        self.assertEqual(len(r), 2)
        self.assertEqual(abs(r[0].pk - r[1].pk), 1)
        await execute("delete from test where id='6666'")

    async def test_conn(self):
        with self.assertRaises(OperationalError):
            async with Transaction() as conn:
                t = Test(id='9999', age=18)
                await t.use(conn).save()
                rselect = await Test.use(conn).find()
                get = False
                for r in rselect:
                    if r.id == '9999':
                        get = True
                        break
                await execute('insert into test (iiiiid) values (654321)', conn=conn)  # make error
        self.assertEqual(get, True)
        roriginal = await Test.find()
        originalget = False
        for r in roriginal:
            if r.id == '9999':
                originalget = True
                break
        self.assertEqual(originalget, False)

    async def test_default_value(self):
        await execute("delete from test where pk=9999")
        await Test(pk=9999, age=20).save()
        rs = await Test.pk_find(9999)
        await execute("delete from test where pk=9999")
        self.assertEqual(rs.birth_place, 'china')

    async def test_insert(self):
        await execute("DELETE FROM test WHERE pk=5000 or pk=5001 or pk=5002")
        rs = await Test.insert(Test(pk=5000, age=18, birth_place='place1'),
                               Test(pk=5001, age=21, birth_place='place2'),
                               Test(pk=5002, age=19, birth_place='place3'))
        self.assertEqual(rs, 3)
        result = await Test.find()
        result_has = set()
        for r in result:
            pk = r.pk
            if pk == 5000:
                self.assertEqual(r.age, 18)
                self.assertEqual(r.birth_place, 'place1')
                result_has.add(pk)
            elif pk == 5001:
                self.assertEqual(r.age, 21)
                self.assertEqual(r.birth_place, 'place2')
                result_has.add(pk)
            elif pk == 5002:
                self.assertEqual(r.age, 19)
                self.assertEqual(r.birth_place, 'place3')
                result_has.add(pk)
        self.assertSetEqual(result_has, {5000, 5001, 5002})
        await execute("DELETE FROM test WHERE pk=5000 or pk=5001 or pk=5002")

    async def test_insert_raise_ValueError(self):
        with self.assertRaises(ValueError):
            await Test.insert(Test(id='5000', age=18),
                              '5002', 18)  # error use

    async def test_remove(self):
        await execute("DELETE FROM test WHERE id='66666'")
        original = await Test.order_by('id').find()
        await execute("INSERT INTO test (id,age,birth_place,grade) values ('66666',18,'someplace',4)")
        temp = await Test.find()
        insert_success = False
        for obj in temp:
            if obj.id == '66666' and obj.age == 18 and obj.birth_place == 'someplace' and obj.grade == 4:
                insert_success = True
                await obj.remove()
                break
        current = await Test.order_by('id').find()
        self.assertEqual(insert_success, True)
        self.assertListEqual(original, current)

    async def test_remove_raise(self):
        t = Test(age=18)
        with self.assertRaises(RuntimeError):
            await t.remove()
        self.assertLogs(logger, logging.WARNING)

    async def test_delete(self):
        await execute("delete from test where grade >= 3")
        await execute("DELETE FROM test WHERE id>='000010'")
        await execute("""INSERT INTO `test` ( `id`, `age`, `birth_place`, `grade` )
                            VALUES
                                ( '000010', 20, 'someplace', 3 ),
                                ( '000011', 20, 'someplace', 3 ),
                                ( '000012', 20, 'someplace', 4 ),
                                ( '000013', 20, 'someplace', 3 ),
                                ( '000014', 20, 'someplace', 4 ),
                                ( '000015', 20, 'someplace', 3 ),
                                ( '000016', 20, 'someplace', 5 ),
                                ( '000017', 20, 'someplace', 3 )""")
        r = await Test.flex_filter(Test.grade >= 3).aggregate(num=Count('*'))
        r8 = r['num']
        rdelete5 = await Test.filter(grade=3).delete()
        r = await Test.flex_filter(Test.grade >= 3).aggregate(num=Count('*'))
        r3 = r['num']
        rdelete3 = await Test.flex_filter(Test.grade > 3).delete()
        r = await Test.flex_filter(Test.grade >= 3).aggregate(num=Count('*'))
        r0 = r['num']
        self.assertEqual(r8, 8)
        self.assertEqual(rdelete5, 5)
        self.assertEqual(r3, 3)
        self.assertEqual(rdelete3, 3)
        self.assertEqual(r0, 0)

    async def test_update(self):
        await execute("DELETE FROM test WHERE id>='000010'")
        await execute("""INSERT INTO `test` ( `id`, `age`, `birth_place`, `grade` )
                                    VALUES
                                        ( '000010', 20, 'someplace', 1 ),
                                        ( '000011', 20, 'someplace', 3 ),
                                        ( '000012', 20, 'someplace', 4 ),
                                        ( '000013', 20, 'someplace', 2 ),
                                        ( '000014', 20, 'someplace', 4 ),
                                        ( '000015', 20, 'someplace', 3 ),
                                        ( '000016', 20, 'someplace', 5 ),
                                        ( '000017', 20, 'someplace', 3 )""")
        r = await Test.flex_filter(Test.id >= '000010').update(grade=6)
        self.assertEqual(r, 8)
        r_changed = await Test.flex_filter(Test.id > '000010').find()
        for rc in r_changed:
            self.assertEqual(rc.grade, 6)


def main():
    asyncio.get_event_loop().run_until_complete(Test.create_table())
    dir_name = os.path.dirname(__file__)
    suite = unittest.defaultTestLoader.discover(dir_name, pattern='test*.py')
    unittest.TextTestRunner(verbosity=2).run(suite)
    asyncio.get_event_loop().run_until_complete(close_db_connection())


if __name__ == "__main__":
    main()
