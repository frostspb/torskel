
from tornado.options import options

import motor.motor_tornado

options.define("db_server", default='localhost', type=str)
options.define("db_port", default=27017, type=int)
options.define("db_name", default='torskel_db', type=str)
options.define("db_auth_name", default='torskel_db', type=str)
options.define("db_user", default='torskel', type=str)
options.define("db_psw",  default='torskelS5ab80', type=str)
options.define("db_min_pool_size", default=5, type=int)
options.define("db_max_pool_size", default=10, type=int)





mongo_uri = f'mongodb://{options.db_user}:{options.db_psw}@{options.db_server}:{options.db_port}' \
                     f'/{options.db_name}?authSource={options.db_auth_name}' \
                     f'&minPoolSize={options.db_min_pool_size}&maxPoolSize={options.db_max_pool_size}'

mongo_pool = motor.motor_tornado.MotorClient(mongo_uri)['torskel_db']
