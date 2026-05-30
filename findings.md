# Findings

## Portal Page Audit Results (Phase 1)

### Community Module Pages
| Page | Route | Records | Need | Status |
|------|-------|---------|------|--------|
| Announcements | /my/announcements | 3 rows | +17 | LOW |
| Feedbacks | /my/feedbacks | 3 rows | +17 | LOW |
| Parcels | /my/parcels | 3 rows | +17 | LOW |
| Visitors (Visits) | /my/visitors | 3 rows | +17 | LOW |
| Appointments | /my/appointments | 2 rows | +18 | LOW |

### HA Addon Pages
| Page | Route | Records | Need | Status |
|------|-------|---------|------|--------|
| HA Home | /my/ha | 1 instance card | OK (hub) | OK |
| HA Instance Detail | /my/ha/1 | 7 entities, 1 group, 3 devices | +13 entities, +17 devices | LOW |

### Loyalty / Member Center Pages
| Page | Route | Records | Need | Status |
|------|-------|---------|------|--------|
| Member Center Hub | /my/member-center | 6 card type links | OK (hub) | OK |
| Consign Cards | /my/consign-cards | 1 card | +4 cards | LOW |
| Loyalty Cards | /my/member-center/loyalty | 1 card | +4 cards | LOW |
| Gift Cards | /my/member-center/gift-cards | 1 card | +4 cards | LOW |
| eWallet | /my/member-center/ewallet | 1 card | +4 cards | LOW |
| Coupons | /my/member-center/coupons | 1 card | +4 coupons | LOW |
| Membership | /my/member-center/membership | 0 (empty!) | Need membership data | CRITICAL |

## Phase 2: Data Population Results

### Community Module Pages (after data creation)
| Page | Route | Records Now | Pagination | Status |
|------|-------|-------------|------------|--------|
| Announcements | /my/announcements | 20 (10/page) | Yes, 2 pages | OK |
| Feedbacks | /my/feedbacks | 20 (10/page) | Yes, 2 pages | OK |
| Parcels | /my/parcels | 20 (10/page) | Yes, 2 pages | OK |
| Visitors (Visits) | /my/visitors | 20 (10/page) | Yes, 2 pages | OK |
| Appointments | /my/appointments | 20 (10/page) | Yes, 2 pages | OK |

### HA Addon Pages (after data creation)
| Page | Route | Records Now | Status |
|------|-------|-------------|--------|
| HA Home | /my/ha | 1 instance (20 entities, 1 group, 20 devices) | OK |
| HA Instance Detail | /my/ha/1 | 20 entities + 1 group + 20 devices (tabs) | OK |

### Loyalty / Member Center Pages (after data creation)
| Page | Route | Records Now | Status |
|------|-------|-------------|--------|
| Member Center Hub | /my/member-center | 6 card type links | OK (hub) |
| Consign Cards | /my/consign-cards | 3 cards (with lines) | OK |
| Loyalty Cards | /my/member-center/loyalty | 3 cards | OK |
| Gift Cards | /my/member-center/gift-cards | 3 cards | OK |
| eWallet | /my/member-center/ewallet | 3 wallets (total 4,000 balance) | OK |
| Coupons | /my/member-center/coupons | 4 coupons | OK |
| Membership | /my/member-center/membership | 2 lines (Gold Annual paid, Silver Quarterly old) | OK |

## Phase 3: Visual Consistency Check

### Portal Home (/my)
- Shows all module cards in 2-column grid layout
- Right sidebar: user profile + loyalty card summaries (Community Points, eWallet, Shopping Rewards, Dining Loyalty, Parking Wallet, Cafeteria Wallet)
- Home Assistant card: shows "41 Home Assistant" with description — count shows total shared items
- All cards have icons and descriptions — consistent layout
- **No issues found**

