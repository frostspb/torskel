from lib.db_utils import mongo_pool
import asyncio
import os.path
import tornado.ioloop
from tornado.queues import Queue
from tornado.httpserver import HTTPServer
from tornado.netutil import bind_unix_socket
from tornado.options import options
from torskel.torskel_app import TorskelServer
from tornado.web import url
from lib.log_event_controller import TorskelEventLogController
from tornado.options import options
from torskel.torskel_handler import TorskelHandler
from user_agents import parse
from datetime import datetime

DEFAULT_LP_LANG = 'ru'
DEFAULT_INTERNATIONAL_LANG = 'en'


class BaseLPHandler(TorskelHandler):
    """
    Базовый класс, от которого наследуются все хэндлеры логинпейджа.
    """

    def __init__(self, application, request, template_name=None, page_name='',
                 **kwargs):
        super().__init__(application, request, **kwargs)
        self.page_name = page_name
        self.user_lang_strings = None
        self.html_template_name = template_name
        self.session_id = None
        self.user_data = None
        self.user_language = None


        # определить язык пользователя
        try:
            self.user_language = self.get_user_lang_list()[0].upper()
        except IndexError:
            self.user_language = DEFAULT_LP_LANG

    def get(self):
        self.write('Method not allowed')
        self.finish()



    def write_error(self, status_code, **kwargs):
        """
        Кастомный обработчик ошибок. Рендерит свои шаблоны под ошибки
        :param status_code: код ошибки
        :param kwargs:
        :return:
        """

        self.log_debug(status_code, grep_label='STATUS_CODE')
        self.log_debug(kwargs, grep_label='KWARGS')
        try:
            if status_code == 404:
                self.render('errors/404.html', page=None,
                            error_msg='Page not found')
            elif status_code == 500:
                self.render('errors/500.html', page=None,
                            error_msg='Something went wrong. '
                                      'Please, try again later')
            elif status_code == 400:
                self.render('errors/other.html', page=None,
                            error_msg='Invalid argument')
            else:
                self.render('errors/unknown.html', page=None)
        except FileNotFoundError:
            self.log_err('Не найден html-шаблон '
                         'для кастомного обработчика ошибок')
            self.write('System Error')
            self.finish()




    def add_log_event(self, page_name, event_name, event_msg=None, ip=None, mac=None,lp_session_id=None,
                      user_language=None, phone=None, user_url=None):
        user_agent = self.get_user_agent()
        try:
            user_url = user_url[:256]
            user_agent = user_agent[:128]
        except:
            pass

        event = {'page_name': page_name, 'event_name': event_name,
                 'user_agent': user_agent,
                 'date_event': datetime.now()
                }
        self.application.event_writer.add_log_event(event)


class MainPageHandler(BaseLPHandler):
    def get(self):
        self.write('Hello World!')
        # write debug msg to log file
        self.log_debug('This is log msg!!!!')
        self.add_log_event('111', 'xxx')
        self.finish()


handlers = [
    url(r"/", MainPageHandler, name='ROOT'),

]


COUNT_TASK_FOR_LOGWRITER = 5
PERIOD_LOG_WRITER = 100*60




###########################################################################
#                             Настройки                                   #
###########################################################################
options.define("secret-key", '61oETzKdsdaadkL5gEbGeJJFuYh7EQnp2XYTP1o/Vo=',
               type=str)
options.define("srv_name", 'LOCAL', type=str)
options.define("run_on_socket", False, type=bool)
options.define("show_log_event_writer", True, type=bool)
options.define("use_db_logging", True, type=bool)
#tornado.options.parse_config_file(CONF_FILE)

# перезаписать опции, если были опции из командной строки
tornado.options.parse_command_line()

#mongo_pool = db_pool = motor.motor_tornado.MotorClient(MONGO_CON_STR).wf_lp

settings = {
    'cookie_secret': options.secret_key,
    'xsrf_cookies': False,
    'log_db': mongo_pool
}


class WCWFLPServer(TorskelServer):
    def __init__(self, handlers, **settings):
        super().__init__(handlers, root_dir=os.path.dirname(__file__),
                         **settings)

        self.server_name = options.srv_name
        self.log_queue = Queue()
        self.db = settings.get('log_db')
        self.event_writer = TorskelEventLogController(self.db)

    def init_with_loop(self, loop=None) -> type(None):
        super().init_with_loop(loop)
        #todo connect to mongo
        #loop.run_until_complete(self.db.test_collection)


        #res = loop.run_until_complete(self.db.test_collection.insert_one({'1key': '21'}))

    async def write_log_from_queue(self) -> type(None):
        """
        Забирает из очереди задания на Insert логов пользователя
         и выполняет вставку в базу
        """
        await self.event_writer.write_log_from_queue()


def make_app():
    res = WCWFLPServer(handlers, **settings)
    return res


lp_server = make_app()

if __name__ == "__main__":
    ###########################################################################
    #                             Конфигурация                                #
    ###########################################################################
    lp_server.log_debug(f'Starting server {options.srv_name}')
    tornado.ioloop.IOLoop.configure('tornado.platform.asyncio.AsyncIOMainLoop')
    # если указано в конфе - запускаем на сокете
    if options.run_on_socket:
        unix_socket = bind_unix_socket(options.sock_path, 0o666)
        lp_http_server = HTTPServer(lp_server)
        lp_http_server.add_socket(unix_socket)
        lp_server.log_debug(f'Socket {options.port}')
    else:
        lp_server.log_debug(f'Port {options.port}')
        lp_server.listen(options.port)

    ###########################################################################
    #                       Периодические задания                             #
    ###########################################################################
    # стартуем писатель логов
    lp_server.log_debug(f'Starting UserLogWriter with '
                        f'timeout={PERIOD_LOG_WRITER} ms')
    log_writer = tornado.ioloop.PeriodicCallback(
        lp_server.write_log_from_queue,
        PERIOD_LOG_WRITER
    )
    log_writer.start()
    ###########################################################################
    #                            Инициализация                                #
    ###########################################################################
    loop = asyncio.get_event_loop()
    lp_server.log_debug(f'Init with loop...')
    lp_server.init_with_loop(loop)

    loop.run_forever()
