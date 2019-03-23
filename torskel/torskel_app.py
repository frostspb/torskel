"""
Module with basic tornado application class
"""

# pylint: disable=W0511
import json
import os.path
import importlib
import logging.handlers
from urllib.parse import urlencode
import tornado.log
import tornado.web
import tornado.httpclient
from tornado.options import options
from tornado.web import Application
from tornado.httpclient import AsyncHTTPClient
import xmltodict

from torskel.torskel_ping_handler import TorskelPingHandler
from torskel.torskel_mixins.redis_mixin import RedisApplicationMixin
from torskel.torskel_mixins.log_mix import TorskelLogMixin
from torskel.libs.db_utils.mongo import get_mongo_pool
from torskel.libs.db_utils.mongo import bulk_mongo_insert
from torskel.libs.str_consts import INIT_REDIS_LABEL
from torskel.libs.str_consts import DEFAULT_SERVER_VERSION
from torskel.libs.event_controller import TorskelEventLogController
from torskel.libs.startup import server_init

# server params
options.define('debug', default=True, help='debug mode', type=bool)
options.define("port", default=8888, help="run on the given port", type=int)
options.define("srv_name", 'LOCAL', help="Server verbose name", type=str)
options.define("run_on_socket", False, help="Run on socket", type=bool)
options.define("socket_path", None, help="Path to unix-socket", type=str)

# using uvloop
options.define("use_uvloop", False, help="Use uvloop", type=bool)

# xml-rpc
options.define(
    'use_xmlrpc', default=False, help='use xmlrpc client', type=bool
)
options.define("max_xmlrpc_clients", default=10, type=int)

# autocreating ping handler
options.define("create_ping_handler", default=False, type=bool)
options.define("ping_handler_url", default='/service/ping', type=str)

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

# graylog options

options.define('use_graylog', default=False, help='use graylog', type=bool)
options.define("graylog_host", default='127.0.0.1', type=str)
options.define("graylog_port", default=12201, type=int)


