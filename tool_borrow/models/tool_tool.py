from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ToolCategory(models.Model):
    """Tool Category - holds property definitions for tools"""
    _name = 'tool.category'
    _description = 'Tool Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    tool_ids = fields.One2many('tool.tool', 'category_id', string='Tools')
    tool_count = fields.Integer(string='Tool Count', compute='_compute_tool_count')

    # Properties Definition for tools in this category
    tool_properties_definition = fields.PropertiesDefinition('Tool Properties')

    @api.depends('tool_ids')
    def _compute_tool_count(self):
        for category in self:
            category.tool_count = len(category.tool_ids)


class ToolTool(models.Model):
    _name = 'tool.tool'
    _description = 'Tool'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, default='New', copy=False, tracking=True)

    state = fields.Selection([
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('maintenance', 'Under Maintenance'),
    ], string='Status', default='available', required=True, tracking=True)

    # Category for property definitions
    category_id = fields.Many2one(
        'tool.category',
        string='Category',
        help='Category determines which properties are available for this tool',
    )

    # Dynamic properties (like Project tasks)
    tool_properties = fields.Properties(
        'Properties',
        definition='category_id.tool_properties_definition',
        copy=True,
    )

    # Allowed users who can see/request this tool (internal + portal with a tool_borrow role)
    allowed_user_ids = fields.Many2many(
        'res.users',
        'tool_tool_portal_user_rel',
        'tool_id',
        'user_id',
        string='Allowed Users',
        domain=[('tool_borrow_access', 'in', ['user', 'manager', 'admin'])],
        help='Select users who can request to borrow this tool',
    )

    loan_ids = fields.One2many('tool.loan', 'tool_id', string='Loan History')
    property_ids = fields.One2many('tool.property', 'tool_id', string='Custom Properties')
    notes = fields.Html(string='Notes')
    active = fields.Boolean(default=True)

    current_loan_id = fields.Many2one(
        'tool.loan',
        string='Current Loan',
        compute='_compute_current_loan',
        store=True,
    )
    current_borrower_id = fields.Many2one(
        'res.users',
        string='Current Borrower',
        compute='_compute_current_loan',
        store=True,
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Tool code must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals['code'] == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('tool.tool') or 'New'
        return super().create(vals_list)

    @api.depends('loan_ids', 'loan_ids.state')
    def _compute_current_loan(self):
        for tool in self:
            current_loan = tool.loan_ids.filtered(lambda l: l.state == 'borrowed')[:1]
            tool.current_loan_id = current_loan
            tool.current_borrower_id = current_loan.user_id if current_loan else False

    def action_set_maintenance(self):
        self.ensure_one()
        if self.state == 'borrowed':
            raise UserError(_('Cannot set tool to maintenance while it is borrowed.'))
        self.state = 'maintenance'

    def action_set_available(self):
        self.ensure_one()
        if self.state == 'borrowed':
            raise UserError(_('Cannot set tool to available while it is borrowed. Please confirm return first.'))
        self.state = 'available'


class ToolProperty(models.Model):
    _name = 'tool.property'
    _description = 'Tool Custom Property'
    _order = 'sequence, id'

    tool_id = fields.Many2one('tool.tool', string='Tool', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Property Name', required=True)
    value = fields.Char(string='Property Value', required=True)
