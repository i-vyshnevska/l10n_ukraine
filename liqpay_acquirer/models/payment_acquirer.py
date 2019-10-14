# -*- coding: utf-8 -*-

import base64
import json

from odoo import fields, models, api

from ..utils.utils import make_signature


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('liqpay', 'Liqpay')])
    liqpay_public_key = fields.Char(
        'Liqpay Public Key', required_if_provider='liqpay')
    liqpay_private_key = fields.Char(
        'Liqpay Private Key', required_if_provider='liqpay')
    liqpay_base_url = fields.Char(
        'Base callback url', required_if_provider='liqpay')
    liqpay_server_side =  fields.Char(
        default='https://www.liqpay.ua/api/request',
        help="If you don't sure don't change it",
        string='Server Side', required_if_provider='liqpay')
    liqpay_client_side =  fields.Char(
        default='https://www.liqpay.ua/api/3/checkout',
        help="If you don't sure don't change it",
        string='Client Side', required_if_provider='liqpay')

    def liqpay_form_generate_values(self, values):
        """
            Method to generate values for liqpay acquirer payment
        :param values: values to generate payment from
        :return: updated values dict with:
                liqpay_data - request data in json encoded to base64
                liqpay_signature - {private_key}{data_in_base64}{private_key}
                signature for sending to liqpay for transactions verification
        """

        self.ensure_one()

        base_url = self.liqpay_base_url
        return_url = '{}/shop/confirmation'.format(base_url)
        callback_url = '{}/liqpay/callback'.format(base_url)
        partner_lang = 'ru'

        # Fill in request data for liqpay transaction
        request = {
          'version': '3',
          'public_key': self.liqpay_public_key,
          'action': 'pay',
          'amount': values['amount'],
          'currency': values['currency'] and values['currency'].name or 'UAH',
          'description': 'Order payment: {}'.format(values['reference']),
          'order_id': values['reference'],
          'language': partner_lang,
          'sandbox': '1' if self.environment == 'test' else '',
          'server_url': callback_url,
          'result_url': return_url,
          'sender_first_name': values['billing_partner_name'] or '',
          'sender_city': values['billing_partner_city'] or '',
          'sender_address': values['billing_partner_address'] or '',
          'sender_postal_code': values['billing_partner_zip'] or '',
        }

        # Dump request data to json and encode it to base64
        data = base64.b64encode(json.dumps(request))

        # Make signature for current transaction
        signature = make_signature(
            self.liqpay_private_key, data, self.liqpay_private_key)

        values.update({
            'liqpay_data': data,
            'liqpay_signature': signature,
        })
        return values

    def liqpay_get_form_action_url(self):
        """
        :return: LiqPay checkout API method route
        """
        return self.liqpay_client_side

    @api.multi
    def show_liqpay_journal(self):
        """
        :return: Window action to open liqpay_journal view
        """
        tree_view_id = self.env.ref(
            'liqpay_acquirer.liqpay_journal_tree_view').id
        form_view_id = self.env.ref(
            'liqpay_acquirer.liqpay_journal_form_view').id

        return {
            'name': 'LiqPay journal',
            'view_type': 'form',
            'view_mode': 'tree, form',
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'res_model': 'liqpay.journal',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
        }
