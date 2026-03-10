{
    'name': 'Tool Borrow',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Manage tool and device borrowing with approval workflow',
    'description': """
Tool Borrow Module
==================

This module provides functionality to manage internal tool/device lending:

* Tool management with status tracking (available, borrowed, maintenance)
* Loan request workflow with manager approval
* Support for both internal users and portal users
* Access control with User/Manager/Admin levels
    """,
    'author': 'WoowTech',
    'website': 'https://aiot.woowtech.io/',
    'depends': ['base', 'mail', 'portal'],
    'data': [
        'security/tool_borrow_security.xml',
        'security/ir.model.access.csv',
        'data/tool_sequence_data.xml',
        'data/tool_category_data.xml',
        'views/tool_tool_views.xml',
        'views/tool_loan_views.xml',
        'views/res_users_views.xml',
        'views/menu_views.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
