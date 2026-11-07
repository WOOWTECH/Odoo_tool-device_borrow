from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

# Workflow / approval fields that only Equipment Managers (or sudo code
# running inside the workflow actions) may set.  Regular internal and portal
# users have write/create ACL on their own loans (needed for drafts and
# notes), so these fields must be guarded at the ORM level -- the ``readonly``
# attribute is a UI hint only and is not enforced by ``write()``.
PROTECTED_LOAN_FIELDS = (
    'state',
    'approved_by',
    'approved_date',
    'borrow_date',
    'return_date',
    'request_date',
)


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
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    request_date = fields.Datetime(string='Request Date', readonly=True, copy=False)
    approved_date = fields.Datetime(string='Approved Date', readonly=True, copy=False)
    borrow_date = fields.Datetime(string='Borrow Date', readonly=True, copy=False)
    return_date = fields.Datetime(string='Return Date', readonly=True, copy=False)

    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    notes = fields.Text(string='Notes')

    def _check_manager_access(self):
        """Check if current user has manager or admin access"""
        if not self.env.user.has_group('tool_borrow.group_tool_manager'):
            raise UserError(_('Only Tool Managers can perform this action.'))

    def _is_loan_manager(self):
        """True for superuser-mode code and Equipment Managers."""
        return self.env.su or self.env.user.has_group('tool_borrow.group_tool_manager')

    def _check_borrower_or_manager(self):
        """Only the borrower himself (or a manager) may drive his own request."""
        if self._is_loan_manager():
            return
        for loan in self:
            if loan.user_id != self.env.user:
                raise AccessError(_('You can only manage your own loan requests.'))

    def action_submit(self):
        """Submit loan request for approval"""
        self.ensure_one()
        self._check_borrower_or_manager()
        if self.state != 'draft':
            raise UserError(_('Only draft requests can be submitted.'))
        if not self.tool_id.active or self.tool_id.state != 'available':
            raise UserError(_('This tool is not available for borrowing.'))
        # The transition has been validated above; write the protected
        # workflow fields in sudo so regular users cannot set them directly.
        self.sudo().write({
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
        """Reset a pending (borrower or manager) or rejected (manager only)
        request back to draft."""
        self.ensure_one()
        self._check_borrower_or_manager()
        if self.state not in ('rejected', 'pending'):
            raise UserError(_('Only rejected or pending requests can be reset to draft.'))
        if self.state == 'rejected' and not self._is_loan_manager():
            raise UserError(_('Only Tool Managers can reset a rejected request to draft.'))
        self.sudo().write({
            'state': 'draft',
            'request_date': False,
            'approved_date': False,
            'approved_by': False,
            'borrow_date': False,
            'return_date': False,
        })

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('tool_id', 'state')
    def _check_tool_available(self):
        """Prevent creating or moving a loan to active states when the tool
        is already borrowed by another loan."""
        active_states = ('draft', 'pending', 'approved', 'borrowed')
        for loan in self:
            if loan.state not in active_states:
                continue
            if loan.tool_id.state == 'borrowed' and loan.tool_id.current_loan_id and loan.tool_id.current_loan_id != loan:
                raise ValidationError(
                    _('Tool "%(tool)s" is already borrowed and cannot be '
                      'assigned to a new loan request.',
                      tool=loan.tool_id.name)
                )

    @api.constrains('borrow_date', 'return_date')
    def _check_return_date(self):
        """Return date must be on or after the borrow date."""
        for loan in self:
            if loan.borrow_date and loan.return_date:
                if loan.return_date < loan.borrow_date:
                    raise ValidationError(
                        _('Return date cannot be earlier than the borrow date.')
                    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def _changed_fields(self, vals, fnames):
        """Return the fields of ``fnames`` whose value in ``vals`` differs
        from the current value of at least one record of ``self`` (so that a
        client re-sending an unchanged value is not rejected)."""
        changed = []
        for fname in fnames:
            if fname not in vals:
                continue
            field = self._fields[fname]
            for loan in self:
                new = field.convert_to_cache(vals[fname], loan)
                old = field.convert_to_cache(loan[fname], loan)
                if new != old:
                    changed.append(fname)
                    break
        return changed

    @api.model_create_multi
    def create(self, vals_list):
        if not self._is_loan_manager():
            for vals in vals_list:
                if vals.get('state', 'draft') != 'draft':
                    raise AccessError(_(
                        'Only Tool Managers can create loan requests in a '
                        'state other than draft.'))
                forbidden = [
                    fname for fname in PROTECTED_LOAN_FIELDS
                    if fname != 'state' and vals.get(fname)
                ]
                if forbidden:
                    raise AccessError(_(
                        'Only Tool Managers can set the following fields: '
                        '%(fields)s', fields=', '.join(forbidden)))
                user_id = vals.get('user_id', self.env.uid)
                if user_id and user_id != self.env.uid:
                    raise AccessError(_(
                        'You can only create loan requests for yourself.'))
                # Pin every protected field (and the borrower) explicitly so
                # that no default source -- ``default_<field>`` context keys
                # sent over RPC or user-scoped ``ir.default`` rows, both
                # applied by ``default_get`` for missing keys -- can fill
                # them in behind the checks above.
                for fname in PROTECTED_LOAN_FIELDS:
                    vals[fname] = 'draft' if fname == 'state' else False
                vals['user_id'] = self.env.uid
        for vals in vals_list:
            if vals.get('tool_id'):
                tool = self.env['tool.tool'].browse(vals['tool_id'])
                if not tool.active or tool.state != 'available':
                    raise UserError(_('Cannot create loan request for unavailable tool.'))
        return super().create(vals_list)

    def write(self, vals):
        if not self._is_loan_manager():
            forbidden = self._changed_fields(vals, PROTECTED_LOAN_FIELDS)
            if forbidden:
                raise AccessError(_(
                    'Only Tool Managers can change the following fields: '
                    '%(fields)s', fields=', '.join(forbidden)))
            relinked = self._changed_fields(vals, ('tool_id', 'user_id'))
            if relinked:
                if any(loan.state != 'draft' for loan in self):
                    raise AccessError(_(
                        'The tool and borrower can only be changed while the '
                        'request is a draft.'))
                if 'user_id' in relinked and vals['user_id'] != self.env.uid:
                    raise AccessError(_(
                        'You can only create loan requests for yourself.'))
                if 'tool_id' in relinked:
                    tool = self.env['tool.tool'].browse(vals['tool_id'])
                    if not tool.active or tool.state != 'available':
                        raise UserError(_(
                            'Cannot create loan request for unavailable tool.'))
        return super().write(vals)
