import json
import os.path
import logging.handlers
import tornado.log
import tornado.web
import xmltodict
import tornado.httpclient

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

try:
    import pycurl
except ImportError:
    pycurl = None

try:
    from tornado_xmlrpc.client import ServerProxy
    xmlrpc_import = True
except ImportError:
    xmlrpc_import = False

from tornado.options import options
from urllib.parse import urlencode
from tornado.httpclient import AsyncHTTPClient
from tornado.autoreload import watch
from torskel.libs.db_utils.mongo import get_mongo_pool
from torskel.libs.db_utils.mongo import bulk_mongo_insert
from torskel.libs.str_consts import INIT_REDIS_LABEL
from torskel.libs.event_controller import TorskelEventLogController
from torskel.libs.startup import server_init


settings = {
    # 'cookie_secret': options.secret_key,
    # 'xsrf_cookies': True,
}

# server params
options.define('debug', default=True, help='debug mode', type=bool)
options.define("port", default=8888, help="run on the given port", type=int)
options.define("srv_name", 'LOCAL', help="Server verbose name", type=str)
options.define("run_on_socket", False, help="Run on socket", type=bool)
options.define("socket_path", None, help="Path to unix-socket", type=str)


# xml-rpc
options.define('use_xmlrpc', default=False, help='use xmlrpc client', type=bool)
options.define("max_xmlrpc_clients", default=10, type=int)

# http-client params
options.define("max_http_clients", default=100, type=int)
options.define("http_client_timeout", default=30, type=int)
options.define("use_curl_http_client", default=False, type=bool)

# mail logger params
options.define('use_mail_logging', default=False, help='SMTP log handler',
               type=bool)
options.define("log_mail_subj", default='', type=str)
options.define("log_mail_from", default='', type=str)
options.define("log_mail_to", default=[], type=list)
options.define("log_mail_host", default='', type=str)
options.define("log_mail_user", default='', type=str)
options.define("log_mail_psw", default='', type=str)

# mongodb params
options.define("use_mongo", default=False, help="use mongodb", type=bool)
options.define("mongo_server", default="localhost", type=str)
options.define("mongo_port", default=27017, type=int)
options.define("mongo_db_name", type=str)
options.define("mongo_auth_db_name", default=options.mongo_db_name, type=str)
options.define("mongo_user", type=str)
options.define("mongo_psw", type=str)
options.define("mongo_min_pool_size", default=5, type=int)
options.define("mongo_max_pool_size", default=10, type=int)

# redis params
options.define('use_redis', default=False, help='use redis', type=bool)
options.define('use_redis_socket', default=True,
               help='connection to redis unixsocket file', type=bool)
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

# events writer params
options.define('use_events_writer', default=False, help='use_events_writer',
               type=bool)
options.define('show_log_event_writer', default=False,
               type=bool)
options.define('use_lite_event', default=False, type=bool)
options.define("task_list_size", default=10, type=int)
options.define("writer_period", default=1000*10, type=int)
options.define("events_collection_name", default='user_events', type=str)

# user language settings
options.define("default_local_language", default='en', type=str)
options.define("default_international_language", default='en', type=str)


