import re

from odoo.tests import HttpCase, tagged

from .common import ToolBorrowTestMixin


@tagged('post_install', '-at_install', 'tool_borrow')
class TestPortalHardening(ToolBorrowTestMixin, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_tool_borrow_fixtures()

    def _csrf_token(self, tool):
        res = self.url_open('/my/tools/%d' % tool.id)
        self.assertEqual(res.status_code, 200)
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', res.text)
        self.assertTrue(match, 'request form with csrf token expected')
        return match.group(1)

    def _loans(self, user):
        return self.env['tool.loan'].search([('user_id', '=', user.id)])

    # ------------------------------------------------------------------
    # Happy path: portal request form
    # ------------------------------------------------------------------
    def test_portal_request_creates_pending_loan(self):
        self.authenticate('tb_portal', 'tb_portal')
        token = self._csrf_token(self.tool)
        res = self.url_open(
            '/my/tools/%d/request' % self.tool.id,
            data={'csrf_token': token, 'notes': 'need it tomorrow'},
            allow_redirects=False,
        )
        self.assertIn(res.status_code, (301, 302, 303))
        loan = self._loans(self.portal_user)
        self.assertEqual(len(loan), 1)
        self.assertEqual(loan.state, 'pending')
        self.assertEqual(loan.notes, 'need it tomorrow')
        self.assertTrue(loan.request_date)
        self.assertIn('/my/loans/%d' % loan.id, res.headers.get('Location', ''))
        detail = self.url_open('/my/loans/%d' % loan.id)
        self.assertEqual(detail.status_code, 200)
        self.assertIn('TB Drill', detail.text)

    def test_internal_user_portal_request(self):
        self.authenticate('tb_internal', 'tb_internal')
        token = self._csrf_token(self.tool2)
        self.url_open('/my/tools/%d/request' % self.tool2.id,
                      data={'csrf_token': token}, allow_redirects=False)
        loan = self._loans(self.internal_user)
        self.assertEqual(loan.state, 'pending')

    # ------------------------------------------------------------------
    # Archived tools are not reachable from the portal (hardening 6abdbb5e9694)
    # ------------------------------------------------------------------
    def test_archived_tool_detail_redirects(self):
        self.authenticate('tb_portal', 'tb_portal')
        res = self.url_open('/my/tools/%d' % self.archived_tool.id,
                            allow_redirects=False)
        self.assertIn(res.status_code, (301, 302, 303))
        self.assertTrue(res.headers.get('Location', '').endswith('/my/tools'))
        listing = self.url_open('/my/tools')
        self.assertEqual(listing.status_code, 200)
        self.assertNotIn('TB Archived Hammer', listing.text)
        self.assertIn('TB Drill', listing.text)

    def test_archived_tool_cannot_be_requested(self):
        self.authenticate('tb_portal', 'tb_portal')
        token = self._csrf_token(self.tool)
        res = self.url_open(
            '/my/tools/%d/request' % self.archived_tool.id,
            data={'csrf_token': token}, allow_redirects=False,
        )
        self.assertIn(res.status_code, (301, 302, 303))
        self.assertTrue(res.headers.get('Location', '').endswith('/my/tools'))
        self.assertFalse(self._loans(self.portal_user))

    # ------------------------------------------------------------------
    # Unknown sortby / filterby fall back to defaults (hardening f53730c0cc7b)
    # ------------------------------------------------------------------
    def test_unknown_sort_and_filter_do_not_crash(self):
        self.authenticate('tb_portal', 'tb_portal')
        for url in (
            '/my/tools?sortby=bogus',
            '/my/loans?sortby=bogus',
            '/my/loans?filterby=bogus',
            '/my/loans?sortby=__class__&filterby=__init__',
        ):
            with self.subTest(url=url):
                res = self.url_open(url)
                self.assertEqual(res.status_code, 200)
        # valid values keep working
        for url in ('/my/tools?sortby=code', '/my/loans?sortby=state&filterby=pending'):
            with self.subTest(url=url):
                self.assertEqual(self.url_open(url).status_code, 200)

    # ------------------------------------------------------------------
    # RPC: workflow fields cannot be forged through call_kw (d3da922fb4ba)
    # ------------------------------------------------------------------
    def test_rpc_cannot_forge_borrowed_loan(self):
        self.authenticate('tb_portal', 'tb_portal')
        with self.assertLogs('odoo.http', level='WARNING'):
            with self.assertRaisesRegex(Exception, 'odoo.exceptions.AccessError'):
                self.make_jsonrpc_request('/web/dataset/call_kw', {
                    'model': 'tool.loan',
                    'method': 'create',
                    'args': [{
                        'tool_id': self.tool.id,
                        'user_id': self.portal_user.id,
                        'state': 'borrowed',
                        'approved_by': self.manager.id,
                    }],
                    'kwargs': {},
                })
        self.assertFalse(self._loans(self.portal_user))
        self.assertEqual(self.tool.state, 'available')

    def test_rpc_context_defaults_cannot_forge_approval(self):
        """default_<field> keys in the call_kw context must not fill the
        protected workflow fields (d3da922fb4ba, round 2)."""
        self.authenticate('tb_portal', 'tb_portal')
        now = '2026-01-01 08:00:00'
        loan_id = self.make_jsonrpc_request('/web/dataset/call_kw', {
            'model': 'tool.loan',
            'method': 'create',
            'args': [{'tool_id': self.tool.id}],
            'kwargs': {'context': {
                'default_state': 'borrowed',
                'default_approved_by': self.manager.id,
                'default_approved_date': now,
                'default_borrow_date': now,
                'default_return_date': now,
                'default_request_date': now,
            }},
        })
        loan = self.env['tool.loan'].browse(loan_id)
        self.assertEqual(loan.user_id, self.portal_user)
        self.assertEqual(loan.state, 'draft')
        for fname in ('approved_by', 'approved_date', 'borrow_date',
                      'return_date', 'request_date'):
            self.assertFalse(loan[fname], '%s must not be forged' % fname)
        self.make_jsonrpc_request('/web/dataset/call_kw', {
            'model': 'tool.loan',
            'method': 'action_submit',
            'args': [[loan_id]],
            'kwargs': {},
        })
        loan.invalidate_recordset()
        self.assertEqual(loan.state, 'pending')
        self.assertFalse(loan.approved_by)
        self.assertFalse(loan.borrow_date)
        # The portal detail page must not show a forged approver.
        res = self.url_open('/my/loans/%d' % loan_id)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('TB Manager', res.text)
