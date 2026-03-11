from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Force-replace menu groups to manager-only after upgrade.

    Odoo's res.groups._apply_group() automatically propagates menu access
    to implied groups when processing security XML. This migration runs
    AFTER all data loading to ensure menus have the correct groups.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    manager_group = env.ref('tool_borrow.group_tool_manager')
    admin_group = env.ref('tool_borrow.group_tool_admin')

    # Manager-only menus
    for menu_xmlid in [
        'tool_borrow.menu_tool_borrow_root',
        'tool_borrow.menu_tool_tools',
        'tool_borrow.menu_tool_loans',
        'tool_borrow.menu_tool_my_loans',
    ]:
        menu = env.ref(menu_xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'groups_id': [(6, 0, [manager_group.id])]})

    # Admin-only menus
    for menu_xmlid in [
        'tool_borrow.menu_tool_config',
    ]:
        menu = env.ref(menu_xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'groups_id': [(6, 0, [admin_group.id])]})
