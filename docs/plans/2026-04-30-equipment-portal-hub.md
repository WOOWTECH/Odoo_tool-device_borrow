# 設備借用中間頁設計

## 目標

將總覽頁的「工具」和「我的借用」兩張獨立卡片合併為一張「設備借用」入口卡片，點擊後進入新的中間頁面 `/my/equipment`，該頁面再分為「設備工具」和「我的借用」兩張卡片。

## 結構

```
/my/home (總覽頁)
├── 設備借用 → /my/equipment (新整合 SVG 圖示)
└── 連線及保安 → /my/security (不變)

/my/equipment (新中間頁)
├── 麵包屑：首頁 / 設備借用
├── 設備工具 → /my/tools (tools.svg)
└── 我的借用 → /my/loans (loans.svg)
```

## 改動檔案

1. **`views/portal_templates.xml`** — 總覽頁改為單一「設備借用」卡片 + 新增 equipment 頁面模板
2. **`controllers/portal.py`** — 新增 `/my/equipment` 路由
3. **`static/src/img/equipment.svg`** — 全新整合 SVG（扳手+借還箭頭，Odoo 原生多色插圖風）
4. **`i18n/zh_TW.po`** — 翻譯更新

## 卡片規格

### 總覽頁「設備借用」卡片
- 標題：Equipment Borrowing (設備借用)
- 描述：Browse equipment and manage borrowing (瀏覽設備工具及借還管理)
- 圖示：equipment.svg (新)
- URL：/my/equipment

### 中間頁「設備工具」卡片
- 標題：Equipment Tools (設備工具)
- 描述：Browse available tool equipment (瀏覽可用的工具設備)
- 圖示：tools.svg (現有)
- URL：/my/tools

### 中間頁「我的借用」卡片
- 標題：My Loans (我的借用)
- 描述：View and manage loan records (查看與管理借用紀錄)
- 圖示：loans.svg (現有)
- URL：/my/loans
