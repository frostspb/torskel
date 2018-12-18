from tornado.options import options
try:
    from tornado.netutil import bind_unix_socket
    no_unix_socket = False
except ImportError:
    no_unix_socket = True
from tornado.httpserver import HTTPServer


def server_init(server):
    """
    Initializing an application on a port or socket depending on the settings
    :param server:
    :return: None
    """
    if options.run_on_socket and not no_unix_socket:

        unix_socket = bind_unix_socket(options.socket_path, 0o666)
        http_server = HTTPServer(server)
        http_server.add_socket(unix_socket)
        server.log_debug(f'Running on socket {options.socket_path}')
    else:

        server.log_debug(f'Running on port {options.port}')
        server.listen(options.port)