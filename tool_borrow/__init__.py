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
        'tool_borrow.menu_tool_my_loans',
    ]:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'groups_id': [(6, 0, [manager_group.id])]})

    for xmlid in ['tool_borrow.menu_tool_config']:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'groups_id': [(6, 0, [admin_group.id])]})
