<p align="center">
  <img src="tool_borrow/static/description/icon.png" alt="Tool Borrow" width="120"/>
</p>

<h1 align="center">Odoo Tool / Device Borrow Management</h1>

<p align="center">
  <strong>Complete tool and device borrowing management for Odoo 18</strong><br/>
  Approval workflow · Portal self-service · Role-based access control
</p>

<p align="center">
  <a href="#features">Features</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#screenshots">Screenshots</a> &bull;
  <a href="#installation">Installation</a> &bull;
  <a href="#configuration">Configuration</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#testing">Testing</a> &bull;
  <a href="README_zh_TW.md">中文文件</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Odoo-18.0-purple?logo=odoo" alt="Odoo 18"/>
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/License-LGPL--3-green" alt="License"/>
  <img src="https://img.shields.io/badge/Tests-154%2F154%20PASS-brightgreen" alt="Tests"/>
</p>

---

## Overview

**Tool Borrow** is a production-ready Odoo 18 module that streamlines internal tool and device lending within organizations. It provides a full loan lifecycle with manager approval, a branded portal for end users, and fine-grained access control — all integrated with Odoo's mail and notification system.

<p align="center">
  <img src="docs/screenshots/portal_tools.png" alt="Portal Tools Overview" width="720"/>
</p>

### Why This Module?

| Challenge | Solution |
|-----------|----------|
| No visibility into who has which tool | Real-time status tracking with automatic availability updates |
| Manual approval is slow and error-prone | Structured Draft → Pending → Approved → Borrowed → Returned workflow |
| End users can't self-serve | Branded portal at `/my/tools` for browsing, requesting, and tracking loans |
| Access control is all-or-nothing | Four permission levels: No Access, User, Manager, Admin |
| Tool categories have different attributes | Dynamic properties per category (e.g. Voltage, Weight, Calibration Date) |
| Import/export breaks with many2many fields | Comma-separated export for clean import/export cycles |

---

## Features

### Tool Management

- **Category-based organization** — group tools by type (power tools, measurement instruments, hand tools, etc.)
- **Auto-generated codes** — sequential `TL-001`, `TL-002`, … codes assigned automatically
- **Status tracking** — Available / Unavailable / Under Maintenance with automatic state transitions
- **Dynamic properties** — category-level property templates that apply to all tools in that category
- **Allowed users** — control which users can see and request each tool

### Loan Workflow with Approval

- **Full lifecycle** — Draft → Pending Approval → Approved → Borrowed → Returned (or Rejected)
- **Manager approval** — requests require manager sign-off before tools are released
- **Automatic availability** — tool status updates automatically when borrowed or returned
- **Reset support** — rejected or pending requests can be sent back to Draft

### Portal Self-Service

- **Tool catalog** — branded card-based layout at `/my/tools` with status indicators
- **Tool details** — individual tool pages with properties and borrow action
- **Loan tracking** — users view their loan history and current requests at `/my/loans`
- **Borrow requests** — submit requests with optional notes directly from the portal

### Role-Based Access Control

- **Four levels** controlled per user via Settings:

