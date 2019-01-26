"""
Module contains functions for mongodb
"""
import importlib
import tornado.log

from torskel.libs.str_consts import INIT_MONGO_LABEL


# pylint: disable=C0103
logger = tornado.log.gen_log


# pylint: disable=W1203
def get_mongo_pool(**kwargs):
    """
    Create connections pool to mongo
    :param kwargs:
    :return:
    """
    mongo_db_name = kwargs.get('mongo_db_name', None)
    mongo_user = kwargs.get('mongo_user', None)
    mongo_psw = kwargs.get('mongo_psw', None)
    mongo_auth_db_name = kwargs.get('mongo_auth_db_name', None)
    mongo_server = kwargs.get('mongo_server', 'localhost')
    mongo_port = kwargs.get('mongo_port', 27017)
    mongo_min_pool_size = kwargs.get('mongo_min_pool_size', 5)
    mongo_max_pool_size = kwargs.get('mongo_max_pool_size', 10)
    con_str = kwargs.get('con_str', None)
    db_name = kwargs.get('db_name', None)

    try:
        motor = importlib.import_module('motor')
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
    except ImportError:
        raise ModuleNotFoundError('Required package motor is missing')
    return res


async def bulk_mongo_insert(db, collection_name, bulk_list):
    """
    Bulk insert into collection
    :param db: database name
    :param collection_name:  collection name
    :param bulk_list: list of documents
    :return:
    """
    await db[collection_name].insert_many(bulk_list)
