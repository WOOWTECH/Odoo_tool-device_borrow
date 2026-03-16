# Tool Borrow

> [中文版 README](README_zh_TW.md)

A tool and device borrowing management module for **Odoo 18**.

## Features

- **Tool management** — track tools by category with status (Available / Unavailable / Under Maintenance), auto-generated codes, and dynamic properties per category.
- **Loan workflow with approval** — Draft → Pending → Approved → Borrowed → Returned (or Rejected). Managers approve or reject requests; the system updates tool availability automatically.
- **Portal self-service** — portal users browse available tools at `/my/tools` and submit borrow requests with notes.
- **Role-based access** — four levels controlled per user: No Access, User, Manager, Admin.
- **Export-friendly** — many2many fields (e.g. Allowed Users) export as comma-separated values in a single cell for clean import/export cycles.

## Installation

### Prerequisites

- Odoo 18
- Modules: `base`, `mail`, `portal` (included in Odoo core)

### Steps

1. Copy the `tool_borrow` folder into your Odoo addons directory.
2. Restart Odoo (or update the apps list via **Settings → Technical → Update Apps List**).
3. Go to **Apps**, search for "Tool Borrow", and click **Install**.

## Configuration

### 1. Set User Access

Go to **Settings → Users & Companies → Users**, select a user, and find the **Tool Borrow Access** field under the **Tool Borrow** section:

| Level | Permissions |
|-------|-------------|
| No Access | Cannot see or use the module |
| User | Browse tools, submit borrow requests |
| Manager | Approve/reject requests, confirm borrow and return |
| Admin | Full access including configuration |

### 2. Create Tool Categories

Navigate to **Tool Borrow → Configuration → Tool Categories**. Categories group tools and define dynamic property templates (e.g. "Voltage", "Weight") that apply to all tools in the category.

### 3. Create Tools

Go to **Tool Borrow → Tools**, click **New**, and fill in:

- **Name** and **Code** (auto-generated if left as "New")
- **Category** — determines available dynamic properties
- **Allowed Users** — which users can see and request this tool

## Usage

### For Users (Portal)

1. Log in to the portal and navigate to `/my/tools`.
2. Browse available tools and click one to view details.
3. Click **Borrow** and add optional notes.
4. The request moves to **Pending Approval** status.

### For Managers (Backend)

1. Open **Tool Borrow → Loan Requests** to see pending requests.
2. **Approve** or **Reject** each request.
3. When the borrower picks up the tool, click **Confirm Borrow**.
4. When the tool is returned, click **Confirm Return** — the tool status resets to Available.

### Loan Lifecycle

```
Draft → Pending Approval → Approved → Borrowed → Returned
                         ↘ Rejected
```

Rejected or pending requests can be reset back to Draft.

## License

**LGPL-3** — GNU Lesser General Public License v3.

## Author

**WoowTech** — [https://aiot.woowtech.io/](https://aiot.woowtech.io/)