| Level | Permissions |
|-------|-------------|
| No Access | Cannot see or use the module |
| User | Browse tools, submit borrow requests |
| Manager | Approve/reject requests, confirm borrow and return |
| Admin | Full access including configuration and tool categories |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Tool Borrow Module (tool_borrow)            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  tool.tool    │  │  tool.loan   │  │  tool.category   │   │
│  │              │  │              │  │                  │   │
│  │ • Name/Code  │  │ • Workflow   │  │ • Name           │   │
│  │ • Category   │  │ • Approval   │  │ • Properties     │   │
│  │ • Status     │  │ • Borrower   │  │ • Tool count     │   │
│  │ • Properties │  │ • Dates      │  │                  │   │
│  │ • Allowed    │  │ • Notes      │  │                  │   │
│  │   Users      │  │              │  │                  │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                 │                    │             │
│         └────────┬────────┘────────────────────┘             │
│                  │                                           │
│  ┌───────────────▼──────────────────────────────────────┐   │
│  │              Controllers (Portal)                     │   │
│  │                                                       │   │
│  │  /my/tools ──── Tool Catalog (card grid)              │   │
│  │  /my/tools/<id> ── Tool Detail + Borrow Action        │   │
│  │  /my/loans ──── Loan History                          │   │
│  │  /my/loans/<id> ── Loan Detail                        │   │
│  └───────────────────────────────────────────────────────┘   │
│                  │                                           │
│  ┌───────────────▼──────────────────────────────────────┐   │
│  │              Security Layer                           │   │
│  │                                                       │   │
│  │  Groups: base user │ manager │ admin                  │   │
│  │  Record Rules: per-user tool visibility               │   │
│  │  Portal Access: portal users via allowed_user_ids     │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                         Odoo 18 Framework                    │
│           base │ mail │ portal                               │
└──────────────────────────────────────────────────────────────┘
```

### Module Structure

```
tool_borrow/
├── controllers/
│   └── portal.py              # Portal routes (/my/tools, /my/loans)
├── data/
│   ├── tool_category_data.xml # Default category data
│   └── tool_sequence_data.xml # Auto-generated tool codes (TL-XXX)
├── i18n/
│   └── zh_TW.po               # Traditional Chinese translations
├── models/
│   ├── res_users.py           # User access level extension
│   ├── tool_loan.py           # Loan request model & workflow
│   └── tool_tool.py           # Tool/device model & categories
├── security/
│   ├── ir.model.access.csv    # Model-level access rights
│   └── tool_borrow_security.xml  # Groups & record rules
├── static/
│   ├── description/
│   │   ├── icon.png           # Module icon
│   │   ├── tool_form.png      # Backend screenshot
│   │   └── category_list.png  # Backend screenshot
│   └── src/css/
│       └── portal_brand.css   # Portal design system (Woowtech brand)
├── tests/
│   ├── test_round1_models.py      # Model CRUD & workflow (30 tests)
│   ├── test_round2_security.py    # Access control & permissions (30 tests)
│   ├── test_round3_http.py        # Portal HTTP endpoints (30 tests)
│   ├── test_round4_browser.py     # Browser UI tests (34 tests)
│   └── test_round5_supplementary.py  # Edge cases & coverage (30 tests)
├── views/
│   ├── menu_views.xml         # Menu structure
│   ├── portal_templates.xml   # Portal templates (branded)
│   ├── res_users_views.xml    # User form extension
│   ├── tool_loan_views.xml    # Loan list/form views
│   └── tool_tool_views.xml    # Tool list/form views
├── __init__.py
└── __manifest__.py
```

---

## Screenshots

### Backend — Tool List

All tools at a glance with status, category, allowed users, and current borrower.

<p align="center">
  <img src="docs/screenshots/tool_list.png" alt="Tool List View" width="720"/>
</p>

### Backend — Tool Form

Detailed tool view with dynamic properties, allowed users, and loan history.

<p align="center">
  <img src="docs/screenshots/tool_form.png" alt="Tool Form View" width="720"/>
</p>

### Backend — Loan Requests

Track all borrow requests with status, dates, and approval workflow.

<p align="center">
  <img src="docs/screenshots/loan_list.png" alt="Loan Request List" width="720"/>
</p>

### Backend — Loan Form

Individual loan request with approval buttons and status tracking.

<p align="center">
  <img src="docs/screenshots/loan_form.png" alt="Loan Form View" width="720"/>
</p>

### Backend — Tool Categories

Configure categories with dynamic property templates.

<p align="center">
  <img src="docs/screenshots/category_list.png" alt="Tool Categories" width="720"/>
</p>

### Backend — User Access Settings

Per-user access level configuration (No Access / User / Manager / Admin).

<p align="center">
  <img src="docs/screenshots/user_access.png" alt="User Access Settings" width="720"/>
</p>

### Portal — Tool Catalog

Branded card layout with availability indicators and category tags.

<p align="center">
  <img src="docs/screenshots/portal_tools.png" alt="Portal Tool Catalog" width="720"/>
</p>

### Portal — Tool Detail

Individual tool page with properties and borrow action button.

<p align="center">
  <img src="docs/screenshots/portal_tool_detail.png" alt="Portal Tool Detail" width="720"/>
</p>

### Portal — Loan History

Users track their borrow requests and current loans.

<p align="center">
  <img src="docs/screenshots/portal_loans.png" alt="Portal Loan History" width="720"/>
</p>

### Portal — Loan Detail

Detailed loan status with timeline.

<p align="center">
  <img src="docs/screenshots/portal_loan_detail.png" alt="Portal Loan Detail" width="720"/>
</p>

---

## Installation

### Prerequisites

- **Odoo 18.0** (Community or Enterprise)
- **Python 3.10+**
- Core modules: `base`, `mail`, `portal` (included in Odoo)

### Steps

1. Copy the `tool_borrow` folder into your Odoo addons directory:

   ```bash
   git clone https://github.com/WOOWTECH/Odoo_tool-device_borrow.git
   cp -r Odoo_tool-device_borrow/tool_borrow /path/to/odoo/addons/
   ```

2. Restart Odoo or update the apps list:

   **Settings → Technical → Update Apps List**

3. Install the module:

   **Apps → Search "Tool Borrow" → Install**

---

## Configuration

### 1. Set User Access Levels

Navigate to **Settings → Users & Companies → Users**, select a user, and set the **Tool Borrow Access** field:

| Level | Permissions |
|-------|-------------|
| No Access | Cannot see or use the module |
| User | Browse tools, submit borrow requests |
| Manager | Approve/reject requests, confirm borrow and return |
| Admin | Full access including configuration |

### 2. Create Tool Categories

Go to **Tool Borrow → Configuration → Tool Categories**.

Categories group tools and define dynamic property templates (e.g. "Voltage", "Weight", "Calibration Date") that automatically apply to all tools in that category.

### 3. Add Tools

Navigate to **Tool Borrow → Tools → New**:

- **Name** — descriptive tool name
- **Code** — auto-generated as `TL-XXX` (leave as "New")
- **Category** — determines available dynamic properties
- **Allowed Users** — which portal/internal users can see and request this tool

---

## Usage

### Loan Lifecycle

```
Draft ──► Pending Approval ──► Approved ──► Borrowed ──► Returned
                            ↘ Rejected
