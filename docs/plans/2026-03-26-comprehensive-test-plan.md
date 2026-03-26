# Tool Borrow Module - Comprehensive Pre-Launch Test Plan

## Overview
- **Module:** tool_borrow (Odoo 18)
- **Version:** 18.0.1.3.0
- **Total Test Cases:** 124
- **Approach:** Mixed (XML-RPC scripts + Python requests + Chrome DevTools MCP + Playwright)

## Test Rounds

### Round 1: Backend Model Tests (40 cases, #1-40)
- XML-RPC script: `tests/test_round1_models.py`
- tool.loan state machine (18), tool.tool operations (10), res.users group sync (8), category/property (4)

### Round 2: Security & Permission Tests (24 cases, #41-64)
- XML-RPC script: `tests/test_round2_security.py`
- 6 roles × CRUD + action methods, privilege escalation attempts

### Round 3: Portal HTTP Route Tests (34 cases, #65-98)
- Python requests script: `tests/test_round3_http.py`
- Route access control, form submission, CSRF, pagination, chatter

### Round 4: Frontend UI Tests (26 cases, #99-124)
- Chrome DevTools MCP: interactive (12 cases)
- Playwright script: `tests/test_round4_playwright.py` (14 cases)
- Rendering, RWD, E2E flow, XSS, performance

## Test Accounts
| Account | Role | Purpose |
|---------|------|---------|
| admin/admin | System admin + tool_admin | Full backend |
| portal/portal | Portal (access=user) | Portal frontend |
| xiaoming/xiaoming | Portal (access=user) | Cross-user isolation |
| testmanager/testmanager | Internal + tool_manager | Manager permission |
| testuser/testuser | Internal + tool_user | User permission |
| noaccess/noaccess | Portal (access=no_access) | Denial testing |
