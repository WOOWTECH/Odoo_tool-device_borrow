from odoo.addons.web.controllers.action import Action
from odoo.http import request, route


class ToolBorrowAction(Action):

    @route()
    def load(self, action_id, context=None):
        result = super().load(action_id, context=context)
        if result and result.get('groups_id'):
            user_group_ids = set(request.env.user.groups_id.ids)
            if not user_group_ids.intersection(result['groups_id']):
                return False
        return result
