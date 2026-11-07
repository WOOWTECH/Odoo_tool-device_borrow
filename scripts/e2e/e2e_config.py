# -*- coding: utf-8 -*-
"""Connection settings and shared helpers for the standalone E2E scripts.

These scripts drive a *running* Odoo instance over XML-RPC / HTTP (and
Playwright for round 4).  They are NOT Odoo unit tests: they live outside the
shipped ``tool_borrow/`` module, are never loaded by ``--test-enable`` and are
never referenced by the module.  The module's own regression tests are in
``tool_borrow/tests/``.

Credentials are read from the environment; no password has a default:

    TB_E2E_URL                 default http://localhost:8069
    TB_E2E_DB                  required
    TB_E2E_ADMIN_LOGIN         default admin
    TB_E2E_ADMIN_PASSWORD      required  (admin must be in Equipment Manager)
    TB_E2E_MANAGER_LOGIN       default testmanager   (internal + Equipment Manager)
    TB_E2E_MANAGER_PASSWORD    required by rounds 2, 5
    TB_E2E_USER_LOGIN          default testuser      (internal, not a manager)
    TB_E2E_USER_PASSWORD       required by rounds 2, 3, 5
    TB_E2E_PORTAL_LOGIN        default portal        (portal user)
    TB_E2E_PORTAL_PASSWORD     required by rounds 2-5
    TB_E2E_PORTAL2_LOGIN       default xiaoming      (second non-manager user)
    TB_E2E_PORTAL2_PASSWORD    required by rounds 2-5
    TB_E2E_NOACCESS_LOGIN      default noaccess      (portal user, round 4)
    TB_E2E_NOACCESS_PASSWORD   required by round 4
    TB_E2E_SCREENSHOT_DIR      default <this folder>/screenshots (round 4)
    TB_E2E_GRANT_ADMIN_MANAGER set to 1 to add the admin login to
                               tool_borrow.group_tool_manager when it is not
                               a member yet (otherwise the scripts stop)

Since 18.0.1.3.2, only Equipment Managers may create/write the workflow
fields of ``tool.loan`` (state, approved_by, approved_date, borrow_date,
return_date, request_date), create loans for somebody else or approve/reject.
The admin login used for setup and cleanup therefore has to be an Equipment
Manager, and every state change goes through the ``action_*`` methods.
"""
import os
import sys
import xmlrpc.client

HERE = os.path.dirname(os.path.abspath(__file__))

MANAGER_GROUP_XMLID = 'tool_borrow.group_tool_manager'


def _env(name, default=None, required=True):
    value = os.environ.get(name, default)
    if required and not value:
        sys.exit(f"Missing environment variable {name} "
                 f"(see scripts/e2e/e2e_config.py)")
    return value


URL = _env('TB_E2E_URL', 'http://localhost:8069').rstrip('/')
DB = _env('TB_E2E_DB')

_ROLES = {
    'admin': 'ADMIN',
    'manager': 'MANAGER',
    'user': 'USER',
    'portal': 'PORTAL',
    'portal2': 'PORTAL2',
    'noaccess': 'NOACCESS',
}
_DEFAULT_LOGINS = {
    'admin': 'admin',
    'manager': 'testmanager',
    'user': 'testuser',
    'portal': 'portal',
    'portal2': 'xiaoming',
    'noaccess': 'noaccess',
}


def login_of(role):
    """Return the login of ``role`` (no password needed)."""
    return _env('TB_E2E_' + _ROLES[role] + '_LOGIN', _DEFAULT_LOGINS[role])


def credentials(role):
    """Return ``(login, password)`` for ``role`` from the environment."""
    return login_of(role), _env('TB_E2E_' + _ROLES[role] + '_PASSWORD')


def screenshots_dir():
    path = _env('TB_E2E_SCREENSHOT_DIR', os.path.join(HERE, 'screenshots'))
    os.makedirs(path, exist_ok=True)
    return path


def _object_proxy():
    return xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)


def xmlid_to_res_id(models, uid, password, xmlid):
    module, name = xmlid.split('.', 1)
    rows = models.execute_kw(DB, uid, password, 'ir.model.data', 'search_read',
                             [[('module', '=', module), ('name', '=', name)]],
                             {'fields': ['res_id'], 'limit': 1})
    return rows[0]['res_id'] if rows else False


def default_stages(models, uid, password):
    """Return the ids of the three default stages (by XML id, since
    ``tool.stage`` no longer has ``is_closed``/``fold``)."""
    return (
        xmlid_to_res_id(models, uid, password, 'tool_borrow.tool_stage_in_service'),
        xmlid_to_res_id(models, uid, password, 'tool_borrow.tool_stage_maintenance'),
        xmlid_to_res_id(models, uid, password, 'tool_borrow.tool_stage_retired'),
    )


def ensure_admin_is_manager(models, uid, password):
    """Stop unless the setup/cleanup admin is an Equipment Manager.

    With ``TB_E2E_GRANT_ADMIN_MANAGER=1`` the admin is added to the group
    instead (a change on the target database, hence opt-in).
    """
    gid = xmlid_to_res_id(models, uid, password, MANAGER_GROUP_XMLID)
    if not gid:
        sys.exit(f"{MANAGER_GROUP_XMLID} not found - is tool_borrow installed in {DB}?")
    groups = models.execute_kw(DB, uid, password, 'res.users', 'read',
                               [[uid], ['groups_id']])[0]['groups_id']
    if gid in groups:
        return
    if os.environ.get('TB_E2E_GRANT_ADMIN_MANAGER') == '1':
        models.execute_kw(DB, uid, password, 'res.users', 'write',
                          [[uid], {'groups_id': [(4, gid)]}])
        print(f"  [SETUP] added the admin login to {MANAGER_GROUP_XMLID}")
        return
    sys.exit(f"The admin login (uid {uid}) is not in {MANAGER_GROUP_XMLID}; "
             f"add it (Settings > Users > Access Rights > Equipment Manager) "
             f"or rerun with TB_E2E_GRANT_ADMIN_MANAGER=1")


def admin_session():
    """Authenticate the admin login and check it is an Equipment Manager.

    Returns ``(uid, models_proxy, password)``.
    """
    login, password = credentials('admin')
    uid = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common').authenticate(
        DB, login, password, {})
    if not uid:
        sys.exit(f"Admin login {login!r} failed on {URL} / {DB}")
    models = _object_proxy()
    ensure_admin_is_manager(models, uid, password)
    return uid, models, password
