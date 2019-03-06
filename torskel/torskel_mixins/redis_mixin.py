"""
Module contains class for work with Redis
"""
import json
import asyncio
import importlib

import tornado.web
import tornado.httpclient
import tornado.log

from tornado.options import options


class RedisApplicationMixin():
    """
    Redis controller
    """
    def __init__(self):
        self.logger = tornado.log.gen_log
        self.redis_connection_pool = None

    @property
    def redis_addr(self) -> str:
        """
        Returns address for connecting to redis
        :return: str
        """
        redis_addr = options.redis_socket if options.use_redis_socket \
            else (options.redis_host, options.redis_port)
        return redis_addr

    @property
    def redis_min_con(self) -> int:
        """
        Returns the minimal size of redis connections pool
        :return: int
        """
        return options.redis_min_con

    @property
    def redis_max_con(self) -> int:
        """
        Returns the maximal size of redis connections pool
        :return: int
        """
        return options.redis_max_con

    @property
    def redis_psw(self) -> str:
        """
        Returns password for connecting to redis
        :return: str
        """
        psw = options.redis_psw

        if psw == "":
            psw = None
        return psw

    @property
    def redis_db(self) -> int:
        """
        Returns number of default redis database
        :return: int
        """
        db_number = options.redis_db
        if db_number == -1:
            db_number = None
        return db_number

    @staticmethod
    def _get_json_util() -> object:
        """
        Returns json_util from bson if exists
        :return:
        """
        try:
            bson = importlib.import_module('bson')

            json_util = bson.json_util
        except ImportError:
            json_util = False
        return json_util

    def init_redis_pool(self):
        """
        Init redis connection pool
        """
        try:
            aioredis = importlib.import_module('aioredis')
            self.redis_connection_pool \
                = asyncio.get_event_loop().run_until_complete(
                    aioredis.create_pool(
                        self.redis_addr,
                        password=self.redis_psw,
                        db=self.redis_db,
                        minsize=self.redis_min_con,
                        maxsize=self.redis_max_con
                    )
                )
        except ImportError:
            raise ImportError('Required package aioredis is missing')

    async def set_redis_exp_val(self, key, val, exp=None, **kwargs):
        """
        Write value to redis
        :param key: key
        :param val: value
        :param exp: Expire time in seconds
        param convert_to_json: bool
        param use_json_utils: bool use json utils from bson

        """

        convert_to_json = kwargs.get('convert_to_json', False)
        use_json_utils = kwargs.get('use_json_utils', False)
        if convert_to_json:
            if use_json_utils:
                json_util = self._get_json_util()
                if json_util:
                    val = json.dumps(val, default=json_util.default)
                else:
                    raise ImportError('Can not import json_util. '
                                      'Module bson is missing')
            else:
                val = json.dumps(val)

        await self.redis_connection_pool.execute('set', key, val)
        if isinstance(exp, int):
            await self.redis_connection_pool.execute('expire', key, exp)

    async def del_redis_val(self, key):
        """
        delete value from redis by key
        :param key: key

        """

        await self.redis_connection_pool.execute('del', key)

    async def get_redis_val(self, key: str, **kwargs):
        """
        get value from redis by key
        :param key: key
        param from_json: loads from json
        param use_json_utils: bool use json utils from bson
        :return: value
        """

        from_json = kwargs.get('from_json', False)
        use_json_utils = kwargs.get('use_json_utils', False)

        val = await self.redis_connection_pool.execute('get', key)
        redis_val = val.decode('utf-8') if val is not None else val
        if redis_val:
            if use_json_utils:
                json_util = self._get_json_util()
                if json_util:
                    res = json.loads(
                        redis_val, object_hook=json_util.object_hook
                    ) if from_json else redis_val
                else:
                    raise ImportError('Can not import json_util. '
                                      'Module bson is missing')

            else:
                res = json.loads(redis_val) if from_json else redis_val
        else:
            res = None
        return res
