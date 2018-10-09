try:
    from bson import json_util
except ImportError:
    json_util = False

import tornado.gen
from tornado.options import options
from user_agents import parse
from datetime import datetime
from torskel.str_utils import get_hash_str
from torskel.str_utils import is_hash_str
from torskel.torskel_mixins.log_mix import TorskelLogMixin
from torskel.libs.str_consts import EVENTS_USER_AGENT
from torskel.libs.str_consts import EVENTS_DATE
from torskel.libs.str_consts import EVENTS_IP, EVENTS_METHOD
from torskel.libs.str_consts import EVENTS_URL, EVENTS_SRV_NAME
from torskel.str_utils import default_json_dt


class TorskelHandler(tornado.web.RequestHandler, TorskelLogMixin):
    def __init__(self, application, request, **kwargs):
        super(TorskelHandler, self).__init__(application, request, **kwargs)
        # filter dict by list of keys
        self.filter_dict = lambda x, y: dict(
            [(i, x[i]) for i in x if i in set(y)]
        )

    def react_render(self, template_name, render_data_dict=None):
        if render_data_dict is None:
            render_data_dict = {}
        template = self.application.react_env.get_template(template_name)
        render_data_dict.update({'assets': self.application.react_assets})
        return self.write(template.render(render_data_dict))

    @staticmethod
    def get_hash_str(value, alg='sha224'):
        """
        Return hash by string
        :param value: source string
        :param alg: algorithm, default sha224
        :return: hash
        """
        return get_hash_str(value, alg)

    @staticmethod
    def is_hash_str(value):
        """
        Checks whether the hash string is a string of any algorithm
        :param value: hash string
        :return: boolean
        """
        return is_hash_str(value)

    def get_req_args(self, args_list=None):
        """
        Get list of params from request
        :param args_list: list of params
        :return: list of values
        """
        if not args_list:
            args_list = []
        return [self.get_argument(x, False) for x in args_list]

    def get_req_args_dict(self):
        """
        Return dict of request arguments
        :return: dict
        """

        try:
            res = {
                k: ''.join([i.decode('utf-8') for i in v])
                for k, v in self.request.arguments.items()
            }
        except Exception:
            self.log_exc('get_req_args_dict failed')
            res = {}
        return res

    def get_user_ip(self):
        """
        Return user ip from request object
        :return: user_ip
        """
        x_real_ip = self.request.headers.get("X-Real-IP")
        remote_ip = x_real_ip or self.request.remote_ip
        return remote_ip

    def _handle_request_exception(self, e):
        super(TorskelHandler, self)._handle_request_exception(e)
        msg = '''handler classname = %s \n
                request = %s \n
                exception = %s \n'''

        self.log_exc(msg % (type(self).__name__, self.request, e))

    async def http_request_get(self, url, **kwargs):
        """
        async http request. Method GET
        :param url: url
        :param from_json: boolean, convert response to dict
        :return: response
        """

        return await self.application.http_request_get(url, **kwargs)

    async def http_request_post(self, url, body, **kwargs):
        """
        async http request. Method POST
        :param url: url
        :param body: dict with POST-params
        :param from_json: boolean, convert response to dict
        :return: response
        """
        return await self.application.http_request_post(url, body, **kwargs)

    # TODO refact add params to kwargs
    async def set_redis_exp_val(self, key, val, exp, **kwargs):
        """
        Write value to redis
        :param key: key
        :param val: value
        :param exp: Expire time in seconds
        :param convert_to_json: bool
        :param use_json_utils: bool use json utils from bson
        """
        await self.application.set_redis_exp_val(key, val, exp, **kwargs)

    async def del_redis_val(self, key):
        """
        delete value from redis by key
        :param key: key

        """
        await self.application.del_redis_val(key)

    async def get_redis_val(self, key, **kwargs):
        """
        get value from redis by key
        :param key: key
        :param from_json: loads from json
        :param use_json_utils: bool use json utils from bson
        :return: value
        """
        res = await self.application.get_redis_val(key, **kwargs)
        return res

    def get_current_url(self):
        """
        Get current handler url for urls named by class name
        :return: str
        """
        return self.reverse_url(self.__class__.__name__)

    def get_user_agent(self) -> str:
        """
        Defines the device, OS and user browser by the User-Agent header
        :return: str
        """
        try:
            ua_string = self.request.headers["User-Agent"]
            user_agent = str(parse(ua_string))
        except KeyError:
            user_agent = 'Unknown'
        self.log_debug(user_agent, grep_label='USER_AGENT')
        return user_agent

    def get_user_lang_list(self) -> list:
        """
        Returns a list of the language codes configured in the client's browser
        :return: language codes
        """
        try:
            languages = self.request.headers["Accept-Language"].split(",")
            res = [
                language.strip().split(";")[0][:2] for language in languages
            ]
        except Exception:
            res = [options.default_local_language]
        return res

    def add_log_event(self, event=None, use_legacy_event=True):
        if event is None:
            event = {}
        if use_legacy_event:
            legacy_event = self.get_event_skeleton(options.use_lite_event)
        else:
            legacy_event = {}

        if isinstance(event, dict):
            legacy_event.update(event)
            compl_event = legacy_event
        else:
            compl_event = legacy_event

        if len(compl_event) > 0:
            self.application.event_writer.add_log_event(compl_event)

    def get_event_skeleton(self, lite_event=False):
        user_agent = self.get_user_agent()
        url = self.request.uri
        try:
            user_agent = user_agent[:128]
            url = url[:128]
        except Exception:
            pass

        ip = self.get_user_ip()
        res = {
            EVENTS_DATE: datetime.now(),
            EVENTS_USER_AGENT: user_agent,
            EVENTS_IP: ip,
        }

        if not lite_event:
            add_info = {
                EVENTS_URL: url,
                EVENTS_SRV_NAME: self.application.server_name,
                EVENTS_METHOD: self.request.method,

            }
            res.update(add_info)

        return res

    @staticmethod
    def default_json_dt(o):
        return default_json_dt(o)
