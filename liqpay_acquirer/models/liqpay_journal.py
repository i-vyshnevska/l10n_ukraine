# -*- coding: utf-8 -*-

from odoo import fields, models


class LiqpayJournal(models.Model):
    # should be payment.transaction ?
    _name = 'liqpay.journal'


    name = fields.Char('Transaction name')
    received_data = fields.Text('Data received with request')
    status = fields.Char('Status')
    connected_payer = fields.Many2one(
        'payment.acquirer', string='Connected acquirer',
        default=lambda self: self.env.ref(
            'liqpay_acquirer.payment_acquirer_liqpay'))
