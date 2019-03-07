from torskel.torskel_app import TorskelServer
from torskel.torskel_handler import TorskelHandler


class HelloHttpHandler(TorskelHandler):
    async def get(self):
        res = await self.http_request_get('http://example.com')
        self.write(res)
        self.finish()


hello_http_app = TorskelServer(handlers=[(r"/", HelloHttpHandler)])

if __name__ == '__main__':
    hello_http_app.init_srv()
