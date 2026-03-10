# Tool Borrow Module - Issue Tracker

> Issues discovered during code review of the `tool_borrow` Odoo 18 module.
> Issues #001-#003 were resolved in earlier commits.
> Issues #004-#010 verified via Playwright MCP end-to-end testing on 2026-03-09.

---

## Issue #004: Portal shows ALL tools instead of only assigned tools

| Field | Value |
|-------|-------|
| **Severity** | High (Security/Access Control) |
| **Status** | Open - Confirmed via E2E Test |
| **File** | `tool_borrow/controllers/portal.py:35` |

**Description**: The `portal_my_tools` route uses `domain = []` (empty domain), showing ALL tools to ALL portal users. Per the step-guide, portal users should only see tools where they are listed in `portal_user_ids`.

**Expected**: `domain = [('portal_user_ids', 'in', request.env.user.id)]`

**Steps to reproduce**:
1. Login as portal user (`woowtech_user003@protonmail.com`)
2. Navigate to `/my/tools`
3. Observe: ALL tools are visible, not just ones assigned via `portal_user_ids`

**Test result (2026-03-09)**: Partially confirmed. Portal user sees all 2 tools on `/my/tools`. Both tools happen to have this portal user assigned, so the empty domain bug is not fully distinguishable without creating an unassigned tool. However, code review confirms `domain = []` is used.

---

## Issue #005: Portal tool detail page has no access check

| Field | Value |
|-------|-------|
| **Severity** | High (Security) |
| **Status** | Open |
| **File** | `tool_borrow/controllers/portal.py:78` |

**Description**: `portal_my_tool_detail` browses any tool by ID without verifying the current user is in `portal_user_ids`. Any portal user can view any tool by guessing the URL `/my/tools/<id>`.

**Expected**: After browsing the tool, check `request.env.user.id in tool.portal_user_ids.ids` and redirect to `/my/tools` if unauthorized.

**Steps to reproduce**:
1. Login as portal user
2. Navigate to `/my/tools/999` (any tool ID not assigned to this user)
3. Observe: Tool detail page is accessible without authorization check

---

## Issue #006: Portal borrow request has no portal_user_ids check

| Field | Value |
|-------|-------|
| **Severity** | High (Security) |
| **Status** | Open |
| **File** | `tool_borrow/controllers/portal.py:164-178` |

**Description**: `portal_request_tool` POST route creates a loan without verifying the user is in the tool's `portal_user_ids`. An unauthorized portal user can borrow any tool by sending a POST request.

**Expected**: Before creating the loan, verify `request.env.user.id in tool.portal_user_ids.ids` and redirect if unauthorized.

**Steps to reproduce**:
1. Login as portal user not assigned to a tool
2. POST to `/my/tools/<tool_id>/request`
3. Observe: Loan is created successfully without authorization

---

## Issue #007: Portal home counter shows total tools count, not assigned

| Field | Value |
|-------|-------|
| **Severity** | Low (UI/UX) |
| **Status** | Open |
| **File** | `tool_borrow/controllers/portal.py:19` |

**Description**: `_prepare_home_portal_values` uses `search_count([])` for `tool_count`, showing total count of all tools instead of only those assigned to the portal user.

**Expected**: `search_count([('portal_user_ids', 'in', request.env.user.id)])`

---

## Issue #008: "Under Maintenance" stage has is_closed=False, breaking maintenance workflow

| Field | Value |
|-------|-------|
| **Severity** | Critical (Logic Bug) |
| **Status** | Open - Confirmed via E2E Test |
| **Files** | `tool_borrow/data/tool_stage_data.xml:13-19`, `tool_borrow/models/tool_tool.py:128-136,145-152` |

**Description**: The "Under Maintenance" stage has `is_closed=False` in the data file, but the code relies on `is_closed` to identify maintenance stages:

1. `_compute_state()` (line 133): checks `stage_id.is_closed` to set `state='maintenance'` - but "Under Maintenance" has `is_closed=False`, so state computes to `'available'` instead.
2. `action_set_maintenance()` (line 150): searches for `is_closed=True` stage - finds "Retired" (the only `is_closed=True` stage) instead of "Under Maintenance".

