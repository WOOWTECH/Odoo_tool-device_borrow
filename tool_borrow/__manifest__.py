{
    'name': 'Tool Borrow',
    'version': '18.0.1.2.0',
    'category': 'Inventory',
    'summary': 'Manage tool and device borrowing with approval workflow',
    'description': """
Tool Borrow Module
==================

A comprehensive tool and device borrowing management system for Odoo 18.

Key Features
------------
* **Tool Management** — Organize tools by category with status tracking
  (Available / Unavailable / Under Maintenance), auto-generated codes,
  and dynamic properties per category.
* **Loan Workflow with Approval** — Full lifecycle management:
  Draft → Pending → Approved → Borrowed → Returned (or Rejected).
  Managers approve or reject requests; the system updates tool
  availability automatically.
* **Portal Self-Service** — Portal users can browse available tools
  and submit borrow requests directly from the website.
* **Role-Based Access Control** — Four levels per user:
  No Access, User, Manager, Admin.
* **Export-Friendly** — Many2many fields (e.g. Allowed Users) export
  as comma-separated values for clean import/export cycles.

For full documentation, see the README at the repository root.
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
    'post_init_hook': '_post_init_hook',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
