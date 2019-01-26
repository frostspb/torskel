"""
Module with JWT functionality
"""

import jwt
import tornado.log

JWT_DEFAULT_OPTIONS = {
    'verify_signature': True,
    'verify_exp': True,
    'verify_nbf': False,
    'verify_iat': True,
    'verify_aud': False
}
DEFAULT_ALGORITM = 'HS256'
INVALID_AUTH_HEADER = "Invalid header authorization"
RESULT_KEY = 'result'
MESSAGE_KEY = 'message'
TOKEN_KEY = 'token'
TOKEN_INFO_KEY = 'token_info'
AUTH_RES_FAIL = {RESULT_KEY: False, MESSAGE_KEY: INVALID_AUTH_HEADER}
AUTH_RES_GOOD = {RESULT_KEY: True, MESSAGE_KEY: ''}
INVALID_TOKEN = {RESULT_KEY: False, MESSAGE_KEY: 'Invalid Token'}
logger = tornado.log.gen_log  # pylint: disable=C0103


# pylint: disable=W0703
def jwt_decode(token: str, secret_key: str, options: dict = None) -> dict:
    """
    Decode JWT token
    :param token:
    :param secret_key:
    :param options:
    :return:
    """
    res = {RESULT_KEY: True, MESSAGE_KEY: ''}
    if options is None:
        options = JWT_DEFAULT_OPTIONS
        try:

            res.update(jwt.decode(token, secret_key, options=options))
        except Exception:
            logger.exception('jwt_decode failed')
            res[RESULT_KEY] = False

    else:
        res[RESULT_KEY] = False
    return res


def jwt_encode(secret_key, payload: dict = None,
               algoritm: str = DEFAULT_ALGORITM):
    """
    encode JWT
    :param secret_key:
    :param payload:
    :param algoritm:
    :return:
    """
    res = jwt.encode(payload=payload, key=secret_key, algorithm=algoritm,
                     ).decode("utf-8")
    return res


def validate_token(auth_header):
    """
    Validate access token
    :param auth_header:
    :return:
    """
    res = AUTH_RES_GOOD
    if auth_header:
        try:
            parts = auth_header.split()
            if parts[0].lower() != 'bearer':
                res = AUTH_RES_FAIL

            elif len(parts) == 1:
                res = AUTH_RES_FAIL
            elif len(parts) > 2:
                res = AUTH_RES_FAIL
            else:
                res[TOKEN_KEY] = parts[1]
        except IndexError:
            logger.exception('_validate_token failed')
            res = INVALID_TOKEN
        except KeyError:
            logger.exception('_validate_token failed')
            res = INVALID_TOKEN
    else:
        res = AUTH_RES_FAIL
    return res


# pylint: disable=W0212
# pylint: disable=W0703
def jwtauth(handler_class):
    """
        Class decorator to check for authorization
    """

    # pylint: disable=W0613

    def wrap_execute(handler_execute):
        def require_auth(handler, kwargs):

            auth = handler.request.headers.get('Authorization')
            token_validation_res = validate_token(auth)

            if token_validation_res.get(RESULT_KEY, False):

                token = token_validation_res.get(TOKEN_KEY)
                try:

                    res = jwt_decode(
                        token, handler.application.get_secret_key()
                    )

                    if not res.get(RESULT_KEY):
                        handler._transforms = []
                        handler.set_status(401)
                        handler.write("Missing authorization")
                        handler.finish()

                except Exception:

                    handler._transforms = []
                    handler.set_status(401)
                    handler.write("Missing authorization")
                    handler.finish()

            else:
                handler._transforms = []
                handler.set_status(401)
                handler.write("Missing authorization")
                handler.finish()

            return True

        def _execute(self, transforms, *args, **kwargs):

            try:
                require_auth(self, kwargs)
            except Exception:
                return False

            return handler_execute(self, transforms, *args, **kwargs)

        return _execute

    handler_class._execute = wrap_execute(handler_class._execute)
    return handler_class
