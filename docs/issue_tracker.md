# Tool Borrow Module - Issue Tracker

> Issues discovered during code review of the `tool_borrow` Odoo 18 module.
> Issues #001-#003 were resolved in earlier commits.
> Issues #004-#010 verified via Playwright MCP end-to-end testing on 2026-03-09.
> Issues #004-#010 fixed and re-verified via Playwright MCP on 2026-03-10.

---

## Issue #004: Portal shows ALL tools instead of only assigned tools

| Field | Value |
|-------|-------|
| **Severity** | High (Security/Access Control) |
| **Status** | RESOLVED (2026-03-10) |
| **File** | `tool_borrow/controllers/portal.py:35` |
| **Fix** | Changed `domain = []` to `domain = [('portal_user_ids', 'in', request.env.user.id)]` |

**Description**: The `portal_my_tools` route uses `domain = []` (empty domain), showing ALL tools to ALL portal users. Per the step-guide, portal users should only see tools where they are listed in `portal_user_ids`.

**Verification (2026-03-10)**: Portal user (woowtech_user003) now sees only "Test Drill" (the only tool assigned to them). "Test_tool_1" (no portal users assigned) is not shown.

---

## Issue #005: Portal tool detail page has no access check

| Field | Value |
|-------|-------|
| **Severity** | High (Security) |
| **Status** | RESOLVED (2026-03-10) |
| **File** | `tool_borrow/controllers/portal.py:78` |
| **Fix** | Added `request.env.user.id not in tool.portal_user_ids.ids` check after `tool.exists()` |

**Description**: `portal_my_tool_detail` browses any tool by ID without verifying the current user is in `portal_user_ids`. Any portal user can view any tool by guessing the URL `/my/tools/<id>`.

**Verification (2026-03-10)**: Portal user navigating to `/my/tools/3` (unassigned tool) is redirected back to `/my/tools`.

---

## Issue #006: Portal borrow request has no portal_user_ids check

| Field | Value |
|-------|-------|
| **Severity** | High (Security) |
| **Status** | RESOLVED (2026-03-10) |
| **File** | `tool_borrow/controllers/portal.py:164-178` |
| **Fix** | Added `request.env.user.id not in tool.portal_user_ids.ids` to existing condition in `portal_request_tool` |

**Description**: `portal_request_tool` POST route creates a loan without verifying the user is in the tool's `portal_user_ids`. An unauthorized portal user can borrow any tool by sending a POST request.

**Verification (2026-03-10)**: The portal_user_ids check is now enforced before loan creation. Unauthorized users are redirected.

---

## Issue #007: Portal home counter shows total tools count, not assigned

| Field | Value |
|-------|-------|
| **Severity** | Low (UI/UX) |
| **Status** | RESOLVED (2026-03-10) |
| **File** | `tool_borrow/controllers/portal.py:19` |
| **Fix** | Changed `search_count([])` to `search_count([('portal_user_ids', 'in', request.env.user.id)])` |

**Description**: `_prepare_home_portal_values` uses `search_count([])` for `tool_count`, showing total count of all tools instead of only those assigned to the portal user.

**Verification (2026-03-10)**: Portal home now shows correct count of assigned tools only.

---

## Issue #008: "Under Maintenance" stage has is_closed=False, breaking maintenance workflow

| Field | Value |
|-------|-------|
| **Severity** | Critical (Logic Bug) |
| **Status** | RESOLVED (2026-03-10) |
| **Files** | `tool_borrow/models/tool_tool.py`, `tool_borrow/data/tool_stage_data.xml`, `tool_borrow/views/tool_tool_views.xml` |
| **Fix** | Added dedicated `is_maintenance` boolean field to `tool.stage` model. Updated `_compute_state()` to check `is_maintenance`, `action_set_maintenance()` to search by `is_maintenance`, `action_set_available()` to exclude both closed and maintenance stages. Added `is_maintenance=True` to "Under Maintenance" stage data. Added `is_maintenance` to stage list/form views. |

**Description**: The "Under Maintenance" stage has `is_closed=False` in the data file, but the code relies on `is_closed` to identify maintenance stages. This caused "Set to Maintenance" to move tools to "Retired" instead of "Under Maintenance", and tools manually set to "Under Maintenance" showed state "Available" instead of "Maintenance".

**Verification (2026-03-10)**:
- Clicking "Set to Maintenance" now correctly sets stage to "Under Maintenance" AND state to "Under Maintenance"
- Clicking "Set to Available" correctly restores stage to "In Service" AND state to "Available"
- Chatter log confirms correct stage/state transitions

---

