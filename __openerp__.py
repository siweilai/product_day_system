# -*- coding: utf-8 -*-


{
    'name': u'odoo8.0 产品 月一次,加权平均',
    'summary': u'加权平均',
    'category': 'amos',
    'sequence': 0,
    'author': 'Amos',
    'website': 'http://www.odoo.pw',
    'depends': ['base', 'product', 'stock','odoo8_model','account' ],
    'version': '0.1',
    'data': [
        'view/product_monthly.xml',
        'view/product_monthly_task_timer.xml',
        'product_monthly_statistics.xml',
        'product_pool.xml',
        'product_monthly_price_changes_view.xml',
        'product_product.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
""",
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
