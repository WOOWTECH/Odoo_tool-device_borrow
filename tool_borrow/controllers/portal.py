from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


def _website_installed():
    """Check if website module is installed in the current database."""
    try:
        return 'website' in request.env.registry._init_modules
    except Exception:
        return False


class ToolBorrowPortal(CustomerPortal):

    def _check_tool_borrow_access(self):
        """Check if current user has tool_borrow access. Returns True if access granted."""
        access = request.env.user.sudo().tool_borrow_access
        return access and access != 'no_access'

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        has_tool_access = self._check_tool_borrow_access()
        if not counters:
            # Only set template visibility flag for page render, not for /my/counters RPC
            values['show_tool_borrow'] = has_tool_access
        if has_tool_access:
            if 'tool_count' in counters:
                values['tool_count'] = request.env['tool.tool'].search_count([('allowed_user_ids', 'in', request.env.user.id)])
            if 'loan_count' in counters:
                values['loan_count'] = request.env['tool.loan'].search_count([
                    ('user_id', '=', request.env.user.id)
                ])
        return values

    # Routes with website=True - required when website module is installed
    # The module itself doesn't depend on website, but if website is installed,
    # the portal templates require website context

    @http.route(['/my/tools', '/my/tools/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_tools(self, page=1, sortby=None, **kw):
        if not self._check_tool_borrow_access():
            return request.redirect('/my/home')
        values = self._prepare_portal_layout_values()
        Tool = request.env['tool.tool']

        domain = [('allowed_user_ids', 'in', request.env.user.id)]

        # Default sort by name
        searchbar_sortings = {
            'name': {'label': _('Name'), 'order': 'name'},
            'code': {'label': _('Code'), 'order': 'code'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'name'
        order = searchbar_sortings[sortby]['order']

        # Count for pager
        tool_count = Tool.search_count(domain)

        # Pager
        pager = portal_pager(
            url='/my/tools',
            url_args={'sortby': sortby},
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
        })
        return request.render('tool_borrow.portal_my_tools', values)

    @http.route(['/my/tools/<int:tool_id>'], type='http', auth='user', website=True)
    def portal_my_tool_detail(self, tool_id, **kw):
        if not self._check_tool_borrow_access():
            return request.redirect('/my/home')
        tool = request.env['tool.tool'].browse(tool_id)
        if not tool.exists() or request.env.user.id not in tool.allowed_user_ids.ids:
            return request.redirect('/my/tools')

        values = self._prepare_portal_layout_values()
        values.update({
            'tool': tool,
            'page_name': 'tool_detail',
        })
        return request.render('tool_borrow.portal_my_tool_detail', values)

    @http.route(['/my/loans', '/my/loans/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_loans(self, page=1, sortby=None, filterby=None, **kw):
        if not self._check_tool_borrow_access():
            return request.redirect('/my/home')
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

        # Count for pager
        loan_count = Loan.search_count(domain)

        # Pager
        pager = portal_pager(
            url='/my/loans',
            url_args={'sortby': sortby, 'filterby': filterby},
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
        })
        return request.render('tool_borrow.portal_my_loans', values)

    @http.route(['/my/loans/<int:loan_id>'], type='http', auth='user', website=True)
    def portal_my_loan_detail(self, loan_id, **kw):
        if not self._check_tool_borrow_access():
            return request.redirect('/my/home')
        loan = request.env['tool.loan'].browse(loan_id)
        if not loan.exists() or loan.user_id != request.env.user:
            return request.redirect('/my/loans')

        values = self._prepare_portal_layout_values()
        values.update({
            'loan': loan,
            'page_name': 'loan_detail',
        })
        return request.render('tool_borrow.portal_my_loan_detail', values)

    @http.route(['/my/tools/<int:tool_id>/request'], type='http', auth='user', website=True, methods=['POST'])
    def portal_request_tool(self, tool_id, **kw):
        if not self._check_tool_borrow_access():
            return request.redirect('/my/home')
        tool = request.env['tool.tool'].browse(tool_id)
        if not tool.exists() or tool.state != 'available' or request.env.user.id not in tool.allowed_user_ids.ids:
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
