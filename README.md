# Odoo Tool/Device Borrow Management

An Odoo 18 module for managing tool and device borrowing within organizations.

## Features

- **Tool Management**: Track all tools and devices available for borrowing
- **Loan Management**: Complete workflow for borrowing and returning items
- **Employee Self-Service Portal**: Employees can request and return tools via web portal
- **Inventory Tracking**: Real-time availability status of all tools
- **Multi-language Support**: Traditional Chinese (zh_TW) and English

## Requirements

- Odoo 18.0
- Python 3.10+

## Dependencies

- `base`
- `mail`
- `portal`
- `hr`

## Installation

1. Clone this repository to your Odoo addons directory:
   ```bash
   git clone https://github.com/WOOWTECH/Odoo_tool-device_borrow.git
   ```

2. Update the addons path in your Odoo configuration

3. Restart Odoo server

4. Go to Apps menu and install "Tool Borrow Management"

## Module Structure

```
tool_borrow/
├── controllers/
│   └── portal.py          # Portal controllers for self-service
├── data/
│   └── tool_stage_data.xml # Default stages configuration
├── i18n/
│   └── zh_TW.po           # Traditional Chinese translations
├── models/
│   ├── res_users.py       # User extensions
│   ├── tool_loan.py       # Loan management model
│   └── tool_tool.py       # Tool/device model
├── security/
│   ├── ir.model.access.csv
│   └── tool_borrow_security.xml
├── views/
│   ├── menu_views.xml
│   ├── portal_templates.xml
│   ├── res_users_views.xml
│   ├── tool_loan_views.xml
│   └── tool_tool_views.xml
├── __init__.py
└── __manifest__.py
```

## Usage

### Backend (Administrators)

1. Navigate to **Tool Management** menu
2. Add tools/devices to the system
3. Manage loan requests and returns
4. Track tool availability and history

### Portal (Employees)

1. Access the portal via `/my/tools`
2. Browse available tools
3. Submit borrow requests
4. Return tools when done

## License

LGPL-3

## Author

WOOWTECH

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/WOOWTECH/Odoo_tool-device_borrow/issues) page.
