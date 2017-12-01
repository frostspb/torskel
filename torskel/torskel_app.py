# -*- coding: utf-8 -*-
import json
import os.path
import logging.handlers
import tornado.log
import tornado.web
import xmltodict

try:
    from bson import json_util
except ImportError:
    json_util = False

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
    jinja2_import = True
except ImportError:
    jinja2_import = False


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
options.define("log_mail_user", default='', type=str)
options.define("log_mail_psw", default='', type=str)

# redis params
options.define('use_redis', default=False, help='use redis', type=bool)
options.define('use_redis_socket', default=True, help='connection to redis unixsocket file', type=bool)
options.define("redis_min_con", default=5, type=int)
options.define("redis_max_con", default=10, type=int)
options.define("redis_host", default='127.0.0.1', type=str)
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
        #self.redis_connection_pool = None
        self.logger = tornado.log.gen_log
        tornado.ioloop.IOLoop.configure('tornado.platform.asyncio.AsyncIOMainLoop')

        if options.use_mail_logging:
            if options.log_mail_user == '' and options.log_mail_psw == '':
                credentials_list = None
            else:
                credentials_list = [options.log_mail_user, options.log_mail_psw]

            self.set_mail_logging(options.log_mail_host, options.log_mail_from, options.log_mail_to,
                                  options.log_mail_subj, credentials_list)

        if options.use_reactjs:
            if not jinja2_import:
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
        """
        Init SMTP log handler for sendig log to email
        :param mail_host: host
        :param from_addr: from
        :param to_addr: to
        :param subject: subject
        :param credentials_list: (login, password)
        :param log_level: log level
        :return:
        """
        # TODO validate mail params try catch
        mail_logging = logging.handlers.SMTPHandler(mailhost=mail_host,
                                                    fromaddr=from_addr,
                                                    toaddrs=to_addr,
                                                    subject=subject,
                                                    credentials=credentials_list
                                                    )

        mail_logging.setLevel(log_level)
        self.logger.addHandler(mail_logging)

    @staticmethod
    def get_log_msg(msg, grep_label=''):
        """
        Make message by template
        :param msg: message
        :param grep_label: label for grep
        :return: compiled message
        """
        try:
            res = LOG_MSG_DEBUG_TMPL % (grep_label, msg)
        except Exception:
            res = msg
        return res

    def log_debug(self, msg, grep_label=''):
        """
        Log debug message
        :param msg: message
        :param grep_label: label for grep
        :return:
        """
        self.logger.debug(self.get_log_msg(msg, grep_label))

    def log_err(self, msg, grep_label=''):
        """
        Log error
        :param msg: message
        :param grep_label: label for grep
        :return:
        """
        self.logger.error(self.get_log_msg(msg, grep_label))

    def log_exc(self, msg, grep_label=''):
        """
        Log exception
        :param msg: message
        :param grep_label: label for grep
        :return:
        """
        self.logger.exception(self.get_log_msg(msg, grep_label))

    # ############################# #
    #  Async Http-client functions  #
    # ############################# #
    async def http_request_post(self, url, body, **kwargs):
        """
        http request. Method POST
        :param url: url
        :param body: dict with POST-params
        :param from_json: boolean, convert response to dict
        :return: response
        """
        try:
            headers = None
            param_s = urlencode(body)

            res_fetch = await self.http_client.fetch(url, method='POST', body=param_s, headers=headers)

            res_s = res_fetch.body.decode(encoding="utf-8") if res_fetch is not None else res_fetch
            from_json = kwargs.get('from_json', False)
            from_xml = kwargs.get('from_xml', False)
            res = res_s
            if from_json:
                res = json.loads(res_s)
            if from_xml:
                res = json.loads(json.dumps(xmltodict.parse(res_s)))

        except Exception:
            res = None
            self.log_exc('http_request_post failed! url = %s  body=%s ' % (url, body))

        return res

    async def http_request_get(self, url, **kwargs):
        """
        http request. Method GET
        :param url: url
        :param from_json: boolean, convert response to dict
        :return: response
        """
        try:
            res_fetch = await self.http_client.fetch(url)
            res_s = res_fetch.body.decode(encoding="utf-8") if res_fetch is not None else res_fetch
            from_json = kwargs.get('from_json', False)
            from_xml = kwargs.get('from_xml', False)
            res = res_s
            if from_json:
                res = json.loads(res_s)

            if from_xml:
                res = json.loads(json.dumps(xmltodict.parse(res_s)))
        except Exception:
            self.log_exc('http_request_get failed! url = %s' % url)
            res = None
        return res

    # ######################## #
    #  Redis client functions  #
    # ######################## #

    def init_redis_pool(self, loop):
        """
        Init redis connection pool
        :param loop: ioloop

        """
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

    async def set_redis_exp_val(self, key, val, exp, **kwargs):
        """
        Write value to redis
        :param key: key
        :param val: value
        :param exp: Expire time in seconds
        :param convert_to_json: bool
        :param use_json_utils: bool use json utils from bson

        """
        convert_to_json = kwargs.get('convert_to_json', False)
        use_json_utils = kwargs.get('use_json_utils', False)
        if convert_to_json:
            if use_json_utils and json_util:
                val = json.dumps(val, default=json_util.default)
            else:
                val = json.dumps(val)

        with await self.redis_connection_pool as redis:
            await redis.execute('set', key, val)
            await redis.execute('expire', key, exp)

    async def del_redis_val(self, key):
        """
        delete value from redis by key
        :param key: key

        """
        with await self.redis_connection_pool as redis:
            await redis.execute('del', key)

    async def get_redis_val(self, key, **kwargs):
        """
        get value from redis by key
        :param key: key
        :param from_json: loads from json
        :param use_json_utils: bool use json utils from bson
        :return: value
        """
        try:
            from_json = kwargs.get('from_json', False)
            use_json_utils = kwargs.get('use_json_utils', False)
            with await self.redis_connection_pool as redis:
                r = await redis.execute('get', key)
                redis_val = r.decode('utf-8') if r is not None else r
                if redis_val:
                    if use_json_utils and json_util:
                        res = json.loads(redis_val, object_hook=json_util.object_hook) if from_json else redis_val
                    else:
                        res = json.loads(redis_val) if from_json else redis_val
                else:
                    res = None
                return res
        except:
            self.log_exc('get_redis_val failed key = %s' % key)
            res = None
            return res
