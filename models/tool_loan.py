from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ToolLoan(models.Model):
    _name = 'tool.loan'
    _description = 'Tool Loan Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'

    tool_id = fields.Many2one(
        'tool.tool',
        string='Tool',
        required=True,
        tracking=True,
        domain="[('state', '=', 'available')]",
    )
    user_id = fields.Many2one(
        'res.users',
        string='Borrower',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
    ], string='Status', default='draft', required=True, tracking=True)

    request_date = fields.Datetime(string='Request Date', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)
    borrow_date = fields.Datetime(string='Borrow Date', readonly=True)
    return_date = fields.Datetime(string='Return Date', readonly=True)

    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    notes = fields.Text(string='Notes')

    def _check_manager_access(self):
        """Check if current user has manager or admin access"""
        if not self.env.user.has_group('tool_borrow.group_tool_manager'):
            raise UserError(_('Only Tool Managers can perform this action.'))

    def action_submit(self):
        """Submit loan request for approval"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft requests can be submitted.'))
        if self.tool_id.state != 'available':
            raise UserError(_('This tool is not available for borrowing.'))
        self.write({
            'state': 'pending',
            'request_date': fields.Datetime.now(),
        })

    def action_approve(self):
        """Approve loan request"""
        self.ensure_one()
        self._check_manager_access()
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be approved.'))
        if self.tool_id.state != 'available':
            raise UserError(_('This tool is no longer available.'))
        self.write({
            'state': 'approved',
            'approved_date': fields.Datetime.now(),
            'approved_by': self.env.user.id,
        })

    def action_reject(self):
        """Reject loan request"""
        self.ensure_one()
        self._check_manager_access()
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be rejected.'))
        self.write({
            'state': 'rejected',
        })

    def action_confirm_borrow(self):
        """Confirm tool has been picked up"""
        self.ensure_one()
        self._check_manager_access()
        if self.state != 'approved':
            raise UserError(_('Only approved requests can be confirmed for borrowing.'))
        if self.tool_id.state != 'available':
            raise UserError(_('This tool is no longer available.'))
        self.write({
            'state': 'borrowed',
            'borrow_date': fields.Datetime.now(),
        })
        # Note: tool.state is computed from current_loan_id.state, no direct assignment needed

    def action_confirm_return(self):
        """Confirm tool has been returned"""
        self.ensure_one()
        self._check_manager_access()
        if self.state != 'borrowed':
            raise UserError(_('Only borrowed tools can be returned.'))
        self.write({
            'state': 'returned',
            'return_date': fields.Datetime.now(),
        })
        # Note: tool.state is computed from current_loan_id.state, no direct assignment needed

    def action_reset_to_draft(self):
        """Reset rejected request to draft"""
        self.ensure_one()
        if self.state not in ('rejected', 'pending'):
            raise UserError(_('Only rejected or pending requests can be reset to draft.'))
        self.write({
            'state': 'draft',
            'request_date': False,
            'approved_date': False,
            'approved_by': False,
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('tool_id'):
                tool = self.env['tool.tool'].browse(vals['tool_id'])
                if tool.state != 'available':
                    raise UserError(_('Cannot create loan request for unavailable tool.'))
        return super().create(vals_list)
