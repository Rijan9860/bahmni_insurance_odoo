{
    'name': "Bahmni Insurance Odoo",
    'version': '1.0',
    'summary': "Bahmni Insurance Odoo",
    'description': """
        Bahmni Insurance Odoo
    """,
    'author': "Rijan Maharjan",
    'website': "",
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/insurance_security.xml',
        'views/menu_view.xml',
        'views/sale_order_view.xml',
        'views/insurance_claim_view.xml'
    ],
    'installable': True,
    'application': True,
    "sequence":-100,
}