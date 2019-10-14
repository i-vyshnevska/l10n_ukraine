# -*- coding: utf-8 -*-
{
    'name': 'liqpay_integration',
    'summary': """
        Liqpay widget integration module
        """,
    'author': 'Camptocamp,Odoo Community Association (OCA)',
    'category': 'Localization',
    'website': 'https://github.com/OCA/l10n-ukraine',
    'version': '10.0.1.0.0',
    'depends': [
        'base',
        'payment',
        'website_sale',
        'account',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/liqpay_button_view.xml',
        'views/payment_acquirer.xml',
        'views/liqpay_journal.xml',
        'data/liqpay_acquirer.xml',
        'data/account_journal.xml',
    ],
}
