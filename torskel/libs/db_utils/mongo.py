
import tornado.log
try:
    import motor.motor_tornado
    motor_import = True
except ImportError:
    motor_import = False


from torskel.libs.str_consts import INIT_MONGO_LABEL

logger = tornado.log.gen_log


def get_mongo_pool(mongo_db_name: str=None, mongo_user: str=None,
                   mongo_psw: str=None, mongo_auth_db_name: str=None,
                   mongo_server: str='localhost', mongo_port: int=27017,
                   mongo_min_pool_size: int=5, mongo_max_pool_size: int=10,
                   con_str: str=None, db_name: str=None):
    if motor_import:
        logger.info('Init MongoDB pool...')
        if con_str is None:
            logger.info(f'[{INIT_MONGO_LABEL}] MONGO_SRV={mongo_server} '
                        f'MONGO_PORT={mongo_port}')

            logger.info(f'[{INIT_MONGO_LABEL}]MONGO_USER={mongo_user}')

            logger.info(f'[{INIT_MONGO_LABEL}]'
                        f'MONGO_DB_NAME={mongo_db_name}')

            logger.info(f'[{INIT_MONGO_LABEL}]MONGO_AUTH_DB_NAME'
                        f'={mongo_auth_db_name}')

            logger.info(f'[{INIT_MONGO_LABEL}]MONGO_MIN_POOL_SIZE'
                        f'={mongo_min_pool_size}')

            logger.info(f'[{INIT_MONGO_LABEL}]MONGO_MAX_POOL_SIZE'
                        f'={mongo_max_pool_size}')
            mongo_uri = f'mongodb://{mongo_user}:{mongo_psw}' \
                        f'@{mongo_server}:{mongo_port}' \
                        f'/{mongo_db_name}' \
                        f'?authSource={mongo_auth_db_name}' \
                        f'&minPoolSize={mongo_min_pool_size}' \
                        f'&maxPoolSize={mongo_max_pool_size}'

            res = motor.motor_tornado.MotorClient(mongo_uri)[mongo_db_name]
        else:
            if isinstance(con_str, str) and isinstance(db_name, str):
                res = motor.motor_tornado.MotorClient(con_str)[db_name]
            else:
                res = None
    else:
        raise ModuleNotFoundError('Required package motor is missing')
    return res


async def bulk_mongo_insert(db, collection_name, bulk_list):
    await db[collection_name].insert_many(bulk_list)
