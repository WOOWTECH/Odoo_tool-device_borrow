from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    tool_borrow_access = fields.Selection([
        ('user', 'User'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ], string='Tool Borrow Access', groups='base.group_system')

    @api.onchange('tool_borrow_access')
    def _onchange_tool_borrow_access(self):
        """Update groups based on tool_borrow_access selection"""
        self._update_tool_borrow_groups()

    def _update_tool_borrow_groups(self):
        """Sync groups with tool_borrow_access field"""
        group_user = self.env.ref('tool_borrow.group_tool_user', raise_if_not_found=False)
        group_manager = self.env.ref('tool_borrow.group_tool_manager', raise_if_not_found=False)
        group_admin = self.env.ref('tool_borrow.group_tool_admin', raise_if_not_found=False)

        if not all([group_user, group_manager, group_admin]):
            return

        all_groups = group_user | group_manager | group_admin

        for user in self:
            # Remove all tool borrow groups first
            user.groups_id = [(3, g.id) for g in all_groups]

            # Add appropriate group based on selection
            if user.tool_borrow_access == 'user':
                user.groups_id = [(4, group_user.id)]
            elif user.tool_borrow_access == 'manager':
                user.groups_id = [(4, group_manager.id)]
            elif user.tool_borrow_access == 'admin':
                user.groups_id = [(4, group_admin.id)]

    def write(self, vals):
        res = super().write(vals)
        if 'tool_borrow_access' in vals:
            self._update_tool_borrow_groups()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users.filtered(lambda u: u.tool_borrow_access)._update_tool_borrow_groups()
        return users
