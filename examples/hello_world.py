#import asyncio
from torskel.torskel_app import TorskelServer
from torskel.torskel_handler import TorskelHandler
import tornado.web


class HelloHandler(TorskelHandler):
	def get(self):
		self.write('Hello World!')
		# write debug msg to log file
		self.log_debug('This is log msg!!!!')
		self.finish()

hello_app = TorskelServer(handlers=[(r"/", HelloHandler)])

if __name__ == '__main__':
	hello_app.listen(8888)
	tornado.ioloop.IOLoop.instance().start()
