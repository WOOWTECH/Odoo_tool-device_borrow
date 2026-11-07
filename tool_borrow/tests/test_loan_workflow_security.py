from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

from .common import ToolBorrowTestMixin


@tagged('post_install', '-at_install', 'tool_borrow')
class TestLoanWorkflowSecurity(ToolBorrowTestMixin, TransactionCase):
    """Finding d3da922fb4ba: regular users must not be able to drive the
    approval workflow by writing/creating tool.loan workflow fields over RPC."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_tool_borrow_fixtures()

    def _own_loan(self, user, tool=None, **vals):
        return self.env['tool.loan'].with_user(user).create(dict({
            'tool_id': (tool or self.tool).id,
            'user_id': user.id,
        }, **vals))

    # ------------------------------------------------------------------
    # write(): protected workflow fields
    # ------------------------------------------------------------------
    def test_portal_cannot_write_state(self):
        loan = self._own_loan(self.portal_user)
        with self.assertRaises(AccessError):
            loan.write({'state': 'approved'})
        loan.action_submit()
        for state in ('approved', 'borrowed', 'returned'):
            with self.assertRaises(AccessError):
                loan.write({'state': state})
        self.assertEqual(loan.state, 'pending')
        self.assertEqual(self.tool.state, 'available')

    def test_internal_cannot_write_approval_fields(self):
        loan = self._own_loan(self.internal_user)
        loan.action_submit()
        now = fields.Datetime.now()
        for vals in (
            {'approved_by': self.manager.id},
            {'approved_date': now},
            {'borrow_date': now},
            {'return_date': now},
            {'request_date': False},
        ):
            with self.subTest(vals=vals), self.assertRaises(AccessError):
                loan.write(vals)
        self.assertFalse(loan.approved_by)
        self.assertTrue(loan.request_date)

    def test_rejected_loan_cannot_be_revived_by_borrower(self):
        loan = self._own_loan(self.portal_user)
        loan.action_submit()
        loan.with_user(self.manager).action_reject()
        with self.assertRaises(AccessError):
            loan.write({'state': 'borrowed'})
        with self.assertRaises(UserError):
            loan.action_reset_to_draft()
        self.assertEqual(loan.state, 'rejected')
        # A manager may still reset a rejected request
        loan.with_user(self.manager).action_reset_to_draft()
        self.assertEqual(loan.state, 'draft')

    def test_unchanged_protected_values_are_accepted(self):
        """Clients re-sending the current value (e.g. a form save) still work."""
        loan = self._own_loan(self.portal_user)
        loan.write({'state': 'draft', 'notes': 'please'})
        self.assertEqual(loan.notes, 'please')

    def test_tool_and_borrower_locked_outside_draft(self):
        loan = self._own_loan(self.internal_user)
        loan.write({'tool_id': self.tool2.id})  # still a draft: allowed
        self.assertEqual(loan.tool_id, self.tool2)
        loan.action_submit()
        with self.assertRaises(AccessError):
            loan.write({'tool_id': self.tool.id})
        with self.assertRaises(AccessError):
            loan.write({'user_id': self.portal_user.id})
        self.assertEqual(loan.tool_id, self.tool2)

    def test_borrower_cannot_hand_draft_to_someone_else(self):
        loan = self._own_loan(self.internal_user)
        with self.assertRaises(AccessError):
            loan.write({'user_id': self.portal_user.id})

    # ------------------------------------------------------------------
    # create(): forced draft
    # ------------------------------------------------------------------
    def test_portal_cannot_create_borrowed_loan(self):
        Loan = self.env['tool.loan'].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Loan.create({
                'tool_id': self.tool.id,
                'user_id': self.portal_user.id,
                'state': 'borrowed',
            })
        self.assertEqual(self.tool.state, 'available')
        self.assertFalse(self.tool.current_borrower_id)

    def test_internal_cannot_create_with_approval_fields(self):
        Loan = self.env['tool.loan'].with_user(self.internal_user)
        with self.assertRaises(AccessError):
            Loan.create({
                'tool_id': self.tool.id,
                'approved_by': self.manager.id,
                'approved_date': fields.Datetime.now(),
            })
        with self.assertRaises(AccessError):
            Loan.create({
                'tool_id': self.tool.id,
                'borrow_date': fields.Datetime.now(),
            })

    def test_create_explicit_draft_is_accepted(self):
        loan = self._own_loan(self.portal_user, state='draft', notes='n')
        self.assertEqual(loan.state, 'draft')

    def test_create_for_another_user_rejected(self):
        with self.assertRaises(AccessError):
            self.env['tool.loan'].with_user(self.internal_user).create({
                'tool_id': self.tool.id,
                'user_id': self.portal_user.id,
            })

    def test_copy_by_borrower_restarts_as_draft(self):
        loan = self._own_loan(self.internal_user)
        loan.action_submit()
        loan.with_user(self.manager).action_approve()
        loan.with_user(self.manager).action_confirm_borrow()
        loan.with_user(self.manager).action_confirm_return()
        dup = loan.copy()
        self.assertEqual(dup.state, 'draft')
        self.assertFalse(dup.approved_by)
        self.assertFalse(dup.borrow_date)
        self.assertFalse(dup.return_date)
        self.assertEqual(self.tool.state, 'available')

    def test_cannot_create_loan_on_archived_tool(self):
        with self.assertRaises(UserError):
            self._own_loan(self.portal_user, tool=self.archived_tool)

    # ------------------------------------------------------------------
    # Legitimate workflow keeps working
    # ------------------------------------------------------------------
    def test_full_workflow_portal_borrower(self):
        loan = self._own_loan(self.portal_user, notes='for site visit')
        self.assertEqual(loan.state, 'draft')
        loan.action_submit()
        self.assertEqual(loan.state, 'pending')
        self.assertTrue(loan.request_date)

        as_manager = loan.with_user(self.manager)
        as_manager.action_approve()
        self.assertEqual(loan.state, 'approved')
        self.assertEqual(loan.approved_by, self.manager)
        self.assertTrue(loan.approved_date)

        as_manager.action_confirm_borrow()
        self.assertEqual(loan.state, 'borrowed')
        self.assertEqual(self.tool.state, 'borrowed')
        self.assertEqual(self.tool.current_borrower_id, self.portal_user)

        as_manager.action_confirm_return()
        self.assertEqual(loan.state, 'returned')
        self.assertTrue(loan.return_date)
        self.assertEqual(self.tool.state, 'available')

    def test_borrower_can_withdraw_pending_request(self):
        loan = self._own_loan(self.internal_user)
        loan.action_submit()
        loan.action_reset_to_draft()
        self.assertEqual(loan.state, 'draft')
        self.assertFalse(loan.request_date)
        loan.action_submit()
        self.assertEqual(loan.state, 'pending')

    def test_manager_actions_still_restricted(self):
        loan = self._own_loan(self.portal_user)
        loan.action_submit()
        with self.assertRaises(UserError):
            loan.action_approve()
        loan.with_user(self.manager).action_reject()
        self.assertEqual(loan.state, 'rejected')

    def test_manager_can_write_and_create_workflow_fields(self):
        loan = self.env['tool.loan'].with_user(self.manager).create({
            'tool_id': self.tool.id,
            'user_id': self.internal_user.id,
            'state': 'pending',
            'request_date': fields.Datetime.now(),
        })
        self.assertEqual(loan.state, 'pending')
        loan.with_user(self.manager).write({'notes': 'ok', 'state': 'rejected'})
        self.assertEqual(loan.state, 'rejected')

    def test_submit_requires_own_loan_or_manager(self):
        other = self.env['tool.loan'].with_user(self.manager).create({
            'tool_id': self.tool.id,
            'user_id': self.portal_user.id,
        })
        with self.assertRaises(AccessError):
            other.with_user(self.internal_user).action_submit()
        other.with_user(self.manager).action_submit()
        self.assertEqual(other.state, 'pending')

    def test_submit_rejected_for_archived_tool(self):
        loan = self._own_loan(self.portal_user)
        self.tool.active = False
        with self.assertRaises(UserError):
            loan.action_submit()
        self.assertEqual(loan.state, 'draft')

    # ------------------------------------------------------------------
    # create(): default sources cannot fill protected fields
    # (d3da922fb4ba, round 2 -- default_<field> context / ir.default)
    # ------------------------------------------------------------------
    def _forged_defaults_context(self):
        now = fields.Datetime.to_string(fields.Datetime.now())
        return {
            'default_state': 'borrowed',
            'default_approved_by': self.manager.id,
            'default_approved_date': now,
            'default_borrow_date': now,
            'default_return_date': now,
            'default_request_date': now,
        }

    def _assert_clean_draft(self, loan, user):
        self.assertEqual(loan.state, 'draft')
        self.assertEqual(loan.user_id, user)
        for fname in ('approved_by', 'approved_date', 'borrow_date',
                      'return_date', 'request_date'):
            self.assertFalse(loan[fname], '%s must not be forged' % fname)

    def _assert_clean_after_submit(self, loan):
        loan.action_submit()
        self.assertEqual(loan.state, 'pending')
        self.assertTrue(loan.request_date)
        for fname in ('approved_by', 'approved_date', 'borrow_date',
                      'return_date'):
            self.assertFalse(loan[fname], '%s must not be forged' % fname)

    def test_context_defaults_cannot_forge_protected_fields(self):
        for user in (self.portal_user, self.internal_user):
            with self.subTest(user=user.login):
                loan = self.env['tool.loan'].with_user(user).with_context(
                    **self._forged_defaults_context()
                ).create({'tool_id': self.tool.id})
                self._assert_clean_draft(loan, user)
                self._assert_clean_after_submit(loan)
                loan.action_reset_to_draft()
                loan.sudo().unlink()
        self.assertEqual(self.tool.state, 'available')

    def test_context_default_borrower_is_ignored_for_non_manager(self):
        loan = self.env['tool.loan'].with_user(self.internal_user).with_context(
            default_user_id=self.portal_user.id,
        ).create({'tool_id': self.tool.id})
        self.assertEqual(loan.user_id, self.internal_user)

    def test_user_scoped_ir_default_cannot_forge_protected_fields(self):
        IrDefault = self.env['ir.default'].with_user(self.internal_user)
        now = fields.Datetime.to_string(fields.Datetime.now())
        IrDefault.set('tool.loan', 'approved_by', self.manager.id, user_id=True)
        IrDefault.set('tool.loan', 'borrow_date', now, user_id=True)
        IrDefault.set('tool.loan', 'state', 'borrowed', user_id=True)
        loan = self.env['tool.loan'].with_user(self.internal_user).create({
            'tool_id': self.tool.id,
        })
        self._assert_clean_draft(loan, self.internal_user)
        self._assert_clean_after_submit(loan)

    def test_manager_context_defaults_still_apply(self):
        loan = self.env['tool.loan'].with_user(self.manager).with_context(
            default_user_id=self.portal_user.id,
            default_state='pending',
        ).create({'tool_id': self.tool.id})
        self.assertEqual(loan.user_id, self.portal_user)
        self.assertEqual(loan.state, 'pending')
