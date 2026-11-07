from odoo.tests.common import new_test_user


class ToolBorrowTestMixin:
    """Shared fixtures: one portal user, one internal user, one manager and
    a couple of available tools."""

    @classmethod
    def _setup_tool_borrow_fixtures(cls):
        cls.portal_user = new_test_user(
            cls.env, login='tb_portal', groups='base.group_portal',
            name='TB Portal')
        cls.internal_user = new_test_user(
            cls.env, login='tb_internal', groups='base.group_user',
            name='TB Internal')
        cls.manager = new_test_user(
            cls.env, login='tb_manager',
            groups='base.group_user,tool_borrow.group_tool_manager',
            name='TB Manager')
        cls.in_service = cls.env.ref('tool_borrow.tool_stage_in_service')
        Tool = cls.env['tool.tool']
        cls.tool = Tool.create({
            'name': 'TB Drill', 'code': 'TB-001', 'stage_id': cls.in_service.id,
        })
        cls.tool2 = Tool.create({
            'name': 'TB Saw', 'code': 'TB-002', 'stage_id': cls.in_service.id,
        })
        cls.archived_tool = Tool.create({
            'name': 'TB Archived Hammer', 'code': 'TB-003',
            'stage_id': cls.in_service.id, 'active': False,
        })
