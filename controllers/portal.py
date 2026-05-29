from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ToolBorrowPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'tool_count' in counters:
            values['tool_count'] = request.env['tool.tool'].search_count([])
        if 'loan_count' in counters:
            values['loan_count'] = request.env['tool.loan'].search_count([
                ('user_id', '=', request.env.user.id)
            ])
        return values

    @http.route(['/my/equipment'], type='http', auth='user', website=True)
    def portal_my_equipment(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_home_portal_values(['tool_count', 'loan_count']))
        values['page_name'] = 'equipment'
        return request.render('tool_borrow.portal_my_equipment', values)

    @http.route(['/my/tools', '/my/tools/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_tools(self, page=1, sortby=None, search=None, search_in='all', **kw):
        values = self._prepare_portal_layout_values()
        Tool = request.env['tool.tool']

        domain = []

        # Sorting
        searchbar_sortings = {
            'name': {'label': _('Name'), 'order': 'name'},
            'code': {'label': _('Code'), 'order': 'code'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'name'
        order = searchbar_sortings[sortby]['order']

        # Search inputs
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'name': {'input': 'name', 'label': _('Name')},
            'code': {'input': 'code', 'label': _('Code')},
        }

        # Apply search
        if search and search_in:
            search_domain = []
            if search_in in ('name', 'all'):
                search_domain = [('name', 'ilike', search)]
            if search_in in ('code', 'all'):
                code_domain = [('code', 'ilike', search)]
                if search_domain:
                    search_domain = ['|'] + search_domain + code_domain
                else:
                    search_domain = code_domain
            domain += search_domain

        # Count for pager
        tool_count = Tool.search_count(domain)

        # Pager
        pager = portal_pager(
            url='/my/tools',
            url_args={'sortby': sortby, 'search_in': search_in, 'search': search},
            total=tool_count,
            page=page,
            step=self._items_per_page
        )

        # Content according to pager and target sort
        tools = Tool.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )

        values.update({
            'tools': tools,
            'page_name': 'tools',
            'pager': pager,
            'default_url': '/my/tools',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
        })
        return request.render('tool_borrow.portal_my_tools', values)

    @http.route(['/my/tools/<int:tool_id>'], type='http', auth='user', website=True)
    def portal_my_tool_detail(self, tool_id, **kw):
        tool = request.env['tool.tool'].browse(tool_id)
        if not tool.exists():
            return request.redirect('/my/tools')

        # Record pager (prev/next)
        tool_ids = request.env['tool.tool'].search([]).ids
        try:
            tool_index = tool_ids.index(tool_id)
        except ValueError:
            tool_index = 0
        prev_record = '/my/tools/%d' % tool_ids[tool_index - 1] if tool_index > 0 else None
        next_record = '/my/tools/%d' % tool_ids[tool_index + 1] if tool_index < len(tool_ids) - 1 else None

        values = self._prepare_portal_layout_values()
        values.update({
            'tool': tool,
            'page_name': 'tool_detail',
            'prev_record': prev_record,
            'next_record': next_record,
        })
        return request.render('tool_borrow.portal_my_tool_detail', values)

    @http.route(['/my/loans', '/my/loans/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_loans(self, page=1, sortby=None, filterby=None, search=None, search_in='all', **kw):
        values = self._prepare_portal_layout_values()
        Loan = request.env['tool.loan']

        domain = [('user_id', '=', request.env.user.id)]

        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Request Date'), 'order': 'request_date desc'},
            'tool': {'label': _('Tool'), 'order': 'tool_id'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Filtering
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'pending': {'label': _('Pending'), 'domain': [('state', '=', 'pending')]},
            'approved': {'label': _('Approved'), 'domain': [('state', '=', 'approved')]},
            'borrowed': {'label': _('Borrowed'), 'domain': [('state', '=', 'borrowed')]},
            'returned': {'label': _('Returned'), 'domain': [('state', '=', 'returned')]},
        }
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Search inputs
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search in All')},
            'tool': {'input': 'tool', 'label': _('Tool Name')},
        }

        # Apply search
        if search and search_in:
            if search_in in ('tool', 'all'):
                domain += [('tool_id.name', 'ilike', search)]

        # Count for pager
        loan_count = Loan.search_count(domain)

        # Pager
        pager = portal_pager(
            url='/my/loans',
            url_args={'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            total=loan_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        loans = Loan.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )

        values.update({
            'loans': loans,
            'page_name': 'loans',
            'pager': pager,
            'default_url': '/my/loans',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
        })
        return request.render('tool_borrow.portal_my_loans', values)

    @http.route(['/my/loans/<int:loan_id>'], type='http', auth='user', website=True)
    def portal_my_loan_detail(self, loan_id, **kw):
        loan = request.env['tool.loan'].browse(loan_id)
        if not loan.exists() or loan.user_id != request.env.user:
            return request.redirect('/my/loans')

        # Record pager (prev/next)
        loan_ids = request.env['tool.loan'].search([
            ('user_id', '=', request.env.user.id)
        ]).ids
        try:
            loan_index = loan_ids.index(loan_id)
        except ValueError:
            loan_index = 0
        prev_record = '/my/loans/%d' % loan_ids[loan_index - 1] if loan_index > 0 else None
        next_record = '/my/loans/%d' % loan_ids[loan_index + 1] if loan_index < len(loan_ids) - 1 else None

        values = self._prepare_portal_layout_values()
        values.update({
            'loan': loan,
            'page_name': 'loan_detail',
            'prev_record': prev_record,
            'next_record': next_record,
        })
        return request.render('tool_borrow.portal_my_loan_detail', values)

    @http.route(['/my/tools/<int:tool_id>/request'], type='http', auth='user', website=True, methods=['POST'])
    def portal_request_tool(self, tool_id, **kw):
        tool = request.env['tool.tool'].browse(tool_id)
        if not tool.exists() or tool.state != 'available':
            return request.redirect('/my/tools')

        # Create loan request
        loan = request.env['tool.loan'].create({
            'tool_id': tool_id,
            'user_id': request.env.user.id,
            'notes': kw.get('notes', ''),
        })
        # Submit the request
        loan.action_submit()

        return request.redirect('/my/loans/%s' % loan.id)
