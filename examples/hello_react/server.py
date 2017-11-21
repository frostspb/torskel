import tornado.web
import os
from tornado.web import url
from tornado.options import options, define
from torskel.torskel_app import TorskelServer
from torskel.torskel_handler import TorskelHandler

settings = {}

options.define('use_reactjs', default=True, help='use reactjs', type=bool)
options.define("react_assets_file", default='webpack-assets.json', type=str)


# based on https://github.com/ideletemyself/tornado-react-webpack-boilerplate

class MainHandler(TorskelHandler):
    def get(self):
        self.react_render('index.html')
        self.finish()

handlers = [
    url(r"/", MainHandler, name="IndexPage"),

]


class HelloReactApplication(TorskelServer):
    def __init__(self, handlers,  **settings):
        super().__init__(handlers,  **settings)


hello_react = HelloReactApplication(handlers, root_dir=os.path.dirname(__file__), **settings)

if __name__ == "__main__":
    hello_react.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