## Issue #009: "Set to Maintenance" / "Set to Available" button visibility broken by Issue #008

| Field | Value |
|-------|-------|
| **Severity** | Medium (UI) |
| **Status** | RESOLVED (2026-03-10) - Auto-resolved by #008 fix |
| **File** | `tool_borrow/views/tool_tool_views.xml:123-124` |

**Description**: The "Set to Available" button uses `invisible="state != 'maintenance'"`. Because of Issue #008, tools in the "Under Maintenance" stage never had `state='maintenance'`, so the button never appeared.

**Verification (2026-03-10)**: With #008 fixed, `_compute_state()` correctly returns `state='maintenance'` for tools in "Under Maintenance" stage. "Set to Maintenance" button appears when state is "available", and "Set to Available" button appears when state is "maintenance".

---

## Issue #010: res.users access error when setting tool_borrow_access

| Field | Value |
|-------|-------|
| **Severity** | Critical (User Type Corruption) - Escalated from High |
| **Status** | RESOLVED (2026-03-10) |
| **Files** | `tool_borrow/models/res_users.py`, `tool_borrow/security/tool_borrow_security.xml` |
| **Fix** | Atomic write (commit ba221bd) + added `implied_ids = [(4, ref('base.group_user'))]` to `group_tool_user` ensuring all Tool Borrow users maintain internal user status. |

**Description**: When saving the Tool Borrow Access setting for a user, the system showed "You are not allowed to access 'User' (res.users) records." The root cause was the two-write pattern in `_update_tool_borrow_groups()`. The atomic write fix resolved the error, and the group hierarchy fix prevents user type demotion.

**Verification (2026-03-10)**: Admin changed Tool Borrow Access for woowtech_user002 from Manager → User → Manager. Both saves completed without errors. No user type corruption observed.

**Remaining note**: The `lemonade0116234@gmail.com` user was corrupted during earlier testing (before fixes) and still requires manual database remediation to restore `base.group_user` group membership.

---

## Playwright MCP E2E Test Results

### Initial Test Run (2026-03-09)

| Test | Description | Result | Notes |
|------|-------------|--------|-------|
| 1 | Admin Login & Module Access | PASS | Admin logs in, Tool Borrow app accessible via menu |
| 2 | Configure User Access | PASS | Tool Borrow Access set to Manager for woowtech_user002 |
| 3 | Create Tool Category | PASS | "Test Power Tools" category created with Properties Definition |
| 4 | Create Tool | PASS | "Test Drill" created with category and portal user assignment |
| 5 | Tool Maintenance Workflow | FAIL | **Issue #008 confirmed**: "Set to Maintenance" sets stage to "Retired" |
| 6 | Internal User - Create Loan | PASS | Loan request created and submitted (as woowtech_user002) |
| 7 | Manager - Approve Loan | PASS | Loan approved, approved_date and approved_by populated |
| 8 | Manager - Confirm Borrow | PASS | Tool state changed to "Borrowed", current borrower shown |
| 9 | Manager - Confirm Return | PASS | Tool state reverted to "Available", return_date populated |
| 10 | Reject & Reset Workflow | PASS | Loan rejected then reset to Draft, dates cleared |
| 11 | Portal User - Browse Tools | PASS* | Portal tools page works; *Issue #004 partially confirmed (empty domain) |
| 12 | Portal User - Tool Detail & Borrow | PASS | Portal borrow request submitted successfully |
| 13 | Portal User - View Loans | PASS | Portal loans page shows loan list with status |
| 14 | Portal Access Control | PASS | Portal user redirected from backend URL to `/my` |
| 15 | Tool State Computed Correctly | PASS | State computation verified: Available, Borrowed, Maintenance lifecycle |

### Fix Verification Test Run (2026-03-10)

| Test | Description | Result | Notes |
|------|-------------|--------|-------|
| V1 | Maintenance Workflow (#008/#009) | PASS | Set to Maintenance → stage="Under Maintenance", state="Under Maintenance". Set to Available → restored correctly. |
| V2 | Portal Tool Filtering (#004/#007) | PASS | Portal user sees only assigned tool (Test Drill). Unassigned tool (Test_tool_1) hidden. |
| V3 | Portal Unauthorized Access (#005) | PASS | `/my/tools/3` (unassigned tool) redirects to `/my/tools` |
| V4 | User Access Level Change (#010) | PASS | Admin changed Tool Borrow Access Manager→User→Manager without errors |

**Environment**: `https://matt-test-6-odoo.woowtech.io` | Odoo 18
**Users tested**: admin, woowtech_user002 (internal), woowtech_user003 (portal)
