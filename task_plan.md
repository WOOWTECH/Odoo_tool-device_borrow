# Task Plan: Fix Chinese Translations for All Custom Modules

## Goal
Fix zh_TW (Traditional Chinese) translations for all portal pages across Community, HA, and Loyalty modules on odoo-toolborrow (port 9076).

## Root Cause
The .po files use `model:ir.ui.view,arch_db:...` format but Odoo 18 requires `model_terms:ir.ui.view,arch_db:...` for QWeb template string translations. The `model` type tries to replace the entire field value, while `model_terms` replaces individual translatable strings within the JSONB `arch_db` field.

## Affected Modules (11)
- community_base, community_parcel, community_visitor
- odoo_ha_addon
- woow_member_center, woow_mc_loyalty, woow_mc_consign, woow_mc_coupon, woow_mc_ewallet, woow_mc_gift_card, woow_mc_membership

## Phases

### Phase 1: Export correct .pot files from Odoo — `pending`
Use Odoo's translation export to generate .pot files with correct `model_terms` references for each module.

### Phase 2: Rebuild zh_TW.po files — `pending`
- Use the exported .pot as template
- Merge existing Chinese translations from current .po files
- Fill in any remaining untranslated strings
- Ensure all QWeb view entries use `model_terms:ir.ui.view,arch_db:` format

### Phase 3: Deploy and reload translations — `pending`
- Copy updated .po files to container addons
- Run `odoo -u <modules> --load-language=zh_TW --stop-after-init`
- Verify translations stored in DB (check JSONB `arch_db` has `zh_TW` key)

### Phase 4: Verify all portal pages display Chinese — `pending`
- Screenshot all 15 pages
- Check no English UI strings remain (breadcrumbs, column headers, buttons, labels)
- Compare with 9077 reference

### Phase 5: Update source repos — `pending`
- Copy corrected .po files back to source repos
- Commit changes

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| .po uses `model:` instead of `model_terms:` | 1 | Need to regenerate .pot with correct type |
| `base.update.translations` doesn't exist in Odoo 18 | 1 | Use CLI `odoo -u` instead |
| Cron lock error during XML-RPC module upgrade | 1 | Use standalone CLI container |
| `ir.translation` model removed in Odoo 18 | 1 | Translations now in JSONB `arch_db` field |