class TorskelServer(Application, RedisApplicationMixin, TorskelLogMixin):
    """
    Base class of tornado application. Contains methods for work with redis,
    mongoDB and etc
    """
    def __init__(self, handlers, root_dir=None, static_path=None,
                 template_path=None, **settings):
        self.log_msg_tmpl = '%s %s'

        # TODO add valiate paths
        create_http_client = settings.get('create_http_client', True)
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
        self.server_version = settings.get('version', DEFAULT_SERVER_VERSION)
        self.logger = tornado.log.gen_log

        tornado.ioloop.IOLoop.configure(
            'tornado.platform.asyncio.AsyncIOMainLoop'
        )

        if options.use_mail_logging:
            self._set_mail_logging()

        if options.use_curl_http_client:
            self.log_debug(options.use_curl_http_client,
                           grep_label='use_curl_http_client')
            try:
                importlib.import_module('pycurl')
                AsyncHTTPClient.configure(
                    "tornado.curl_httpclient.CurlAsyncHTTPClient"
                )
            except ImportError:
                raise ImportError('Required package for CurlAsyncHTTPClient '
                                  'pycurl is missing')

        self.http_client = AsyncHTTPClient(
            max_clients=options.max_http_clients
        ) if create_http_client else None

        self._configure_mongo()
        self.event_writer = TorskelEventLogController()
        self._configure_ping_handler()
        self.log_info('Configuring loop')
        self._configure_loop()

    @staticmethod
    def _configure_loop():
        """
        Configuration loop
        :return:
        """
        if options.use_uvloop:
            try:
                uvloop = importlib.import_module('uvloop')
                uvloop.install()
            except ImportError:
                raise ImportError('Required package uvloop is missing')

    def _configure_mongo(self):
        """
        Configuration mongodb connection
        :return:
        """
        if options.use_mongo:
            try:
                self.mongo_pool = get_mongo_pool(
                    mongo_db_name=options.mongo_db_name,
                    mongo_user=options.mongo_user,
                    mongo_psw=options.mongo_psw,
                    mongo_auth_db_name=options.mongo_auth_db_name,
                    mongo_server=options.mongo_server,
                    mongo_port=options.mongo_port,
                    mongo_min_pool_size=options.mongo_min_pool_size,
                    mongo_max_pool_size=options.mongo_max_pool_size
                )
            except ModuleNotFoundError:
                self.mongo_pool = None
                raise
        else:
            self.mongo_pool = None

    def _configure_ping_handler(self):
        """
        Configuration ping handler
        :return:
        """
        if options.create_ping_handler:
            self.log_info('Creating ping handler')

            self.add_handlers(
                ".*",
                [(options.ping_handler_url, TorskelPingHandler)]
            )

    def init_srv(self):
        """
        Initializing an application on a port or socket depending on
         the settings
        :return: None
        """
        server_init(self)
        self.init_with_loop()
        tornado.ioloop.IOLoop.current().start()

    @staticmethod
    def get_secret_key() -> str:
        """
        Return secret key from options
        :return: str
        """
        return options.secret_key

    # ########################### #
    #  Validate params functions  #
    # ########################### #
    @staticmethod
    def _validate_options() -> bool:
        """
        Skeleton for validating options
        :return: bool
        """
        return True

    @staticmethod
    def _validate_path() -> bool:
        """
        Skeleton for validating paths
        :return: bool
        """
        return True

    @staticmethod
    def _validate_mail_params() -> bool:
        """
        Skeleton for validating email
        :return: bool
        """
        return True

    # ################# #
    #  Init with loop   #
    # ################# #

    def init_with_loop(self):
        """
        Initialization with loop
        :param loop:
        :return:
        """

        if options.use_redis:
            self.log_info("Init Redis connection pool... ")
            self.log_info(f"ADDR={self.redis_addr} DB={self.redis_db}",
                          grep_label=INIT_REDIS_LABEL)
            self.log_info(f"MIN_POOL_SIZE={self.redis_min_con} "
                          f"MAX_POOL_SIZE={self.redis_max_con}",
                          grep_label=INIT_REDIS_LABEL)
            self.init_redis_pool()
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
            try:
                tornado_xmlrpc = importlib.import_module(
                    'tornado_xmlrpc.client')
                res = tornado_xmlrpc.ServerProxy(
                    xmlrpc_server,
                    AsyncHTTPClient(max_clients=max_connections)
                )
            except ImportError:
                raise ImportError(
                    'Required package tornado_xmlrpc is missing!'
                )

        return res

    async def http_request_post(self, url, body, **kwargs):
        """
        http request. Method POST
        :param url: url
        :param body: dict with POST-params
        param from_json: boolean, convert response to dict
        none_if_err return None if failed request, default True
        :return: response
        """
        from_json = kwargs.get('from_json', False)
        from_xml = kwargs.get('from_xml', False)
        log_timeout_exc = kwargs.get('log_timeout_exc', True)
        none_if_err = kwargs.get('none_if_err', True)
        # clear torskel params from kwargs
        kwargs.pop('from_json', False)
        kwargs.pop('from_xml', False)
        kwargs.pop('log_timeout_exc', False)
        kwargs.pop('none_if_err', False)
        self.log_debug(log_timeout_exc, grep_label='log_timeout_exc')
        res = None
        try:
            headers = None
            param_s = urlencode(body)

            res_fetch = await self.http_client.fetch(url, method='POST',
                                                     body=param_s,
                                                     headers=headers, **kwargs)

            res_s = res_fetch.body.decode(encoding="utf-8") \
                if res_fetch is not None else res_fetch

            res = res_s
            if from_json:
                res = json.loads(res_s)
            if from_xml:
                res = json.loads(json.dumps(xmltodict.parse(res_s)))
        except tornado.httpclient.HTTPError as exception:
            if exception.code == 599:
                if log_timeout_exc is True:
                    self.log_exc('http_request_get failed by timeout url = %s'
                                 % url)
                else:
                    self.log_debug('http_request_get failed by timeout')
            if none_if_err:
                res = None

        return res

    async def http_request_get(self, url, **kwargs):
        """
        http request. Method GET
        :param url: url
        param from_json: boolean, convert response to dict
        none_if_err return None if failed request, default True
        :return: response
        """
        from_json = kwargs.get('from_json', False)
        from_xml = kwargs.get('from_xml', False)
        log_timeout_exc = kwargs.get('log_timeout_exc', True)
        none_if_err = kwargs.get('none_if_err', True)

        # clear torskels params
        kwargs.pop('from_json', False)
        kwargs.pop('from_xml', False)
        kwargs.pop('log_timeout_exc', False)
        kwargs.pop('none_if_err', False)

        self.log_debug(log_timeout_exc, grep_label='log_timeout_exc')
        res = None
        try:
            res_fetch = await self.http_client.fetch(url, **kwargs)
            res_s = res_fetch.body.decode(encoding="utf-8") \
                if res_fetch is not None else res_fetch

            res = res_s
            if from_json:
                res = json.loads(res_s)

            if from_xml:
                res = json.loads(json.dumps(xmltodict.parse(res_s)))
        except tornado.httpclient.HTTPError as exception:
            if exception.code == 599:
                if log_timeout_exc is True:
                    self.log_exc('http_request_get failed by timeout url = %s'
                                 % url)
                else:
                    self.log_debug('http_request_get failed by timeout')
            if none_if_err:
                res = None

        return res

    def _set_mail_logging(self, log_level=logging.ERROR):
        """
        Init SMTP log handler for sendig log to email
        :param log_level: log level
        :return:

        """
        if options.log_mail_user == '' and options.log_mail_psw == '':
            credentials_list = None
        else:
            credentials_list = [
                options.log_mail_user, options.log_mail_psw
            ]

        # TODO validate mail params try catch
        mail_logging = logging.handlers.SMTPHandler(
            mailhost=options.log_mail_host,
            fromaddr=options.log_mail_from,
            toaddrs=options.log_mail_to,
            subject=options.log_mail_subj,
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