class TorskelServer(tornado.web.Application):
    def __init__(self, handlers, root_dir=None, static_path=None,
                 template_path=None, create_http_client=True, **settings):
        self.log_msg_tmpl = '%s %s'

        # TODO add valiate paths
        if root_dir is not None:
            app_static_dir = os.path.join(root_dir, "static") \
                if static_path is None else static_path

            app_template_dir = os.path.join(root_dir, "templates") \
                if template_path is None else template_path
        else:
            app_template_dir = app_static_dir = None

        super().__init__(handlers, static_path=app_static_dir,
                         template_path=app_template_dir,
                         **settings)
        self.server_name = options.srv_name
        self.logger = tornado.log.gen_log
        self.redis_connection_pool = None
        tornado.ioloop.IOLoop.configure(
            'tornado.platform.asyncio.AsyncIOMainLoop'
        )

        if options.use_mail_logging:
            if options.log_mail_user == '' and options.log_mail_psw == '':
                credentials_list = None
            else:
                credentials_list = [
                    options.log_mail_user, options.log_mail_psw
                ]

            self.set_mail_logging(options.log_mail_host, options.log_mail_from,
                                  options.log_mail_to,
                                  options.log_mail_subj, credentials_list)

        if options.use_reactjs:
            if not jinja2_import:
                self.react_env = self.react_assets = None
                raise ImportError('Required package jinja2 is missing')
            else:
                self.react_env = Environment(
                    loader=FileSystemLoader('templates')
                )
                self.react_assets = self.load_react_assets()

        else:
            self.react_env = self.react_assets = None

        if options.use_curl_http_client:
            self.log_debug(options.use_curl_http_client,
                           grep_label='use_curl_http_client')
            if pycurl is None:
                raise ImportError('Required package for pycurl '
                                  'CurlAsyncHTTPClient  is missing')
            else:
                self.log_debug('configure curl')
                AsyncHTTPClient.configure(
                    "tornado.curl_httpclient.CurlAsyncHTTPClient"
                )

        self.http_client = AsyncHTTPClient(
            max_clients=options.max_http_clients
        ) if create_http_client else None

        if options.use_mongo:
            try:
                self.mongo_pool = get_mongo_pool(options.mongo_db_name,
                                                 options.mongo_user,
                                                 options.mongo_psw,
                                                 options.mongo_auth_db_name,
                                                 options.mongo_server,
                                                 options.mongo_port,
                                                 options.mongo_min_pool_size,
                                                 options.mongo_max_pool_size)
            except ModuleNotFoundError:
                self.mongo_pool = None
                raise
        else:
            self.mongo_pool = None
        self.event_writer = TorskelEventLogController()

    def init_srv(self):
        """
        Initializing an application on a port or socket depending on
         the settings
        :return: None
        """
        server_init(self)

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

    def init_with_loop(self, loop=None):
        if options.use_redis:
            # check aioredis lib
            if aioredis is None:
                raise ImportError('Required package aioredis is missing')
            else:
                self.init_redis_pool(loop)
        if options.use_events_writer:
            self.log_info('Init events writer')
            event_writer = tornado.ioloop.PeriodicCallback(
                self.write_log_from_queue,
                options.writer_period
            )
            event_writer.start()

    # ############################# #
    #  Async Http-client functions  #
    # ############################# #
    @staticmethod
    def get_xmlrpc_server(xmlrpc_server,
                          max_connections=options.max_xmlrpc_clients):
        """
        return connection to xmlrpc server
        :param xmlrpc_server: server url
        :param max_connections: count of max connections
        :return: connection
        """
        res = None
        if options.use_xmlrpc:
            if not xmlrpc_import:
                raise ImportError('Required package tornado_xmlrpc is missing!')
            else:
                res = ServerProxy(xmlrpc_server,
                                  AsyncHTTPClient(max_clients=max_connections)
                                  )
        return res

    async def http_request_post(self, url, body, **kwargs):
        """
        http request. Method POST
        :param url: url
        :param body: dict with POST-params
        :param from_json: boolean, convert response to dict
        :return: response
        """
        from_json = kwargs.get('from_json', False)
        from_xml = kwargs.get('from_xml', False)
        log_timeout_exc = kwargs.get('log_timeout_exc', True)
        self.log_debug(log_timeout_exc, grep_label='log_timeout_exc')
        res = None
        try:
            headers = None
            param_s = urlencode(body)

            res_fetch = await self.http_client.fetch(url, method='POST',
                                                     body=param_s,
                                                     headers=headers)

            res_s = res_fetch.body.decode(encoding="utf-8") \
                if res_fetch is not None else res_fetch

            res = res_s
            if from_json:
                res = json.loads(res_s)
            if from_xml:
                res = json.loads(json.dumps(xmltodict.parse(res_s)))
        except tornado.httpclient.HTTPError as e:
            if e.code == 599:
                if log_timeout_exc is True:
                    self.log_exc('http_request_get failed by timeout url = %s'
                                 % url)
                else:
                    self.log_debug('http_request_get failed by timeout')
                res = None

        except Exception:
            res = None
            self.log_exc('http_request_post failed! url = %s  body=%s '
                         % (url, body))

        return res

    async def http_request_get(self, url, **kwargs):
        """
        http request. Method GET
        :param url: url
        :param from_json: boolean, convert response to dict
        :return: response
        """
        from_json = kwargs.get('from_json', False)
        from_xml = kwargs.get('from_xml', False)
        log_timeout_exc = kwargs.get('log_timeout_exc', True)
        self.log_debug(log_timeout_exc, grep_label='log_timeout_exc')
        res = None
        try:
            res_fetch = await self.http_client.fetch(url)
            res_s = res_fetch.body.decode(encoding="utf-8") \
                if res_fetch is not None else res_fetch

            res = res_s
            if from_json:
                res = json.loads(res_s)

            if from_xml:
                res = json.loads(json.dumps(xmltodict.parse(res_s)))
        except tornado.httpclient.HTTPError as e:
            if e.code == 599:
                if log_timeout_exc is True:
                    self.log_exc('http_request_get failed by timeout url = %s'
                                 % url)
                else:
                    self.log_debug('http_request_get failed by timeout')
                res = None
        except Exception:
            self.log_exc('http_request_get failed! url = %s' % url)
            res = None

        return res

    # ######################## #
    #  Redis client functions  #
    # ######################## #

    def init_redis_pool(self, loop=None):
        """
        Init redis connection pool
        :param loop: ioloop

        """
        redis_addr = options.redis_socket if options.use_redis_socket \
            else (options.redis_host, options.redis_port)
        # TODO validate redis connection params
        redis_psw = options.redis_psw

        if redis_psw == "":
            redis_psw = None

        redis_db = options.redis_db
        if redis_db == -1:
            redis_db = None
        self.log_info("Init Redis connection pool... ")
        self.log_info(f"ADDR={redis_addr} DB={redis_db}",
                      grep_label=INIT_REDIS_LABEL)
        self.log_info(f"MIN_POOL_SIZE={options.redis_min_con} "
                      f"MAX_POOL_SIZE={options.redis_max_con}",
                      grep_label=INIT_REDIS_LABEL)

        self.redis_connection_pool = loop.run_until_complete(
            aioredis.create_pool(redis_addr, password=redis_psw, db=redis_db,
                                 minsize=options.redis_min_con,
                                 maxsize=options.redis_max_con)
        )

    async def set_redis_exp_val(self, key, val, exp=None, **kwargs):
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

        await self.redis_connection_pool.execute('set', key, val)
        if isinstance(exp, int):
            await self.redis_connection_pool.execute('expire', key, exp)

    async def del_redis_val(self, key):
        """
        delete value from redis by key
        :param key: key

        """

        await self.redis_connection_pool.execute('del', key)

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

            r = await self.redis_connection_pool.execute('get', key)
            redis_val = r.decode('utf-8') if r is not None else r
            if redis_val:
                if use_json_utils and json_util:
                    res = json.loads(
                        redis_val, object_hook=json_util.object_hook
                    ) if from_json else redis_val
                else:
                    res = json.loads(redis_val) if from_json else redis_val
            else:
                res = None
            return res
        except Exception:
            self.log_exc('get_redis_val failed key = %s' % key)
            res = None
            return res

    # ################### #
    #  Logging functions  #
    # ################### #

    def get_log_msg(self, msg, grep_label=''):
        """
        Make message by template
        :param msg: message
        :param grep_label: label for grep
        :return: compiled message
        """
        try:
            res = self.log_msg_tmpl % (grep_label, msg)
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

    def log_info(self, msg, grep_label=''):
        """
        Log info message
        :param msg: message
        :param grep_label: label for grep
        :return:
        """
        self.logger.info(self.get_log_msg(msg, grep_label))

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

    def set_mail_logging(self, mail_host, from_addr, to_addr, subject,
                         credentials_list=None, log_level=logging.ERROR):
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
        mail_logging = logging.handlers.SMTPHandler(
            mailhost=mail_host,
            fromaddr=from_addr,
            toaddrs=to_addr,
            subject=subject,
            credentials=credentials_list
        )

        mail_logging.setLevel(log_level)
        self.logger.addHandler(mail_logging)

    async def write_log_from_queue(self) -> type(None):
        """
         Retrieves events from the queue.
         and performs the insert into the database
        """
        if self.mongo_pool is None and not options.use_mongo:
            self.log_err('Can not write event. '
                         'Connection to database is missing!')
        else:
            await self.event_writer.write_log_from_queue(
                self.mongo_pool,
                options.events_collection_name,
                bulk_mongo_insert
            )
