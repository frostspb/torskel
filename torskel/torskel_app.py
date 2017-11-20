# -*- coding: utf-8 -*-
import json
import os.path
import logging.handlers
import tornado.log
import tornado.web

try:
    import aioredis
except ImportError:
    aioredis = None

try:
    import aioodbc
except ImportError:
    aioodbc = None

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    jinja2 = None


from tornado.options import options
from urllib.parse import urlencode
from tornado.httpclient import AsyncHTTPClient
from tornado.autoreload import watch

LOG_MSG_DEBUG_TMPL = '%s %s'

settings = {
    # 'cookie_secret': options.secret_key,
    # 'xsrf_cookies': True,
}

options.define('debug', default=True, help='debug mode', type=bool)
options.define("port", default=8888, help="run on the given port", type=int)

# mail logger params
options.define('use_mail_logging', default=False, help='SMTP log handler', type=bool)
options.define("log_mail_subj", default='', type=str)
options.define("log_mail_from", default='', type=str)
options.define("log_mail_to", default=[], type=list)
options.define("log_mail_host", default='', type=str)

# redis params
options.define('use_redis', default=False, help='use redis', type=bool)
options.define('use_redis_socket', default=True, help='connection to redis unixsocket file', type=bool)
options.define("redis_min_con", default=5, type=int)
options.define("redis_max_con", default=10, type=int)
options.define("redis_host", default='localhost', type=str)
options.define("redis_port", default=6379, type=int)
options.define("redis_socket", default='/var/run/redis/redis.sock', type=str)
options.define("redis_psw", default='', type=str)
options.define("redis_db", default=-1, type=int)

# reactjs params
options.define('use_reactjs', default=False, help='use reactjs', type=bool)
options.define("react_assets_file", default='webpack-assets.json', type=str)


