"""
Module with useful string functions
"""
import hashlib
import re
import ipaddress
import datetime

ALL_HASH_RE_TMPL = r"^(?:[a-fA-F\d]{32,40})$|^(?:[a-fA-F\d]{52,60})$|" \
                   r"^(?:[a-fA-F\d]{92,100})$"

# pylint: disable=C0103
hash_sha224_tmpl = re.compile(r"\b([a-f\d]{56}|[A-F\d]{56})\b")
all_hash_tmpl = re.compile(ALL_HASH_RE_TMPL)
mac_address = re.compile('^' + r'[\:\-]'.join(['([0-9a-f]{2})'] * 6) + '$')


def default_json_dt(json_object):
    """
    Formatting date in JSON
    :param json_object:
    :return:
    """
    if isinstance(json_object, (datetime.date, datetime.datetime)):

        res = json_object.isoformat()
    else:
        res = None
    return res


# pylint: disable=C0103
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


# pylint: disable=C0103
def is_valid_mac(mac):
    """
    Validate mac address
    :param mac:
    :return: boolean
    """
    res = False
    if isinstance(mac, str):
        if mac:
            res = mac_address.match(mac.lower()) is not None

    return res


def chr_set_null(chr_value):
    """sql util function"""
    return "null" if chr_value is None or not chr_value else \
        ''.join(("'", chr_value, "'"))


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
            type_to_convert(val)
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
    except UnicodeEncodeError:
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
        if value:
            res = all_hash_tmpl.match(value) is not None

    return res


def is_number(value):
    """
    Checks whether the value is a number
    :param value:
    :return: bool
    """
    try:
        complex(value)
    except ValueError:
        return False

    return True
