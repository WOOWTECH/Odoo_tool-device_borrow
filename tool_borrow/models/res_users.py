from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    tool_borrow_access = fields.Selection([
        ('user', 'User'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ], string='Tool Borrow Access', groups='base.group_system')

    def _get_tool_borrow_group_commands(self, access_value):
        """Build groups_id commands to sync tool borrow groups atomically."""
        group_user = self.env.ref('tool_borrow.group_tool_user', raise_if_not_found=False)
        group_manager = self.env.ref('tool_borrow.group_tool_manager', raise_if_not_found=False)
        group_admin = self.env.ref('tool_borrow.group_tool_admin', raise_if_not_found=False)

        if not all([group_user, group_manager, group_admin]):
            return []

        target_group_id = {
            'user': group_user.id,
            'manager': group_manager.id,
            'admin': group_admin.id,
        }.get(access_value)

        # Remove all tool borrow groups, then add the target
        cmds = [(3, g.id) for g in (group_user | group_manager | group_admin)]
        if target_group_id:
            cmds.append((4, target_group_id))
        return cmds

    def write(self, vals):
        if 'tool_borrow_access' in vals:
            group_cmds = self._get_tool_borrow_group_commands(vals['tool_borrow_access'])
            if group_cmds:
                existing = vals.get('groups_id', [])
                vals = dict(vals, groups_id=list(existing) + group_cmds)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('tool_borrow_access'):
                group_cmds = self._get_tool_borrow_group_commands(vals['tool_borrow_access'])
                if group_cmds:
                    existing = vals.get('groups_id', [])
                    vals['groups_id'] = list(existing) + group_cmds
        return super().create(vals_list)
