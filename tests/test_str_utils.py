import unittest
import re
import hashlib
from torskel.str_utils import get_hash_str
from torskel.str_utils import is_hash_str
from torskel.str_utils import is_valid_ip
from torskel.str_utils import is_valid_mac


SHA224_TMPL = r"\b([a-f\d]{56}|[A-F\d]{56})\b"
ALL_HASH_TMPL = r"^(?:[a-fA-F\d]{32,40})$|^(?:[a-fA-F\d]{52,60})" \
                r"$|^(?:[a-fA-F\d]{92,100})$"
TEST_HASH = '68df004a144aa21f31047e0635c246c990ea2a373c35cedfcac53966'


class TestStrUtils(unittest.TestCase):
    def setUp(self):
        self.hash_sha224_tmpl = re.compile(SHA224_TMPL)
        self.all_hash_tmpl = re.compile(ALL_HASH_TMPL)
        self.test_str = 'test me'
        self.test_hash_res = hashlib.sha224(
            self.test_str.encode('utf-8')
        ).hexdigest()
        self.test_hash = TEST_HASH

    def test_get_hash_str_tmpl(self):
        res = get_hash_str(self.test_str)
        assert self.hash_sha224_tmpl.match(res), True

    def test_get_hash_str(self):
        res = get_hash_str(self.test_str)
        assert res, self.test_hash_res

    def test_get_hash_str_wrong_type(self):
        res = get_hash_str([111])
        assert res is None

    def test_is_hash_str(self):
        res = is_hash_str(self.test_hash)
        self.assertEqual(res, True)

    def test_is_hash_str_wrong_val(self):
        res = is_hash_str(23423)
        self.assertEqual(res, False)

    def test_valid_ip(self):
        res = is_valid_ip('127.0.0.1')
        self.assertEqual(res, True)

    def test_valid_ip_wrong_val(self):
        res = is_valid_ip('327.0.0.1')
        self.assertEqual(res, False)

    def test_valid_mac(self):
        res = is_valid_mac('00:02:02:34:72:a5')
        self.assertEqual(res, True)

    def test_valid_mac_wrong_val(self):
        res = is_valid_mac('.1')
        self.assertEqual(res, False)


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    unittest.main(testRunner=runner)
