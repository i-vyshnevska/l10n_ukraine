# -*- coding: utf-8 -*-

import base64
import json

from odoo.tests.common import SavepointCase

from ..utils.utils import make_signature


class TestAcquirerLiqPay(SavepointCase):

    post_install = True
    at_install = False

    def setUp(self):
        super(TestAcquirerLiqPay, self).setUp()

        self.liqpay_acquirer = self.env['payment.acquirer'].search(
            [('provider', '=', 'liqpay')], limit=1)

        self.amount = 3
        self.currency = self.env['res.currency'].search([('name', '=', 'UAH')])
        self.reference = 'SO228'

        self.transaction_values = {
            'amount': self.amount,
            'currency': self.currency,
            'reference': self.reference,
            'billing_partner_name': 'First Name',
            'billing_partner_city': 'Gutentag',
            'billing_partner_address': 'Troeshina, 18',
            'billing_partner_zip': '1337',
        }

    def test_liqpay_form_generate_values(self):

        result = self.liqpay_acquirer.liqpay_form_generate_values(
            self.transaction_values)

        self.assertIsInstance(result, dict, 'liqpay_form_generate_values '
                                            'method should return dictionary')

        liqpay_data = result.get('liqpay_data', None)
        liqpay_signature = result.get('liqpay_signature', None)

        try:
            decoded_data = base64.b64decode(liqpay_data)
        except TypeError:
            self.fail('Couldn\'t decode liqpay_data dict')

        try:
            received_data = json.loads(decoded_data)
        except TypeError:
            self.fail('Can not parse received json request')

        self.assertEquals(self.liqpay_acquirer.liqpay_public_key,
                          received_data.get('public_key'),
                          'Wrong public key')

        private_key = self.liqpay_acquirer.liqpay_private_key
        generated_sign = make_signature(private_key, liqpay_data, private_key)

        self.assertEquals(generated_sign, liqpay_signature,
                          'Signatures are not equal')

        self.assertEquals(received_data.get('version', None), '3')
        self.assertEquals(received_data.get('public_key', None),
                          self.liqpay_acquirer.liqpay_public_key)
        self.assertEquals(received_data.get('action', None), 'pay')
        self.assertEquals(received_data.get('amount', None), self.amount)
        self.assertEquals(received_data.get('currency', None), 'UAH')
        self.assertEquals(received_data.get('description', None),
                          'Order payment: {}'.format(self.reference))
        self.assertEquals(received_data.get('order_id', None), self.reference)
        self.assertEquals(received_data.get('language', None), 'ru')
        self.assertEquals(received_data.get('sandbox', None),
                          '1' if self.liqpay_acquirer.environment == 'test'
                          else '0')
        self.assertEquals(received_data.get('server_url', None),
                          '{}/liqpay/callback'.format(
                              self.liqpay_acquirer.liqpay_base_url))
        self.assertEquals(received_data.get('result_url', None),
                          '{}/shop/confirmation'.format(
                              self.liqpay_acquirer.liqpay_base_url))

    def test_liqpay_get_form_action_url(self):
        self.assertEquals('https://www.liqpay.ua/api/3/checkout',
                          self.liqpay_acquirer.liqpay_get_form_action_url(),
                          'Wrong LiqPay checkout public API method route')
