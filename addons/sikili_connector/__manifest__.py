{
    'name': 'Sikili Connector',
    'version': '18.0.1.0.0',
    'summary': 'Champs de liaison entre l\'app web Sikili et Odoo',
    'author': 'Sikili',
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': ['sale'],
    'data': [
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
