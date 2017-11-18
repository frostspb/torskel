# -*- coding: utf-8 -*-
import json

try:
    from bson import json_util
except:
    json_util = False
import tornado.gen
from tornado.options import options
from torskel.str_utils import get_hash_str
from torskel.str_utils import is_hash_str


class TorskelHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super(TorskelHandler, self).__init__(application, request, **kwargs)
        # ф-я фильтрации словарей по списку ключей
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
        Возвращает хэш из строки
        :param value: строка
        :param alg: алгоритм. по умолчанию 224
        :return: хэш
        """
        return get_hash_str(value, alg)

    @staticmethod
    def is_hash_str(value):
        """
        Проверяет является ли ф-я хэш строкой любого алгоритма
        :param value:
        :return: boolean
        """
        return is_hash_str(value)

    def get_req_args(self, args_list=None):
        """
        Забирает из реквеста список параметров
        :param args_list: список параметров
        :return: список значений параметров
        """
        if not args_list:
            args_list = []
        return [self.get_argument(x, False) for x in args_list]

    def get_req_args_dict(self):
        """
        Возврщает словарь из всех параметров запроса
        :return: dict
        """

        try:
            res = {k: ''.join([i.decode('utf-8') for i in v]) for k, v in self.request.arguments.items()}
        except:
            self.log_exc('get_req_args_dict failed')
            res = {}
        return res

    def _handle_request_exception(self, e):
        super(TorskelHandler, self)._handle_request_exception(e)
        msg = '''handler classname = %s \n
			   request = %s \n
		       exception = %s\n'''

        self.log_exc(msg % (type(self).__name__, self.request, e))

    def log_debug(self, msg, grep_label=''):
        """
        Дебаг лог
        :param msg: сообщение
        :param grep_label: метка для грепанья
        :return:
        """
        self.application.log_debug(msg, grep_label=grep_label)

    def log_err(self, msg, grep_label=''):
        """
        Логирует ошибку
        :param msg: сообщение
        :param grep_label: метка для грепанья
        :return:
        """
        self.application.log_err(msg, grep_label=grep_label)

    def log_exc(self, msg, grep_label=''):
        """
        Логирует исключение
        :param msg: сообщение
        :param grep_label: метка для грепанья
        :return:
        """
        self.application.log_exc(msg, grep_label)

    async def http_request_get(self, url):
        """
        Делает http запрос, ответ либо json либо xml
        :param url: урл
        :param type_resp: тип ответа
        :return: словарь
        """

        return await self.application.http_request_get(url)

    async def http_request_post(self, url, body):
        """
        Делает http post запрос
        :param url: урл
        :param body: словарь с пост-параметрами
        :return: словарь
        """
        return await self.application.http_request_post(url, body)

    async def set_redis_exp_val(self, key, val, exp, conver_to_json=False):
        if conver_to_json:
            if json_util:
                val = json.dumps(val, default=json_util.default)
            else:
                val = json.dumps(val)

        with await self.application.redis_cnt_pool as redis:
            await redis.connection.execute('set', key, val)
            await redis.connection.execute('expire', key, exp)

        return True

    async def del_redis_val(self, key):

        with await self.application.redis_cnt_pool as redis:
            await redis.connection.execute('del', key)

        return True

    async def get_redis_val(self, key, from_json=True, mail_label=''):
        """
            Достать инфу из редиса
        """
        try:

            with await self.application.redis_cnt_pool as redis:
                r = await redis.connection.execute('get', key)
                redis_val = r.decode('utf-8') if r is not None else r
                if redis_val:
                    if json_util:
                        res = json.loads(redis_val, object_hook=json_util.object_hook) if from_json else redis_val
                    else:
                        res = json.loads(redis_val) if from_json else redis_val
                else:

                    res = None

                return res
        except:
            self.log_exc('get_redis_val failed key = %s label=%s' % (key, mail_label))
            res = None
            return res
