# -*- coding: utf-8 -*-
import hashlib
import re
import pickle
import ipaddress

hash_sha224_tmpl = re.compile(r"\b([a-f\d]{56}|[A-F\d]{56})\b")
all_hash_tmpl = re.compile(r"^(?:[a-fA-F\d]{32,40})$|^(?:[a-fA-F\d]{52,60})$|^(?:[a-fA-F\d]{92,100})$")
mac_address = re.compile(r"[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$")


def is_valid_ip(ip):
    """
    Validate ip address
    :param ip: ip address
    :return: boolean
    """
    res = False
    if isinstance(ip, str):
        try:
            ipaddress.ip_address(ip)
            res = True
        except ValueError:
            res = False
    return res


def is_valid_mac(mac):
    """
    Validate mac address
    :param mac:
    :return: boolean
    """
    res = False
    if isinstance(mac, str):
        if len(mac) > 0:
            try:
                res = mac_address.match(mac) is not None
            except Exception:
                res = False
    return res


def chr_set_null(chr_value):
    """sql util function"""
    return "null" if chr_value is None or not chr_value else ''.join(("'", chr_value, "'"))


def int_set_null(int_value):
    """sql util function"""
    return "null" if int_value is None else str(int_value)


def valid_conversion(val, type_to_convert):
    """
    Checking whether it is possible to convert val to the specified type
    :param val: value
    :param type_to_convert: type
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
    Return hash from string
    :param value: string
    :param alg: algorithm, default sha224
    :return: hash
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
    Checks whether the string is a hash of any algorithm
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


def pack_iters(val):
    """
    Packs the iterated type into a string
    :param val:
    :return: str
    """

    try:
        if isinstance(val, (dict, list, tuple, enumerate)):
            res = pickle.dumps(val)
        else:
            res = val
    except pickle.PicklingError:
        res = None

    return res


def unpack_iters(val):
    """
    Extracts a string into an iterated type
    :param val:
    :return: iter
    """

    try:
        res = pickle.loads(val)
    except pickle.UnpicklingError:
        res = None
    return res
