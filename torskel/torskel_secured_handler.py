"""
    Request handler class with auth
"""
from torskel.torskel_handler import TorskelHandler
from torskel.libs.auth.jwt import jwtauth


# pylint: disable=W0223
@jwtauth
class TorskelSecuredHandler(TorskelHandler):
    """
    RequestHandler class with auth
    """