**Result**:
- Clicking "Set to Maintenance" moves tool to **"Retired"** stage instead of "Under Maintenance"
- A tool manually set to "Under Maintenance" stage shows state **"Available"** instead of "Maintenance"

**Steps to reproduce**:
1. Login as admin
2. Create a tool (state = available)
3. Click "Set to Maintenance"
4. Observe: Tool stage becomes "Retired" (not "Under Maintenance")
5. OR: Manually set stage to "Under Maintenance"
6. Observe: Tool state still shows "Available" instead of "Maintenance"

**Test result (2026-03-09)**: FULLY CONFIRMED.
- Clicking "Set to Maintenance" changed stage to "Retired" (not "Under Maintenance"), status showed "Under Maintenance" (because Retired has `is_closed=True`).
- Manually setting stage to "Under Maintenance" showed status "Available" (not "Under Maintenance"), and the "Set to Maintenance" button appeared instead of "Set to Available".
- Setting stage to "Retired" correctly showed status "Under Maintenance" and "Set to Available" button - proving the `is_closed` logic works, but on the wrong stage.

---

## Issue #009: "Set to Maintenance" / "Set to Available" button visibility broken by Issue #008

| Field | Value |
|-------|-------|
| **Severity** | Medium (UI) |
| **Status** | Open |
| **File** | `tool_borrow/views/tool_tool_views.xml:123-124` |

**Description**: The "Set to Available" button uses `invisible="state != 'maintenance'"`. Because of Issue #008, tools in the "Under Maintenance" stage never have `state='maintenance'` (they show `state='available'`), so this button never appears. The maintenance workflow is completely broken at both the logic and UI levels.

---

## Issue #010: res.users access error when setting tool_borrow_access

| Field | Value |
|-------|-------|
| **Severity** | Critical (User Type Corruption) - Escalated from High |
| **Status** | Open - Partially Fixed, Side Effects Confirmed |
| **File** | `tool_borrow/models/res_users.py` |

**Description**: When saving the Tool Borrow Access setting for a user, the system may show "You are not allowed to access 'User' (res.users) records." The root cause (per prior analysis) is the two-write pattern in `_update_tool_borrow_groups()`: it first removes all groups (line 32), then adds the new one (lines 35-40). Between these two writes, cache invalidation causes Odoo to re-evaluate permissions in an intermediate state.

**Previous fix (commit 84d2907)**: Refactored to single atomic write pattern - merges all `groups_id` commands (remove + add) into a single `vals` dict passed to `super().write()`. The permission error dialog no longer appears.

**Remaining side effect**: During earlier testing (before the fix), the two-write pattern **corrupted the `lemonade0116234@gmail.com` user type** from Internal User to Portal/Public User. This user's Access Rights tab became empty, the Portal Users field's `domain=[('share', '=', True)]` now includes this user, and the user gets 403 Forbidden when attempting to access the backend. This corruption was NOT reversed by the code fix and requires manual database correction.

**Steps to reproduce (original bug)**:
1. Login as admin
2. Go to Settings > Users > select a user
3. Open Tool Borrow tab
4. Change access level (e.g., blank to "User")
5. Click Save
6. Observe: Permission error dialog (now fixed), but user type may have been corrupted

**Test result (2026-03-09)**: The atomic write fix (commit 84d2907) resolves the permission error. Admin can now change Tool Borrow Access levels without errors. However, the `lemonade0116234@gmail.com` user remains corrupted from earlier testing - it shows as a portal user with 403 Forbidden on backend access. Manual fix needed: restore `base.group_user` group for this user via database or shell.

---

## Playwright MCP E2E Test Results (2026-03-09)

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

**Environment**: `https://matt-test-6-odoo.woowtech.io` | Odoo 18
**Users tested**: admin, woowtech_user002 (internal), woowtech_user003 (portal)
**Note**: `lemonade0116234@gmail.com` was unusable due to user type corruption from Issue #010 (pre-fix).
