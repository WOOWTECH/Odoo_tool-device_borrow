# Step-by-Step Guide: tool_borrow Module for Odoo 18

A complete internal tool/device lending system with portal access, approval workflows, and audit trails.

---

## User Types

Odoo 18 has two types of users, and **both** can use this module:

### Internal Users (Backend)

Access the module through Odoo's backend UI (Tool Borrow menu). Three access levels:

| Role | Permissions |
|---|---|
| **User** | Browse tools, create/submit own loan requests, view own loans |
| **Manager** | All User permissions + approve/reject loans, confirm borrow & return |
| **Admin** | All Manager permissions + full CRUD on tools, categories, stages |

### Portal Users (Frontend)

Access through the portal web interface (`/my/tools` and `/my/loans`):

- Browse tools assigned to them (via the `portal_user_ids` field on each tool)
- View tool details and current availability
- Submit borrow requests (auto-creates and submits a loan)
- View their own loan history and status timeline

Portal users **cannot** access the backend, approve/reject loans, or manage tools.

**Typical setup:** Portal users request tools, internal managers approve them.

---

## Step 1: Install the Module

1. Copy the `tool_borrow/` directory into your Odoo 18 addons path
2. Restart Odoo server:
   ```bash
   ./odoo-bin -u base -d your_db
   ```
3. Go to **Apps** → search "Tool Borrow" → click **Install**
4. Default data is auto-created:
   - 3 stages: In Service, Under Maintenance, Retired
   - 1 category: General Tools

---

## Step 2: Configure Internal User Access

Go to **Settings → Users & Companies → Users**, select an internal user, open the **Tool Borrow** tab:

| Access Level | What They Can Do |
|---|---|
| **User** | Browse tools, create/view own loan requests |
| **Manager** | Approve/reject loans, confirm borrow & return |
| **Admin** | Full CRUD on tools, categories, stages, loans |

Set at least one **Admin** and one **Manager** user.

---

## Step 3: Set Up Tool Categories (Optional)

Go to **Tool Borrow → Configuration → Tool Categories**

1. Click **New**
2. Enter category name (e.g., "Power Tools", "Measurement Devices")
3. In the **Properties Definition** tab, define custom fields for tools in this category
   - Example: "Voltage", "Calibration Date", "Weight"
   - These become dynamic fields on all tools in this category
4. Save

---

## Step 4: Create Tools

Go to **Tool Borrow → Tools**

1. Click **New**
2. Fill in:
   - **Name**: e.g., "Bosch Impact Drill"
   - **Code**: unique identifier, e.g., "DRILL-001"
   - **Category**: select from your categories
   - **Stage**: defaults to "In Service"
   - **Portal Users**: add portal users who are allowed to request this tool
3. If the category has custom properties, fill those in the **Custom Properties** tab
4. Save

The tool's **state** is automatically computed:
- `available` = In Service stage + no active loan
- `borrowed` = has an active borrowed loan
- `maintenance` = stage is closed (Maintenance/Retired)

---

## Step 5: Set Up Portal Users (for external borrowers)

1. Go to **Settings → Users → New**
2. Create a portal user (access type: **Portal**)
3. Go back to a tool's form → add this portal user to the **Portal Users** field
4. The portal user can now access `/my/tools` to browse and request assigned tools

> **Note:** Portal users can only see tools where they are listed in `portal_user_ids`. They cannot see all tools.

---

## Step 6: Example — A User Borrows a Tool

### A. User Submits Request

**Portal user** logs in and goes to `/my/tools`:

1. Browses available tools → clicks **View Details** on "Bosch Impact Drill"
2. Sees tool info, status badge (green = available)
3. Clicks **Apply to Borrow** (申請借用)
4. Optionally enters notes → clicks **Submit**
5. Loan is created and auto-submitted → status: **Pending** (待審核)

**Internal user** can also submit from the backend:

1. Go to **Tool Borrow → My Loans → New**
2. Select tool (only available tools shown in dropdown)
3. Add notes → click **Submit Request**

### B. Manager Approves

Manager goes to **Tool Borrow → Loan Requests**:

1. Sees the pending request
2. Opens it → reviews tool, borrower, notes
3. Clicks **Approve** (核准) → status: **Approved**
   - `approved_date` and `approved_by` are recorded
   - (Or clicks **Reject** → user can reset to draft and resubmit)

### C. Manager Confirms Pickup

When the user physically picks up the tool:

1. Manager opens the approved loan
2. Clicks **Confirm Borrow** (確認借出) → status: **Borrowed**
   - `borrow_date` is recorded
   - Tool state changes to `borrowed`
   - Tool is no longer available for other requests

### D. Manager Confirms Return

When the user returns the tool:

1. Manager opens the borrowed loan
2. Clicks **Confirm Return** (確認歸還) → status: **Returned**
   - `return_date` is recorded
   - Tool state changes back to `available`
   - Tool can be borrowed again

### Complete Workflow Diagram

```
Draft → [Submit] → Pending → [Approve] → Approved → [Confirm Borrow] → Borrowed → [Confirm Return] → Returned
                         ↘ [Reject] → Rejected → [Reset to Draft] → Draft
```

---

## Step 7: Ongoing Management

### View All Loans
**Tool Borrow → Loan Requests** — filter/group by tool, user, or status

### Tool Maintenance
Open a tool → click **Set to Maintenance** → tool becomes unavailable for borrowing
- Blocked if tool is currently borrowed (must return first)

### Return to Service
Open a tool in maintenance → click **Set to Available** → tool is borrowable again

### Portal User View
Portal users see their loan timeline at `/my/loans/<id>` with full status progression and all recorded dates

---

## Key Files Reference

| File | Purpose |
|---|---|
| `__manifest__.py` | Module metadata and dependencies |
| `models/tool_tool.py` | Tool, Stage, Category, Property models |
| `models/tool_loan.py` | Loan workflow with state machine |
| `models/res_users.py` | User access level field & group sync |
| `controllers/portal.py` | Portal routes (`/my/tools`, `/my/loans`) |
| `security/tool_borrow_security.xml` | Groups & record rules |
| `security/ir.model.access.csv` | Model-level CRUD permissions |
| `views/portal_templates.xml` | Portal UI (Traditional Chinese) |
| `data/tool_stage_data.xml` | Default stages & category |
