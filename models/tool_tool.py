from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ToolStage(models.Model):
    """Tool Stage - similar to project.task.type for managing tool states"""
    _name = 'tool.stage'
    _description = 'Tool Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    fold = fields.Boolean(string='Folded in Kanban',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    is_closed = fields.Boolean(string='Is Closed Stage',
        help='Tools in this stage are considered closed/unavailable.')
    description = fields.Text(string='Description', translate=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Stage name must be unique!'),
    ]


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
    code = fields.Char(string='Code', required=True, copy=False, tracking=True)

    # Stage-based state (like Project tasks)
    stage_id = fields.Many2one(
        'tool.stage',
        string='Stage',
        tracking=True,
        default=lambda self: self._get_default_stage_id(),
        group_expand='_read_group_stage_ids',
        copy=False,
        index=True,
    )

    # Keep state as computed field based on stage for compatibility
    state = fields.Selection([
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('maintenance', 'Under Maintenance'),
    ], string='Status', compute='_compute_state', store=True, tracking=True)

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

    # Changed from boolean to many2many for portal users
    portal_user_ids = fields.Many2many(
        'res.users',
        'tool_tool_portal_user_rel',
        'tool_id',
        'user_id',
        string='Portal Users',
        domain=[('share', '=', True)],
        help='Select portal users who can request to borrow this tool',
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

    def _get_default_stage_id(self):
        """Get default stage (first available stage)"""
        return self.env['tool.stage'].search([], limit=1).id

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Return all stages for group_expand in kanban view"""
        return stages.search([])

    @api.depends('stage_id', 'stage_id.is_closed', 'current_loan_id', 'current_loan_id.state')
    def _compute_state(self):
        """Compute state based on stage and borrowing status"""
        for tool in self:
            if tool.current_loan_id and tool.current_loan_id.state == 'borrowed':
                tool.state = 'borrowed'
            elif tool.stage_id and tool.stage_id.is_closed:
                tool.state = 'maintenance'
            else:
                tool.state = 'available'

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
        # Find maintenance stage
        maintenance_stage = self.env['tool.stage'].search([('is_closed', '=', True)], limit=1)
        if maintenance_stage:
            self.stage_id = maintenance_stage

    def action_set_available(self):
        self.ensure_one()
        if self.state == 'borrowed':
            raise UserError(_('Cannot set tool to available while it is borrowed. Please confirm return first.'))
        # Find available stage
        available_stage = self.env['tool.stage'].search([('is_closed', '=', False)], limit=1)
        if available_stage:
            self.stage_id = available_stage


class ToolProperty(models.Model):
    _name = 'tool.property'
    _description = 'Tool Custom Property'
    _order = 'sequence, id'

    tool_id = fields.Many2one('tool.tool', string='Tool', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Property Name', required=True)
    value = fields.Char(string='Property Value', required=True)
