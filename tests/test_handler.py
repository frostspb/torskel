import unittest, os, os.path, sys, urllib

import tornado.options
from tornado.options import options
from tornado.testing import AsyncHTTPTestCase


APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(APP_ROOT, '..'))



from torskel.torskel_app import TorskelServer
from torskel.torskel_handler import TorskelHandler

#python -m tornado.test.runtests tests/test_handler.py


class TestHandlerBase(AsyncHTTPTestCase):
    def setUp(self):
        class TestPage(TorskelHandler):
            def get(self):
                self.write('Hi')
                self.finish()
        handlers = [
            (r"/", TestPage),

        ]

        self.app = TorskelServer(handlers, root_dir=os.path.dirname(__file__))
        super(TestHandlerBase, self).setUp()

    def get_app(self):

        return self.app      # this is the global app that we created above.

    def get_http_port(self):
        return options.port


class TestBucketHandler(TestHandlerBase):
    def test_get_req(self):
        response = self.fetch(
            '/',
            method='GET',
            follow_redirects=False)
        self.assertEqual(response.code, 200)
