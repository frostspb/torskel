"""
    Request handler class with auth
"""
from torskel.torskel_handler import TorskelHandler
from torskel.libs.auth.jwt import jwtauth


@jwtauth
class TorskelSecuredHandler(TorskelHandler):
    """
    RequestHandler class with auth
    """
    def __init__(self, application, request, **kwargs):
        super(TorskelHandler, self).__init__(application, request, **kwargs)
