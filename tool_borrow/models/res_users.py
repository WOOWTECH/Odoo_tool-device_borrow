from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    tool_borrow_access = fields.Selection([
        ('no_access', 'No Access'),
        ('user', 'User'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ], string='Tool Borrow Access', default='no_access', required=True)

    def init(self):
        """Backfill any NULL tool_borrow_access values to 'no_access' on module upgrade."""
        self.env.cr.execute(
            "UPDATE res_users SET tool_borrow_access = 'no_access' WHERE tool_borrow_access IS NULL"
        )

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
            access_val = vals['tool_borrow_access']
            group_cmds = self._get_tool_borrow_group_commands(access_val)
            if group_cmds:
                # Split portal vs internal users to avoid user type constraint violation
                portal_users = self.filtered(lambda u: u.share)
                internal_users = self - portal_users

                if portal_users:
                    # Save field value only, no group commands for portal users
                    super(ResUsers, portal_users).write(vals)
                if internal_users:
                    internal_vals = dict(vals, groups_id=list(vals.get('groups_id', [])) + group_cmds)
                    super(ResUsers, internal_users).write(internal_vals)
                return True
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            access_val = vals.get('tool_borrow_access')
            if access_val and access_val != 'no_access':
                # Portal users are identified by share=True, which comes from
                # not having base.group_user. Check groups_id for portal indicator.
                is_portal = self._is_portal_vals(vals)
                if not is_portal:
                    group_cmds = self._get_tool_borrow_group_commands(access_val)
                    if group_cmds:
                        existing = vals.get('groups_id', [])
                        vals['groups_id'] = list(existing) + group_cmds
        return super().create(vals_list)

    def _is_portal_vals(self, vals):
        """Check if vals indicate a portal user based on groups_id commands."""
        group_portal_id = self.env.ref('base.group_portal', raise_if_not_found=False)
        if not group_portal_id:
            return False
        for cmd in vals.get('groups_id', []):
            if isinstance(cmd, (list, tuple)) and len(cmd) >= 2:
                if cmd[0] == 4 and cmd[1] == group_portal_id.id:
                    return True
        return False
