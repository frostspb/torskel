"""
Module contains startup methods
"""
# pylint: disable=C0103
import logging
import importlib
from tornado.options import options
from tornado.httpserver import HTTPServer
import tornado.log


# pylint: disable=C0103
logger = tornado.log.gen_log
# hotfix for windows
try:
    from tornado.netutil import bind_unix_socket
    no_unix_socket = False
except ImportError:
    no_unix_socket = True


def _configure_graylog():
    """
    Configuring graylog's handlers
    :return:
    """
    logger.info('Configuring graylog host=%s port=%s', options.graylog_host,
                options.graylog_port)
    try:
        graypy = importlib.import_module('graypy')
        handler = graypy.GELFHandler(
            options.graylog_host,
            options.graylog_port,
            localname=options.srv_name
        )
        logging.getLogger("tornado.access").addHandler(handler)
        logging.getLogger("tornado.application").addHandler(handler)
        logging.getLogger("tornado.general").addHandler(handler)
    except ImportError:
        raise ModuleNotFoundError('Required package graypy is missing')


def server_init(server):
    """
    Initializing an application on a port or socket depending on the settings
    :param server:
    :return: None
    """
    if options.use_graylog:
        _configure_graylog()

    if options.run_on_socket and not no_unix_socket:

        unix_socket = bind_unix_socket(options.socket_path, 0o666)
        http_server = HTTPServer(server)
        http_server.add_socket(unix_socket)
        server.log_info(f'Running on socket {options.socket_path}')
    else:

        server.log_info(f'Running on port {options.port}')
        server.listen(options.port)
