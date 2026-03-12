from . import controllers
from . import models


def _post_init_hook(env):
    """Set menu groups to manager-only after fresh install.

    Odoo's group implied_ids propagation automatically adds implied groups
    to menus. This hook corrects the groups after all data is loaded.
    """
    manager_group = env.ref('tool_borrow.group_tool_manager')
    admin_group = env.ref('tool_borrow.group_tool_admin')

    for xmlid in [
        'tool_borrow.menu_tool_borrow_root',
        'tool_borrow.menu_tool_tools',
        'tool_borrow.menu_tool_loans',
    ]:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'groups_id': [(6, 0, [manager_group.id])]})

    for xmlid in ['tool_borrow.menu_tool_config']:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'groups_id': [(6, 0, [admin_group.id])]})

    # Force-replace action groups to prevent User role from accessing backend via direct URL
    for xmlid in [
        'tool_borrow.tool_tool_action',
        'tool_borrow.tool_loan_action',
    ]:
        action = env.ref(xmlid, raise_if_not_found=False)
        if action:
            action.write({'groups_id': [(6, 0, [manager_group.id])]})

    for xmlid in ['tool_borrow.tool_category_action']:
        action = env.ref(xmlid, raise_if_not_found=False)
        if action:
            action.write({'groups_id': [(6, 0, [admin_group.id])]})

    # Set Odoo admin user to tool_borrow Admin by default
    admin_user = env.ref('base.user_admin', raise_if_not_found=False)
    if admin_user and admin_user.tool_borrow_access != 'admin':
        admin_user.write({'tool_borrow_access': 'admin'})
