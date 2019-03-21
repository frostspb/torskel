"""
Module contains startup methods
"""
# pylint: disable=C0103
import logging
import platform
import importlib
import tornado
import tornado.log
try:
    from tornado.netutil import bind_unix_socket
    no_unix_socket = False
except ImportError:
    no_unix_socket = True
from tornado.options import options
from tornado.httpserver import HTTPServer

import torskel


# pylint: disable=C0103
logger = tornado.log.gen_log
# hotfix for windows


def _configure_graylog():
    """
    Configuring graylog's handlers
    :return:
    """
    logger.info('Configuring graylog host=%s port=%s', options.graylog_host,
                options.graylog_port)
    try:
        graypy = importlib.import_module('graypy')
        if graypy.__version__[0] < 1:
            handler = graypy.GELFHandler(
                options.graylog_host,
                options.graylog_port,
                localname=options.srv_name
            )
        else:
            handler = graypy.GELFUDPHandler(
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
    logger.info('')
    logger.info('Starting %s v%s', server.server_name, server.server_version)
    logger.info('')
    logger.info('======== Environment info ======== ')
    logger.info('   Python v%s', platform.python_version())
    logger.info('   Tornado v%s', tornado.version)
    logger.info('   Torskel v%s', torskel.version)
    logger.info('   %s %s ', platform.system(), platform.release())
    logger.info('================================== ')

    if options.use_graylog:
        _configure_graylog()

    if options.run_on_socket and not no_unix_socket:

        unix_socket = bind_unix_socket(options.socket_path, 0o666)
        http_server = HTTPServer(server)
        http_server.add_socket(unix_socket)
        logger.info('Running on socket %s', options.socket_path)
    else:

        logger.info('Running on port %s', options.port)
        server.listen(options.port)
