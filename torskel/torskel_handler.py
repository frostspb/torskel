# -*- coding: utf-8 -*-
import json

try:
    from bson import json_util
except ImportError:
    json_util = False

import tornado.gen
from tornado.options import options
from torskel.str_utils import get_hash_str
from torskel.str_utils import is_hash_str


class TorskelHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super(TorskelHandler, self).__init__(application, request, **kwargs)
        # filter dict by list of keys
        self.filter_dict = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])

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
            res = {k: ''.join([i.decode('utf-8') for i in v]) for k, v in self.request.arguments.items()}
        except:
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

    def log_debug(self, msg, grep_label=''):
        """
        Log debug message
        :param msg: message
        :param grep_label: label for grep
        :return:
        """
        self.application.log_debug(msg, grep_label=grep_label)

    def log_err(self, msg, grep_label=''):
        """
        Log error
        :param msg: message
        :param grep_label: label for grep
        :return:
        """
        self.application.log_err(msg, grep_label=grep_label)

    def log_exc(self, msg, grep_label=''):
        """
        Log exception
        :param msg: message
        :param grep_label: label for grep
        :return:
        """
        self.application.log_exc(msg, grep_label)

    async def http_request_get(self, url, from_json=False):
        """
        async http request. Method GET
        :param url: url
        :param from_json: boolean, convert response to dict
        :return: response
        """

        return await self.application.http_request_get(url, from_json)

    async def http_request_post(self, url, body, from_json=False):
        """
        async http request. Method POST
        :param url: url
        :param body: dict with POST-params
        :param from_json: boolean, convert response to dict
        :return: response
        """
        return await self.application.http_request_post(url, body, from_json)

    async def set_redis_exp_val(self, key, val, exp, convert_to_json=False, use_json_utils=False):
        """
        Write value to redis
        :param key: key
        :param val: value
        :param exp: Expire time in seconds
        :param convert_to_json: bool
        :param use_json_utils: bool use json utils from bson
        """
        await self.application.set_redis_exp_val(key, val, exp, convert_to_json, use_json_utils)

    async def del_redis_val(self, key):
        """
        delete value from redis by key
        :param key: key

        """
        await self.application.del_redis_val(key)

    async def get_redis_val(self, key, from_json=True, use_json_utils=False):
        """
        get value from redis by key
        :param key: key
        :param from_json: loads from json
        :param use_json_utils: bool use json utils from bson
        :return: value
        """
        res = await self.application.get_redis_val(key, from_json, use_json_utils)
        return res