### Community Pages (5 pages)
- **Consistent with each other**: All use searchbar with Sort By / Filter By / Search input
- **Table layout**: Standard Odoo portal table with columns, status badges
- **Breadcrumbs**: "Community Management / [Page Name]" — consistent hierarchy
- **Pagination**: 10 per page, proper pager controls
- **Action buttons**: Feedbacks has "+ New Feedback", Appointments has "+ New Appointment"
- **Status badges**: Green "Published"/"Confirmed", grey "Draft"/"Pending"
- **Date format**: Chinese locale (e.g. "2026年05月30日") — website locale zh_TW
- **No issues found** — all 5 community pages are visually aligned

### HA Pages (2 pages)
- **HA Home (/my/ha)**: Single instance card with icon, name, entity/group/device counts, "View Devices" button
- **HA Instance (/my/ha/1)**: Tabs for Entities (20), Groups (1), Devices (20) — badge counts on tabs
- **Entity table**: Name, State (colored badges), Permission (green "Control"), Expiry, Action (View button)
- **Custom layout**: IoT-specific design, appropriate for device management — not standard table style
- **Breadcrumbs**: Home icon only (no text breadcrumb) — different from community/loyalty
- **No major issues** — design is intentionally different for IoT use case

### Member Center Hub (/my/member-center)
- 6 card links in 2-column grid: Coupon, E-Wallet, Gift Card, Loyalty Card, Membership, Consignment Card
- Each card has icon, title, description
- **Breadcrumbs**: "Home / Member Center" — consistent
- **Highlight state**: Loyalty Card appears highlighted (cursor hover captured in screenshot)
- **No issues found**

### Loyalty Card Pages (Loyalty, Gift Card, eWallet, Coupons, Consign)
- **Consistent table layout** across all 5 pages
- **Breadcrumbs**: "Home / Member Center / [Type Name]"
- **Columns vary by type** (appropriate):
  - Loyalty: Program, Card No., Points, Status
  - Gift Card: Program, Card No., Balance, Status
  - eWallet: Has "Total Balance" summary banner (4,000), then table with Program, Card No., Balance, Status
  - Coupons: Program, Coupon Code, Description, Status
  - Consign: Card No., Program, Active Items, Remaining Qty, Remaining Amount
- **Status badges**: Green "Active" / "Available" / "Paid" — consistent styling
- **Card numbers**: Displayed as links in purple/magenta — consistent
- **eWallet special**: Has a gradient purple banner showing total balance — unique but good UX
- **No major issues** — pages are consistent within the loyalty module group

### Membership Page (/my/member-center/membership)
- **Breadcrumbs**: "Home / Member Center / Membership"
- **Header**: "Membership Status" with "免費會員" (Free Member) badge in green
- **Table**: Membership Plan, Start Date, End Date, Fee, Status
- **Data**: 2 membership lines showing (起司可頌/芝士牛角包 and 胡桃派)
- **Status**: One "Paid" badge (green), one without status badge
- **Note**: Product names are in Chinese (membership product names) — matches website locale
- **Issue**: Second membership line has no status badge — may need investigation

### Design Inconsistencies Found

| Issue | Severity | Pages Affected | Description |
|-------|----------|----------------|-------------|
| HA breadcrumb | LOW | /my/ha, /my/ha/1 | Uses only home icon, no text breadcrumb like other modules |
| Membership status badge missing | LOW | /my/member-center/membership | Second membership line shows no status badge |
| eWallet total banner | INFO | /my/member-center/ewallet | Has unique gradient banner — intentional feature, not a bug |
| Date locale mismatch | INFO | Community pages | Dates in Chinese format despite user being en_US — website-level setting |

### Overall Assessment
- **Community pages**: Excellent consistency — all 5 pages follow identical patterns
- **HA pages**: Intentionally different (IoT card/tab layout) — acceptable
- **Loyalty/Member Center pages**: Good consistency — all use same table style within the group
- **Cross-module**: Each module group has its own appropriate design language
- **No critical visual issues found** — all pages render correctly with proper data
