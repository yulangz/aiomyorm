aiomyorm is a simple and easy-to-use ORM framework, which has a similar interface to Django and fully supports asyncio.

## Features


* Perfect support for asyncio and uvloop.
* Simple and easy to use API, similar to Django.
* Support mysql and SQLite.

## Installation
```shell script
pip install aiomyorm
```
   

## Getting Started


```python
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
```
the results
```text
   to create table test.
   insert rows:  3
   pk:5000, id:, age:18, birth_place:place1, grade:0
   pk:5001, id:, age:21, birth_place:place2, grade:0
   pk:5002, id:, age:19, birth_place:place3, grade:0
```

more use see the document: [aiomyorm](https://aiomyorm.readthedocs.io)

## Dependencies

* Python >= 3.5.3
* [aiomysql](https://github.com/aio-libs/aiomysql) (for MySQL)
* [aiosqlite](https://github.com/jreese/aiosqlite) (for sqlite)

## Tests

I have a simple test for you.

It's better for you to test in a ``venv``.

first
```shell script
git clone git@github.com:yulansp/aiomyorm.git
```
then
``` shell script
pip install -r requirements.txt
```

Recipe you must install MySQL and configure the user name and password
in the ``tests/test_mysql/config.py`` file.

then
```shell script
make test
```

## License

MIT