from torskel.torskel_app import TorskelServer
from torskel.torskel_handler import TorskelHandler

from tornado.options import options

# You must turn on support redis option

options.use_redis = True

# If you are using redis without a socket file, set use_redis_socket = False

"""
Default redis options:

use_redis_socket=True  For use localhost turn  off this option
redis_socket = '/var/run/redis/redis.sock' Path to redis unix-socket file
redis_min_con=5
redis_max_con=10
If you using password for connecting to redis define redis_psw option
Default redis db=0 for overwrite this - define option redis_db
"""


class RedisApplication(TorskelServer):
    def __init__(self, handlers, **settings):
        super().__init__(handlers, **settings)
        self.greeting = 'Hello redis!'


class RedisHandler(TorskelHandler):
    async def get(self):
        # get hash string
        my_key = self.get_hash_str('my_key')
        await self.set_redis_exp_val(my_key, self.application.greeting, 3000,
                                     convert_to_json=False)
        res = await self.get_redis_val(my_key, from_json=False)
        self.write(res)
        await self.del_redis_val(my_key)
        self.finish()


redis_app = RedisApplication(handlers=[(r"/", RedisHandler)])

if __name__ == '__main__':
    redis_app.init_srv()
