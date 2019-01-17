import datetime
import tornado.web

from tornado.options import options
from torskel.torskel_app import TorskelServer
from torskel.torskel_handler import TorskelHandler
from torskel.torskel_secured_handler import TorskelSecuredHandler

options.define("secret_key", "#MY_SeCrEt_KEy",
               type=str)


class HelloJwtLoginHandler(TorskelHandler):

    async def check_passwd(self, user, password):
        # Your must check password here
        return True

    async def post(self):

        user = self.get_argument('username')
        psw = self.get_argument('username')
        if await self.check_passwd(user, psw):
            encoded = self.encode_jwt_token(
                {
                    'username': user,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(
                        seconds=120
                    )
                }
            )
            response = {'access': encoded}
            self.set_header('Content-Type', 'application/javascript')
            self.write(response)
            self.finish()
        else:

            raise tornado.web.HTTPError(403, 'invalid username')


class HelloJwtSecuredHandler(TorskelSecuredHandler):
    def get(self):
        self.write('Hello, auth success')


hello_app = TorskelServer(handlers=[(r"/login", HelloJwtLoginHandler),
                                    (r"/secured", HelloJwtSecuredHandler)])

if __name__ == '__main__':
    hello_app.init_srv()
    tornado.ioloop.IOLoop.current().start()
