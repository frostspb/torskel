import unittest
import re
import hashlib
from torskel.str_utils import get_hash_str
from torskel.str_utils import is_hash_str
from torskel.str_utils import valid_conversion


class TestStrUtils(unittest.TestCase):
    def setUp(self):
        self.hash_sha224_tmpl = re.compile(r"\b([a-f\d]{56}|[A-F\d]{56})\b")
        self.all_hash_tmpl = re.compile(r"^(?:[a-fA-F\d]{32,40})$|^(?:[a-fA-F\d]{52,60})$|^(?:[a-fA-F\d]{92,100})$")
        self.test_str = 'test me'
        self.test_hash_res = hashlib.sha224(self.test_str.encode('utf-8')).hexdigest()
        self.test_hash = '68df004a144aa21f31047e0635c246c990ea2a373c35cedfcac53966'

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


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    unittest.main(testRunner=runner)
