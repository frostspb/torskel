# -*- coding: utf-8 -*-
import hashlib
import re


hash_sha224_tmpl = re.compile(r"\b([a-f\d]{56}|[A-F\d]{56})\b")
all_hash_tmpl = re.compile(r"^(?:[a-fA-F\d]{32,40})$|^(?:[a-fA-F\d]{52,60})$|^(?:[a-fA-F\d]{92,100})$")


def valid_conversion(val, type_to_convert):
    """
    Проверяе можно ли конверить val в указанный тип
    :param val: значение
    :param type_to_convert: тип
    :return: boolean
    """

    if isinstance(type_to_convert, type):
        try:
            val = type_to_convert(val)
            res = True
        except ValueError:
            res = False

    else:
        raise TypeError
    return res


def get_hash_str(value, alg='sha224'):
    """
    Возвращает хэш из строки
    :param value: строка
    :param alg: алгоритм. по умолчанию 224
    :return: хэш
    """
    res = None

    try:
        if isinstance(value, str):
            res = getattr(hashlib, alg)(value.encode('utf-8')).hexdigest()
    except:
        pass

    return res


def is_hash_str(value):
    """
    Проверяет является ли ф-я хэш строкой любого алгоритма
    :param value:
    :return: boolean
    """
    res = False
    if isinstance(value, str):
        if len(value) > 0:
            try:
                res = all_hash_tmpl.match(value) is not None
            except Exception:
                res = False
    return res


