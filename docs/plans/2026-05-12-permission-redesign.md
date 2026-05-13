# 工具借用模組權限重設計：從 3 層自訂架構改為 Odoo 原生 2 層設計

## 目標

將工具借用模組的權限從自訂的 3 層架構（User / Manager / Admin + `tool_borrow_access` 欄位）
改為跟保養模組 (maintenance) 一樣的 Odoo 原生 2 層設計（內部使用者 + 設備管理員）。

## 設計決策

| 決策項 | 選擇 |
|--------|------|
| 層級數量 | 2 層（內部使用者 + 設備管理員） |
| 設備管理員權限 | 等同現在的 Admin（全部權限） |
| 一般內部使用者 | 瀏覽工具（唯讀）+ 建立/查看自己的借用申請 |
| Portal 使用者 | 保留，等同一般內部使用者 |
| UI 呈現 | Odoo 原生 `sel_groups` 在「存取權」分頁自動顯示 |
| 群組名稱 | 「設備管理員」（Equipment Manager） |

## 新的權限矩陣

### 角色對照

| 舊角色 | 新角色 | 說明 |
|--------|--------|------|
| group_tool_user | base.group_user（內部使用者） | 不再需要獨立群組 |
| group_tool_manager | **移除** | 合併到設備管理員 |
| group_tool_admin | **group_tool_manager**（設備管理員） | 重新命名，唯一的自訂群組 |

### ACL（ir.model.access.csv）

| Model | 內部使用者 (base.group_user) | 設備管理員 (group_tool_manager) | Portal (base.group_portal) |
|-------|-----|-----|-----|
| tool.tool | R | RWCD | R |
| tool.loan | RWCD | RWCD | RWC |
| tool.property | R | RWCD | R |
| tool.stage | R | RWCD | R |
| tool.category | R | RWCD | R |

### Record Rules（ir.rule）

| Model | 內部使用者 | 設備管理員 | Portal |
|-------|-----------|-----------|--------|
| tool.tool | 唯讀全部 | 全部 CRUD | 唯讀全部 |
| tool.loan | 自己的（read + create/write） | 全部 CRUD | 自己的（read + create/write） |
| tool.property | 唯讀全部 | 全部 CRUD | 唯讀全部 |
| tool.stage | 唯讀全部 | 全部 CRUD | 唯讀全部 |
| tool.category | 唯讀全部 | 全部 CRUD | 唯讀全部 |

### 選單結構

```
工具借用 (root)            ← base.group_user + base.group_portal
├── 工具                   ← base.group_user + base.group_portal
├── 借用申請               ← group_tool_manager（設備管理員限定）
├── 我的借用               ← base.group_user + base.group_portal
└── 設定                   ← group_tool_manager（設備管理員限定）
    ├── 工具階段
    └── 工具類別
```

### 按鈕群組

| 按鈕 | 群組限制 |
|------|---------|
| Approve / Reject | group_tool_manager |
| Confirm Borrow / Confirm Return | group_tool_manager |
| Set to Maintenance / Set to Available | group_tool_manager |

## 需要修改的檔案

### 1. `security/tool_borrow_security.xml`
- 移除 `group_tool_user` 和 `group_tool_admin`
- 將 `group_tool_manager` 改名為 Equipment Manager（設備管理員）
- 移除 implied_ids（不再需要繼承鏈）
- 移除所有引用 `group_tool_user` 和 `group_tool_admin` 的 record rules
- 重寫 record rules：只需要 base.group_user + group_tool_manager + base.group_portal

### 2. `security/ir.model.access.csv`
- 移除所有 `group_tool_user` 和 `group_tool_admin` 的行
- 新增 `group_tool_manager` 的行（RWCD）
- 保留 `base.group_user` 和 `base.group_portal` 的行

### 3. `models/res_users.py`
- 移除 `tool_borrow_access` 欄位
- 移除 `_onchange_tool_borrow_access` 方法
- 移除 `_update_tool_borrow_groups` 方法
- 移除 `write` 和 `create` 覆寫
- 如果檔案變空，從 `__init__.py` 中移除 import

### 4. `views/res_users_views.xml`
- 移除整個自訂的 Tool Borrow 分頁
- Odoo 會自動在「存取權」分頁顯示設備管理員選項

### 5. `views/menu_views.xml`
- `group_tool_user` → `base.group_user`
- `group_tool_manager` → `group_tool_manager`（名稱不變但意義變了）
- `group_tool_admin` → `group_tool_manager`

### 6. `views/tool_loan_views.xml`
- 4 個按鈕：`group_tool_manager` 保持不變

### 7. `views/tool_tool_views.xml`
- 2 個按鈕：`group_tool_admin` → `group_tool_manager`

### 8. `models/tool_loan.py`
- `_check_manager_access`：`group_tool_manager` 保持不變

### 9. `i18n/zh_TW.po`
- 更新群組名稱翻譯
- 移除 tool_borrow_access 相關翻譯

### 10. `controllers/portal.py`
- 無需修改（沒有引用舊的權限欄位）

## 存取權分頁預期效果

修改後，使用者表單的「存取權」分頁會自動顯示：

```
工具借用
  ○ (空白)          ← 一般內部使用者，可瀏覽工具和管理自己的借用
  ◉ 設備管理員       ← 全部權限
```

跟保養模組的顯示方式完全一致。
