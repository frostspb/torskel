import os.path
import sys

from tornado.options import options
from tornado.testing import AsyncHTTPTestCase
from torskel.torskel_app import TorskelServer
from tests.app_handlers import TestPage

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(APP_ROOT, '..'))

# python -m tornado.test.runtests tests/test_handler.py


class TestHandlerBase(AsyncHTTPTestCase):
    def setUp(self):

        handlers = [
            (r"/", TestPage),

        ]

        self.app = TorskelServer(handlers)
        super(TestHandlerBase, self).setUp()

    def get_app(self):

        return self.app

    def get_http_port(self):
        return options.port


class TestBucketHandler(TestHandlerBase):
    def test_get_req(self):
        response = self.fetch(
            '/',
            method='GET',
            follow_redirects=False)

        self.assertEqual(response.code, 200)
