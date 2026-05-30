# Task Plan: Portal Page Audit & Sample Data Completion

## Goal
Audit every portal page for the 3 new module groups (Community, HA, Loyalty), check:
1. Each page has ~20 sample records visible to portal user
2. Visual design is consistent across all pages (Odoo 18 native portal style)

## Modules & Routes

### Community Package (community_base, community_parcel, community_visitor)
| Page | Route | Current Records | Target |
|------|-------|----------------|--------|
| Announcements | /my/announcements | 3 | ~20 |
| Feedbacks | /my/feedbacks | 3 | ~20 |
| Parcels | /my/parcels | 3 | ~20 |
| Visitors (Visits) | /my/visitors | 3 | ~20 |
| Appointments | /my/appointments | 2 | ~20 |

### HA Addon (odoo_ha_addon)
| Page | Route | Current Records | Target |
|------|-------|----------------|--------|
| HA Home | /my/ha | 1 instance, 7 entities, 3 devices | Check if detail pages work |
| HA Entities | /my/ha/instance/1/entities | ? | ~20 entities |
| HA Devices | /my/ha/instance/1/devices | 3 | ~20 devices |

### Loyalty / Member Center (woow_member_center + 6 mc modules)
| Page | Route | Current Records | Target |
|------|-------|----------------|--------|
| Member Center Hub | /my/member-center | hub page | N/A (links only) |
| Consign Cards | /my/consign-cards | 1 card | ~5 cards with lines |
| Loyalty Cards | /my/member-center/loyalty | 1 card | ~5 cards |
| Gift Cards | /my/member-center/gift-cards | 1 card | ~5 cards |
| eWallet | /my/member-center/ewallet | 1 card | ~5 cards |
| Coupons | /my/member-center/coupons | 1 card | ~5 coupons |
| Membership | /my/member-center/membership | 0? | ~5 memberships |

## Phases

### Phase 1: Audit - Screenshot & count records on every page [in_progress]
- Take screenshots of all list pages
- Count visible records
- Note visual inconsistencies

### Phase 2: Create missing sample data [pending]
- Community: Add ~17 more records per model
- HA: Add more entities/devices if needed
- Loyalty: Add more cards/programs

### Phase 3: Visual consistency check [pending]
- Compare searchbar, sorting, filtering, paging across all pages
- Check breadcrumbs, status badges, table headers
- Note any design inconsistencies

### Phase 4: Fix visual inconsistencies [pending]
- Align designs where needed

### Phase 5: Final verification [pending]
- Re-screenshot all pages
- Confirm ~20 records visible
- Confirm consistent design

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | | |
