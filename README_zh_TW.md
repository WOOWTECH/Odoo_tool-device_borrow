# Odoo 工具/設備借用管理

一個用於組織內部工具和設備借用管理的 Odoo 18 模組。

## 功能特色

- **工具管理**：追蹤所有可供借用的工具和設備
- **借用管理**：完整的借用和歸還工作流程
- **員工自助入口**：員工可透過網頁入口申請和歸還工具
- **庫存追蹤**：即時顯示所有工具的可用狀態
- **多語言支援**：繁體中文 (zh_TW) 和英文

## 系統需求

- Odoo 18.0
- Python 3.10+

## 相依模組

- `base`
- `mail`
- `portal`
- `hr`

## 安裝方式

1. 將此儲存庫複製到您的 Odoo 附加模組目錄：
   ```bash
   git clone https://github.com/WOOWTECH/Odoo_tool-device_borrow.git
   ```

2. 更新 Odoo 設定檔中的附加模組路徑

3. 重新啟動 Odoo 伺服器

4. 前往應用程式選單並安裝「工具借用管理」

## 模組結構

```
tool_borrow/
├── controllers/
│   └── portal.py          # 自助服務入口控制器
├── data/
│   └── tool_stage_data.xml # 預設階段設定
├── i18n/
│   └── zh_TW.po           # 繁體中文翻譯
├── models/
│   ├── res_users.py       # 使用者擴充
│   ├── tool_loan.py       # 借用管理模型
│   └── tool_tool.py       # 工具/設備模型
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

## 使用方式

### 後台管理（管理員）

1. 進入 **工具管理** 選單
2. 新增工具/設備到系統中
3. 管理借用申請和歸還
4. 追蹤工具可用性和歷史記錄

### 入口網站（員工）

1. 透過 `/my/tools` 存取入口
2. 瀏覽可用工具
3. 提交借用申請
4. 使用完畢後歸還工具

## 授權條款

LGPL-3

## 作者

WOOWTECH

## 支援

如有問題或功能需求，請使用 [GitHub Issues](https://github.com/WOOWTECH/Odoo_tool-device_borrow/issues) 頁面。