```

Rejected or pending requests can be reset back to Draft.

### For End Users (Portal)

1. Log in and navigate to **`/my/tools`**
2. Browse the tool catalog with status indicators
3. Click a tool to view details and properties
4. Click **Borrow** and add optional notes
5. Track request status at **`/my/loans`**

### For Managers (Backend)

1. Open **Tool Borrow → Borrow Requests**
2. **Approve** or **Reject** pending requests
3. Click **Confirm Borrow** when the tool is handed over
4. Click **Confirm Return** when the tool comes back — status resets to Available

---

## Testing

The module includes a comprehensive test suite of **154 test cases** organized across five rounds:

| Round | Focus | Tests | Status |
|-------|-------|-------|--------|
| Round 1 | Model CRUD & Workflow | 30 | ✅ PASS |
| Round 2 | Security & Access Control | 30 | ✅ PASS |
| Round 3 | Portal HTTP Endpoints | 30 | ✅ PASS |
| Round 4 | Browser UI (Playwright) | 34 | ✅ PASS |
| Round 5 | Edge Cases & Supplementary | 30 | ✅ PASS |
| **Total** | | **154** | **✅ ALL PASS** |

### Running Tests

```bash
# Run all tests via XML-RPC test runner
python3 tests/test_round1_models.py
python3 tests/test_round2_security.py
python3 tests/test_round3_http.py
python3 tests/test_round4_browser.py
python3 tests/test_round5_supplementary.py
```

---

## License

**LGPL-3** — GNU Lesser General Public License v3.

## Author

**WoowTech** — [https://aiot.woowtech.io/](https://aiot.woowtech.io/)
