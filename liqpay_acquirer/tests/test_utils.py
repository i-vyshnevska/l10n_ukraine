# -*- coding: utf-8 -*-

import base64,hashlib

from odoo.tests.common import SavepointCase
from ..utils import utils


class TestUtils(SavepointCase):

    post_install = True
    at_install = False

    def test_to_unicode(self):
        """
            Test if to_unicode method really converts strings to unicode
        """
        test_string = 'SDF'
        result_string = utils.to_unicode(test_string)
        self.assertIsInstance(result_string, unicode)

    def test_make_signature(self):
        """
            Tested method should concatenate its *args and return sha1 of
            resulting string
        """

        s1, s2, s3 = 's1', 's2', 's3'

        # Test with precoded test data
        hash_result = 'TBTmgscUGvwjIW+lIEkXjOejKcc='
        self.assertEquals(hash_result, utils.make_signature(s1, s2, s3))

        # Test with dynamic encoding
        concatenated_string = ''.join((s1, s2, s3))
        result = base64.b64encode(hashlib.sha1(concatenated_string).digest())
        self.assertEquals(result, utils.make_signature(s1, s2, s3))