class TorskelServer(tornado.web.Application):
    def __init__(self, handlers, root_dir=None, static_path=None, template_path=None,
                 create_http_client=True, **settings):

        # TODO add valiate paths
        if root_dir is not None:
            app_static_dir = os.path.join(root_dir, "static") if static_path is None else static_path

            app_template_dir = os.path.join(root_dir, "templates") if template_path is None else template_path
        else:
            app_template_dir = app_static_dir = None

        super().__init__(handlers, static_path=app_static_dir,
                         template_path=app_template_dir,
                         **settings)
        self.redis_connection_pool = None
        self.logger = tornado.log.gen_log
        tornado.ioloop.IOLoop.configure('tornado.platform.asyncio.AsyncIOMainLoop')

        if options.use_reactjs:
            if jinja2 is None:
                self.react_env = self.react_assets = None
                raise ImportError('Required package jinja2 is missing')
            else:
                self.react_env = Environment(loader=FileSystemLoader('templates'))
                self.react_assets = self.load_react_assets()

        else:
            self.react_env = self.react_assets = None

        self.http_client = AsyncHTTPClient() if create_http_client else None

    # ########################### #
    #  Validate params functions  #
    # ########################### #
    @staticmethod
    def validate_options():
        return True

    @staticmethod
    def validate_path():
        return True

    @staticmethod
    def validate_mail_params():
        return True

    # ######################## #
    #  ReactJS render support  #
    # ######################## #

    @staticmethod
    def load_react_assets():
        try:
            fn = options.react_assets_file
            with open(fn) as f:
                watch(fn)
                assets = json.load(f)
        except IOError:
            assets = None
        except KeyError:
            assets = None
        return assets

    # ################# #
    #  Init with loop   #
    # ################# #

    def init_with_loop(self, loop):
        if options.use_redis:
            # check aioredis lib
            if aioredis is None:
                raise ImportError('Required package aioredis is missing')
            else:
                self.init_redis_pool(loop)

    # ################### #
    #  Logging functions  #
    # ################### #

    def set_mail_logging(self, mail_host, from_addr, to_addr, subject, credentials_list=None, log_level=logging.ERROR):
        # TODO validate mail params try catch
        mail_logging = logging.handlers.SMTPHandler(mailhost=mail_host,
                                                    fromaddr=from_addr,
                                                    toaddrs=to_addr,
                                                    subject=subject,
                                                    credentials=credentials_list
                                                    )

        mail_logging.setLevel(log_level)
        self.logger.addHandler(mail_logging)

    def get_log_msg(self, msg, grep_label=''):
        """
        Собирает соощение по шаблону
        :param msg: сообщение
        :param grep_label: метка для грепанья
        :return: итоговое сообщение
        """
        try:
            res = LOG_MSG_DEBUG_TMPL % (grep_label, msg)
        except Exception:
            res = msg
        return res

    def log_debug(self, msg, grep_label=''):
        """
        Дебаг лог
        :param msg: сообщение
        :param grep_label: метка для грепанья
        :return:
        """
        self.logger.debug(self.get_log_msg(msg, grep_label))

    def log_err(self, msg, grep_label=''):
        """
        Логирует ошибку
        :param msg: сообщение
        :param grep_label: метка для грепанья
        :return:
        """
        self.logger.error(self.get_log_msg(msg, grep_label))

    def log_exc(self, msg, grep_label=''):
        """
        Логирует исключение
        :param msg: сообщение
        :param grep_label: метка для грепанья
        :return:
        """
        self.logger.exception(self.get_log_msg(msg, grep_label))

    # ############################# #
    #  Async Http-client functions  #
    # ############################# #
    async def http_request_post(self, url, body):
        """
        Делает http post запрос
        :param url: урл
        :param body: словарь с пост-параметрами
        :return: словарь
        """
        try:
            headers = None
            param_s = urlencode(body)

            res = await self.http_client.fetch(url, method='POST', body=param_s, headers=headers)

            res_s = res.body.decode(encoding="utf-8")
            res_json = json.loads(res_s)
        except Exception:
            res_json = None
            self.log_exc('http_request_post failed! url = %s  body=%s ' % (url, body))

        return res_json

    async def http_request_get(self, url):
        """
        Делает http запрос, ответ либо json либо xml
        :param url: урл
        :param type_resp: тип ответа
        :return: словарь
        """
        try:
            res_fetch = await self.http_client.fetch(url)
            res_s = res_fetch.body.decode(encoding="utf-8")
            res_json = json.loads(res_s)
            res = res_json
        except Exception:
            self.log_exc('http_request_get failed! url = %s' % url)
            res = None
        return res

    # ######################## #
    #  Redis client functions  #
    # ######################## #

    def init_redis_pool(self, loop):
        redis_addr = options.redis_socket if options.use_redis_socket else (options.redis_host, options.redis_port)
        # TODO validate redis connection params
        redis_psw = options.redis_psw

        if redis_psw == "":
            redis_psw = None

        redis_db = options.redis_db
        if redis_db == -1:
            redis_db = None

        self.redis_connection_pool = loop.run_until_complete(aioredis.create_pool(
            redis_addr, password=redis_psw, db=redis_db,
            minsize=options.redis_min_con, maxsize=options.redis_max_con,
            loop=loop))


    async def set_redis_exp_val(self, key, val, exp, conver_to_json=False):
        if conver_to_json:
            val = json.dumps(val)

        with await self.redis_connection_pool as redis:
            await redis.connection.execute('set', key, val)
            await redis.connection.execute('expire', key, exp)

    async def del_redis_val(self, key):
        with await self.redis_connection_pool as redis:
            await redis.connection.execute('del', key)

    async def get_redis_val(self, key, from_json=True):
        """
            Достать инфу из редиса
        """
        try:
            with await self.redis_connection_pool as redis:
                r = await redis.connection.execute('get', key)
                redis_val = r.decode('utf-8')
                if redis_val:
                    res = json.loads(redis_val) if from_json else redis_val
                else:
                    res = None
                return res
        except:
            self.log_exc('get_redis_val failed key = %s' % key)
            res = None
            return res
