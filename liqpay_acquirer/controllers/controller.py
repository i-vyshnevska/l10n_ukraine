# -*- coding: utf-8 -*-

import json
import base64
from datetime import datetime

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

from ..utils.utils import make_signature


class LiqPayController(http.Controller):

    @http.route('/liqpay/callback', type='http', auth='none',
                methods=['POST'], csrf=False)
    def liqpay_callback(self, **post):

        """
            Controller route to accept liqpay callbacks and verify transactions
        :return: True - if everything is fine
                 False - if there were any problems
        """
        pending_statuses = (
            'processing'
            'prepared'
            'wait_bitcoin'
            'wait_secure'
            'wait_accept'
            'wait_lc'
            'hold_wait'
            'cash_wait'
            'wait_qr'
            'wait_sender'
            'wait_card'
            'wait_compensation'
            'invoice_wait'
            'wait_reserve'
        )
        success_statuses = (
            'success',
            'sandbox'
        )
        error_statuses = (
            'error',
            'reversed',
            'failure'
        )

        # Transaction data encoded to base64
        data = post.get('data')

        # sha1 of string {private_key}{data_in_base64}{private_key}
        # we should check it with our private key and verify if our signature
        # would be the same. If so - the transaction data sent is valid
        signature = post.get('signature')

        # Check if there is data in liqpay request
        if data is None:
            transaction_status = 'No data provided'
            return self._failed_transaction(status=transaction_status)

        # Check if there is signature in liqpay request
        if signature is None:
            transaction_status = 'No signature provided'
            return self._failed_transaction(status=transaction_status)

        # Try to decode provided data
        try:
            decoded_data = base64.b64decode(data)
        except TypeError:
            transaction_status = 'Can\'t decode received data'
            return self._failed_transaction(status=transaction_status)

        # Try to convert decoded data to json
        try:
            received_data = json.loads(decoded_data)
        except TypeError:
            transaction_status = 'Can\'t parse received json'
            return self._failed_transaction(data=decoded_data,
                                            status=transaction_status)

        # Find liqpay acquirer
        liqpay_acquirer = request.env['payment.acquirer'].sudo().search(
            [('provider', '=', 'liqpay')], limit=1)

        if len(liqpay_acquirer) == 0:
            transaction_status = 'Can\'t find liqpay acquirer'
            return self._failed_transaction(data=decoded_data,
                                            status=transaction_status)

        private_key = liqpay_acquirer.liqpay_private_key
        public_key = liqpay_acquirer.liqpay_public_key
        received_pub_key = received_data.get('public_key', '')

        # Check if liqpay public key is valid
        if public_key != received_pub_key:
            transaction_status = 'Wrong public key'
            return self._failed_transaction(data=decoded_data,
                                            status=transaction_status)

        # Generate our own signature to verify liqpay signature
        generated_sign = make_signature(private_key, data, private_key)

        # Check if signatures are equal
        if generated_sign != signature:
            transaction_status = 'Wrong signature'
            return self._failed_transaction(data=decoded_data,
                                            status=transaction_status)

        # Check if liqpay transaction action is 'pay'
        action = received_data.get('action', '')
        if action != 'pay':
            transaction_status = 'Wrong action'
            return self._failed_transaction(data=decoded_data,
                                            status=transaction_status)

        # Find all liqpay transactions in odoo backend
        transactions = request.env['payment.transaction'].sudo().search(
            [('acquirer_id', '=', liqpay_acquirer.id)])

        if len(transactions) == 0:
            transaction_status = 'No connected transactions found'
            return self._failed_transaction(data=decoded_data,
                                            status=transaction_status)

        order_id = received_data.get('order_id', '')
        status = received_data.get('status', '')
        acquirer_reference = received_data.get('payment_id', '')

        transaction = transactions.sudo().search(
            [('reference', '=', order_id)])

        # Check if there are more then 1 transaction for this order
        if len(transaction) > 1:
            transaction_status = 'Found more then one connected order'
            return self._failed_transaction(data=decoded_data,
                                            status=transaction_status)

        if len(transaction) < 1:
            transaction_status = 'No connected orders found'
            return self._failed_transaction(data=decoded_data,
                                            status=transaction_status)

        if status in pending_statuses:
            transaction.write({
                'state': 'pending',
                'acquirer_reference': acquirer_reference,
            })
        if status in success_statuses:
            desc = received_data.get('description', '')

            completion_date = received_data.get('completion_date', False)

            transaction.write({
                'state': 'done',
                'acquirer_reference': acquirer_reference,
                'date_validate': completion_date,
                'state_message': desc,
            })
            if transaction.sale_order_id:
                transaction.sale_order_id.with_context(dict(
                    request.context,
                    send_email=True)).action_confirm()

                # IMPORTANT - creates and process invoice only if products
                # invoice policy is "on ordered qty"
                try:
                    # Create invoice
                    invoice_id = transaction.sale_order_id.action_invoice_create()
                    invoice = request.env[
                        'account.invoice'].sudo().browse(invoice_id)

                    # Validate invoice
                    invoice.sudo().action_invoice_open()

                    # Register payment
                    liqpay_journal = request.env.ref(
                        'liqpay_acquirer.account_journal_liqpay')
                    invoice.sudo().with_context(
                        tx_currency_id=transaction.currency_id.id
                    ).pay_and_reconcile(
                        liqpay_journal.sudo(), transaction.amount)
                except UserError:
                    # Invoice wasn't processed
                    transaction.sale_order_id.sudo().message_post(
                        'Invoice wasn\'t created. Check if your products '
                        'invoice policy is set to "on ordered qty"'
                    )

        if status in error_statuses:
            err_desc = received_data.get(
                'err_description',
                'error')
            transaction.write({
                'state': 'error',
                'acquirer_reference': acquirer_reference,
                'state_message': err_desc,
            })

        # Create record in liqpay.journal for this transaction
        request.env['liqpay.journal'].sudo().create({
            'name': transaction.sale_order_id.name,
            'received_data': decoded_data,
            'status': status,
        })
        return 'Transaction processed'

    def _failed_transaction(self, data=None, status=None):
        """
            Method to create liqpay_journal record in odoo backend to
            journal requests that are coming to public controller
        :param data: request data
        :param status: transaction status
        :return:
        """
        request.env['liqpay.journal'].sudo().create({
            'name': 'Failed Transaction at {}'.format(datetime.now()),
            'received_data': data if data else 'No data provided',
            'status': status if status else 'No status provided',
        })
        return 'Transaction failed'
