# Portal Home Page Redesign — Tool Equipment Section

## Summary

Restructure the portal home page (`/my/home`) to group "Tools" and "My Loans" under a single **"Tool Equipment"** section header, replace MDI font icons with custom SVG illustrations matching Odoo's native style, and restore the Security card to its native SVG icon.

## Current State

- 3 cards in `portal_client_category`: Tools, My Loans, Security
- All use MDI (Material Design Icons) font icons
- Odoo native modules use SVG illustrations (64x64, multi-color)

## Design Decisions

1. **Section grouping**: "Tools" and "My Loans" stay as two separate cards inside a section titled "Tool Equipment"
2. **Card click behavior**: Each card links to its original list page (`/my/tools`, `/my/loans`)
3. **Icons**: New custom SVG illustrations matching Odoo's native style palette (`#374874` outlines, `#C1DBF6` fills, `#FBDBD0` accents, `white` highlights)
4. **Security card**: Restore to Odoo's native `portal-connection.svg`
5. **Card labels**:
   - Card 1: title="Tools", text="Browse available tool equipment"
   - Card 2: title="My Loans", text="View and manage loan records"
   - Section title: "Tool Equipment"

## Implementation Plan

### 1. Create SVG Icons

- `tool_borrow/static/src/img/tools.svg` — wrench/tool illustration (64x64)
- `tool_borrow/static/src/img/loans.svg` — clipboard with clock illustration (64x64)
- Style: Odoo native palette — `#374874` dark outlines, `#C1DBF6` blue fills, `#FBDBD0` pink accents, `white` body fills

### 2. Update portal_templates.xml

- Switch from `portal_docs_entry_mdi` to standard `portal.portal_docs_entry`
- Pass `icon` parameter with SVG path instead of `icon_class` with MDI class
- Remove MDI override of Security card (restore native behavior)
- Section title uses `portal_client_category` with appropriate label

### 3. Clean Up

- The `portal_docs_entry_mdi` template can be removed if no other cards use it
- MDI CSS CDN link can be kept (used on other portal pages for header icons)

## Files Modified

- `tool_borrow/static/src/img/tools.svg` (NEW)
- `tool_borrow/static/src/img/loans.svg` (NEW)
- `tool_borrow/views/portal_templates.xml` (MODIFIED)
