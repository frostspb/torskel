from torskel import TorskelServer
from torskel import TorskelHandler


class HelloApplication(TorskelServer):
    greeting = 'Hello world'


class HelloHandler(TorskelHandler):
    def get(self):
        self.write(self.application.greeting)
        self.finish()


hello_app = HelloApplication(handlers=[(r"/", HelloHandler)])

if __name__ == '__main__':
    hello_app.init_srv()
