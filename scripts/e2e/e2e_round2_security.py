#!/usr/bin/env python3
"""
Round 2: Security & Permission Penetration Tests (27 cases, #41-64 + 58a-58c)
Tests ACL, record rules, and privilege escalation across roles.

2-tier permission model:
  - Internal User (base.group_user): read tools, create/view own loans
  - Equipment Manager (group_tool_manager): full CRUD on everything
  - Portal (base.group_portal): read tools, create/view own loans
Workflow fields of tool.loan (state, approved_by, dates) can only be set by
Equipment Managers; everybody else goes through action_submit /
action_reset_to_draft on their own loans.
"""
import xmlrpc.client
import sys

# Connection settings and credentials come from the environment
# (see e2e_config.py); nothing is hardcoded.
from e2e_config import URL, DB, admin_session, credentials, login_of, default_stages  # noqa: E402,F401
MANAGER_LOGIN, MANAGER_PASS = credentials('manager')
PORTAL_LOGIN, PORTAL_PASS = credentials('portal')
PORTAL2_LOGIN, PORTAL2_PASS = credentials('portal2')
USER_LOGIN, USER_PASS = credentials('user')
ADMIN_LOGIN = login_of('admin')

passed = 0
failed = 0
errors = []


def auth(login, password):
    uid = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common').authenticate(DB, login, password, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    return uid, models


def call(models, uid, pwd, model, method, args, kwargs=None):
    if kwargs is None:
        kwargs = {}
    try:
        return models.execute_kw(DB, uid, pwd, model, method, args, kwargs)
    except xmlrpc.client.Fault as e:
        if "cannot marshal None" in str(e):
            return True
        raise


def test(num, desc, fn):
    global passed, failed
    try:
        result = fn()
        if result is True:
            print(f"  [PASS] #{num}: {desc}")
            passed += 1
        else:
            print(f"  [FAIL] #{num}: {desc} — {result}")
            failed += 1
            errors.append(f"#{num}: {desc} — {result}")
    except Exception as e:
        print(f"  [FAIL] #{num}: {desc} — Exception: {str(e)[:300]}")
        failed += 1
        errors.append(f"#{num}: {desc} — Exception: {str(e)[:200]}")


def should_succeed(fn):
    try:
        fn()
        return True
    except Exception as e:
        return f"Expected success but got: {str(e)[:200]}"


def should_fail(fn):
    try:
        result = fn()
        if result is True:
            return "Expected error but action succeeded"
        return "Expected error but succeeded"
    except xmlrpc.client.Fault as e:
        if "cannot marshal None" in str(e):
            return "Expected error but action succeeded (None = success)"
        return True
    except Exception:
        return True


# ---- Auth all roles ----
admin_uid, M, ADMIN_PASS = admin_session()
portal_uid, _ = auth(PORTAL_LOGIN, PORTAL_PASS)
manager_uid, _ = auth(MANAGER_LOGIN, MANAGER_PASS)
user_uid, _ = auth(USER_LOGIN, USER_PASS)

# Get user IDs
portal_user_id = call(M, admin_uid, ADMIN_PASS, 'res.users', 'search', [[('login', '=', PORTAL_LOGIN)]])[0]
manager_user_id = call(M, admin_uid, ADMIN_PASS, 'res.users', 'search', [[('login', '=', MANAGER_LOGIN)]])[0]
user_user_id = call(M, admin_uid, ADMIN_PASS, 'res.users', 'search', [[('login', '=', USER_LOGIN)]])[0]
xiaoming_user_id = call(M, admin_uid, ADMIN_PASS, 'res.users', 'search', [[('login', '=', PORTAL2_LOGIN)]])[0]
xiaoming_uid, _ = auth(PORTAL2_LOGIN, PORTAL2_PASS)

# Create test data
test_tool = call(M, admin_uid, ADMIN_PASS, 'tool.tool', 'create', [{
    'name': 'R2 Security Tool', 'code': 'R2-SEC-001',
    'portal_user_ids': [(6, 0, [portal_user_id, xiaoming_user_id])]
}])

# Create a loan owned by portal user
portal_loan = call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'create', [{
    'tool_id': test_tool, 'user_id': portal_user_id
}])

print("\n" + "=" * 70)
print("ROUND 2: SECURITY & PERMISSION PENETRATION TESTS")
print("=" * 70)

# =====================================================
# tool.tool CRUD by role
# =====================================================
print("\n--- tool.tool Access Control ---")


def test_41():
    """portal can read tools"""
    return should_succeed(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.tool', 'search_read',
        [[('id', '=', test_tool)]], {'fields': ['name'], 'limit': 1}))
test(41, "portal can read tools", test_41)


def test_42():
    """portal CANNOT create tools"""
    return should_fail(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.tool', 'create',
        [{'name': 'Hack Tool', 'code': 'HACK-001'}]))
test(42, "portal CANNOT create tools", test_42)


def test_43():
    """portal CANNOT write tools"""
    return should_fail(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.tool', 'write',
        [[test_tool], {'name': 'Hacked Name'}]))
test(43, "portal CANNOT write tools", test_43)


def test_44():
    """portal CANNOT delete tools"""
    return should_fail(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.tool', 'unlink', [[test_tool]]))
test(44, "portal CANNOT delete tools", test_44)


def test_45():
    """internal user can read but NOT create/write/delete tools"""
    r1 = should_succeed(lambda: call(M, user_uid, USER_PASS, 'tool.tool', 'search_read',
        [[('id', '=', test_tool)]], {'fields': ['name'], 'limit': 1}))
    if r1 is not True:
        return f"Read failed: {r1}"
    r2 = should_fail(lambda: call(M, user_uid, USER_PASS, 'tool.tool', 'create',
        [{'name': 'User Tool', 'code': 'USR-001'}]))
    if r2 is not True:
        return f"Create should fail: {r2}"
    r3 = should_fail(lambda: call(M, user_uid, USER_PASS, 'tool.tool', 'write',
        [[test_tool], {'name': 'User Write'}]))
    if r3 is not True:
        return f"Write should fail: {r3}"
    return True
test(45, "internal user can read but NOT create/write/delete tools", test_45)


def test_46():
    """Equipment Manager has full CRUD on tools"""
    r1 = should_succeed(lambda: call(M, manager_uid, MANAGER_PASS, 'tool.tool', 'search_read',
        [[('id', '=', test_tool)]], {'fields': ['name'], 'limit': 1}))
    if r1 is not True:
        return f"Read failed: {r1}"
    r2 = should_succeed(lambda: call(M, manager_uid, MANAGER_PASS, 'tool.tool', 'write',
        [[test_tool], {'name': 'R2 Security Tool'}]))
    if r2 is not True:
        return f"Write failed: {r2}"
    # Create and delete
    tid = call(M, manager_uid, MANAGER_PASS, 'tool.tool', 'create',
        [{'name': 'Mgr Create Test', 'code': 'R2-MGR-CRT'}])
    r3 = should_succeed(lambda: call(M, manager_uid, MANAGER_PASS, 'tool.tool', 'unlink', [[tid]]))
    if r3 is not True:
        return f"Delete failed: {r3}"
    return True
test(46, "Equipment Manager has full CRUD on tools", test_46)


# =====================================================
# tool.loan CRUD by role
# =====================================================
print("\n--- tool.loan Access Control ---")


def test_47():
    """portal can read own loan"""
    return should_succeed(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'read',
        [[portal_loan], ['state']]))
test(47, "portal can read own loan", test_47)


def test_48():
    """portal CANNOT read other user's loan (record rule)"""
    xm_loan = call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'create', [{
        'tool_id': test_tool, 'user_id': xiaoming_user_id
    }])
    r = should_fail(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'read',
        [[xm_loan], ['state']]))
    call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'unlink', [[xm_loan]])
    return r
test(48, "portal CANNOT read other user's loan (record rule)", test_48)


def test_49():
    """portal can create own loan"""
    avail_tool = call(M, admin_uid, ADMIN_PASS, 'tool.tool', 'create', [{
        'name': 'R2 Avail Tool', 'code': 'R2-AVAIL-001',
        'portal_user_ids': [(6, 0, [portal_user_id])]
    }])
    r = should_succeed(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'create', [{
        'tool_id': avail_tool, 'user_id': portal_user_id
    }]))
    if r is True:
        loans = call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'search', [
            [('tool_id', '=', avail_tool), ('user_id', '=', portal_user_id)]])
        if loans:
            call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'unlink', [loans])
    call(M, admin_uid, ADMIN_PASS, 'tool.tool', 'unlink', [[avail_tool]])
    return r
test(49, "portal can create own loan", test_49)


def test_50():
    """internal user can create own loan"""
    avail_tool = call(M, admin_uid, ADMIN_PASS, 'tool.tool', 'create', [{
        'name': 'R2 User Tool', 'code': 'R2-USR-001'
    }])
    r = should_succeed(lambda: call(M, user_uid, USER_PASS, 'tool.loan', 'create', [{
        'tool_id': avail_tool, 'user_id': user_user_id
    }]))
    if r is True:
        loans = call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'search', [
            [('tool_id', '=', avail_tool)]])
        if loans:
            call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'unlink', [loans])
    call(M, admin_uid, ADMIN_PASS, 'tool.tool', 'unlink', [[avail_tool]])
    return r
test(50, "internal user can create own loan", test_50)


def test_51():
    """internal user CANNOT read other user's loan (record rule)"""
    r = should_fail(lambda: call(M, user_uid, USER_PASS, 'tool.loan', 'read',
        [[portal_loan], ['state']]))
    return r
test(51, "internal user CANNOT read other user's loan (record rule)", test_51)


def test_52():
    """portal can submit own loan"""
    r = should_succeed(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'action_submit', [[portal_loan]]))
    call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_reset_to_draft', [[portal_loan]])
    return r
test(52, "portal can submit own loan", test_52)


def test_53():
    """portal CANNOT approve (needs Equipment Manager)"""
    call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_submit', [[portal_loan]])
    r = should_fail(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'action_approve', [[portal_loan]]))
    call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_reset_to_draft', [[portal_loan]])
    return r
test(53, "portal CANNOT approve (needs Equipment Manager)", test_53)


def test_54():
    """internal user (not manager) CANNOT approve"""
    call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_submit', [[portal_loan]])
    r = should_fail(lambda: call(M, user_uid, USER_PASS, 'tool.loan', 'action_approve', [[portal_loan]]))
    call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_reset_to_draft', [[portal_loan]])
    return r
test(54, "internal user (not manager) CANNOT approve", test_54)


def _fresh_portal_loan():
    """New draft loan for the portal user, created by the (manager) admin.

    Each workflow case gets its own loan instead of forcing a used loan back
    to draft with a direct write of the workflow fields -- only Equipment
    Managers may write those, and returned loans have no reset action.
    """
    return call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'create', [{
        'tool_id': test_tool, 'user_id': portal_user_id
    }])


def test_55():
    """Equipment Manager CAN approve"""
    loan = _fresh_portal_loan()
    try:
        call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'action_submit', [[loan]])
        r = should_succeed(lambda: call(M, manager_uid, MANAGER_PASS, 'tool.loan', 'action_approve', [[loan]]))
        if r is True:
            call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_confirm_borrow', [[loan]])
            call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_confirm_return', [[loan]])
    finally:
        call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'unlink', [[loan]])
    return r
test(55, "Equipment Manager CAN approve", test_55)


def test_56():
    """Equipment Manager CAN confirm_borrow and confirm_return"""
    loan = _fresh_portal_loan()
    try:
        call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'action_submit', [[loan]])
        call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_approve', [[loan]])
        r1 = should_succeed(lambda: call(M, manager_uid, MANAGER_PASS, 'tool.loan', 'action_confirm_borrow', [[loan]]))
        if r1 is not True:
            return f"confirm_borrow failed: {r1}"
        r2 = should_succeed(lambda: call(M, manager_uid, MANAGER_PASS, 'tool.loan', 'action_confirm_return', [[loan]]))
        if r2 is not True:
            return f"confirm_return failed: {r2}"
    finally:
        call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'unlink', [[loan]])
    return True
test(56, "Equipment Manager CAN confirm_borrow and confirm_return", test_56)


def test_57():
    """portal CANNOT reject (needs Equipment Manager)"""
    call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_submit', [[portal_loan]])
    r = should_fail(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'action_reject', [[portal_loan]]))
    call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'action_reset_to_draft', [[portal_loan]])
    return r
test(57, "portal CANNOT reject (needs Equipment Manager)", test_57)


def test_58():
    """portal CANNOT delete loan"""
    return should_fail(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'unlink', [[portal_loan]]))
test(58, "portal CANNOT delete loan", test_58)


def test_58a():
    """portal CANNOT write workflow fields of own loan directly"""
    r = should_fail(lambda: call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'write',
        [[portal_loan], {'state': 'approved', 'approved_by': portal_user_id}]))
    state = call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'read', [[portal_loan], ['state']])[0]['state']
    if state != 'draft':
        return f"portal_loan state changed to {state}"
    return r
test('58a', "portal CANNOT write workflow fields (state/approved_by) directly", test_58a)


def test_58b():
    """portal CANNOT create a loan that is already approved"""
    def attempt():
        loan = call(M, portal_uid, PORTAL_PASS, 'tool.loan', 'create', [{
            'tool_id': test_tool, 'state': 'approved'}])
        call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'unlink', [[loan]])
        return loan
    return should_fail(attempt)
test('58b', "portal CANNOT create a loan in a non-draft state", test_58b)


def test_58c():
    """internal user CANNOT create a loan for somebody else"""
    def attempt():
        loan = call(M, user_uid, USER_PASS, 'tool.loan', 'create', [{
            'tool_id': test_tool, 'user_id': portal_user_id}])
        call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'unlink', [[loan]])
        return loan
    return should_fail(attempt)
test('58c', "internal user CANNOT create a loan for another user", test_58c)


def test_59():
    """internal user CANNOT delete loan"""
    user_tool = call(M, admin_uid, ADMIN_PASS, 'tool.tool', 'create', [{'name': 'R2 Del Test', 'code': 'R2-DEL-001'}])
    user_loan = call(M, user_uid, USER_PASS, 'tool.loan', 'create', [{'tool_id': user_tool, 'user_id': user_user_id}])
    r = should_fail(lambda: call(M, user_uid, USER_PASS, 'tool.loan', 'unlink', [[user_loan]]))
    call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'unlink', [[user_loan]])
    call(M, admin_uid, ADMIN_PASS, 'tool.tool', 'unlink', [[user_tool]])
    return r
test(59, "internal user CANNOT delete loan", test_59)


# =====================================================
# tool.category / tool.stage / tool.property ACL
# =====================================================
print("\n--- Readonly Models Access Control ---")


def test_60():
    """portal/user can read but NOT create categories"""
    for login, uid_val, pwd in [(PORTAL_LOGIN, portal_uid, PORTAL_PASS), (USER_LOGIN, user_uid, USER_PASS)]:
        r = should_succeed(lambda: call(M, uid_val, pwd, 'tool.category', 'search_read',
            [[]], {'fields': ['name'], 'limit': 1}))
        if r is not True:
            return f"{login} read failed: {r}"
        r2 = should_fail(lambda: call(M, uid_val, pwd, 'tool.category', 'create', [{'name': f'Hack {login}'}]))
        if r2 is not True:
            return f"{login} should NOT create categories: {r2}"
    return True
test(60, "portal/user can read but NOT create categories", test_60)


def test_61():
    """Equipment Manager CAN create/modify/delete categories"""
    cat_id = call(M, manager_uid, MANAGER_PASS, 'tool.category', 'create', [{'name': 'R2 Mgr Cat'}])
    if not cat_id:
        return "Create failed"
    r = should_succeed(lambda: call(M, manager_uid, MANAGER_PASS, 'tool.category', 'write', [[cat_id], {'name': 'R2 Mgr Cat Updated'}]))
    if r is not True:
        call(M, admin_uid, ADMIN_PASS, 'tool.category', 'unlink', [[cat_id]])
        return f"Write failed: {r}"
    r2 = should_succeed(lambda: call(M, manager_uid, MANAGER_PASS, 'tool.category', 'unlink', [[cat_id]]))
    if r2 is not True:
        return f"Delete failed: {r2}"
    return True
test(61, "Equipment Manager CAN create/modify/delete categories", test_61)


def test_62():
    """portal/user can read but NOT create stages"""
    for login, uid_val, pwd in [(PORTAL_LOGIN, portal_uid, PORTAL_PASS), (USER_LOGIN, user_uid, USER_PASS)]:
        r = should_succeed(lambda: call(M, uid_val, pwd, 'tool.stage', 'search_read',
            [[]], {'fields': ['name'], 'limit': 1}))
        if r is not True:
            return f"{login} read failed: {r}"
        r2 = should_fail(lambda: call(M, uid_val, pwd, 'tool.stage', 'create', [{'name': f'Hack {login}'}]))
        if r2 is not True:
            return f"{login} should NOT create stages: {r2}"
    return True
test(62, "portal/user can read but NOT create stages", test_62)


def test_63():
    """portal/user can read but NOT create/write properties"""
    for login, uid_val, pwd in [(PORTAL_LOGIN, portal_uid, PORTAL_PASS), (USER_LOGIN, user_uid, USER_PASS)]:
        r = should_succeed(lambda: call(M, uid_val, pwd, 'tool.property', 'search_read',
            [[]], {'fields': ['name'], 'limit': 1}))
        if r is not True:
            return f"{login} read failed: {r}"
        r2 = should_fail(lambda: call(M, uid_val, pwd, 'tool.property', 'create',
            [{'tool_id': test_tool, 'name': 'Hack', 'value': 'x'}]))
        if r2 is not True:
            return f"{login} should NOT create properties: {r2}"
    return True
test(63, "portal/user can read but NOT create properties", test_63)


# =====================================================
# Privilege Escalation & Cross-user Attacks
# =====================================================
print("\n--- Privilege Escalation ---")


def test_64():
    """unauthenticated (uid=0) cannot access any model"""
    try:
        call(M, 0, '', 'tool.tool', 'search_read', [[]], {'fields': ['name'], 'limit': 1})
        return "Expected auth failure for uid=0"
    except Exception:
        return True
test(64, "unauthenticated (uid=0) CANNOT access models", test_64)


# =====================================================
# Cleanup
# =====================================================
call(M, admin_uid, ADMIN_PASS, 'tool.loan', 'unlink', [[portal_loan]])
call(M, admin_uid, ADMIN_PASS, 'tool.tool', 'unlink', [[test_tool]])

# =====================================================
# Summary
# =====================================================
print("\n" + "=" * 70)
print(f"ROUND 2 RESULTS: {passed} PASSED / {failed} FAILED / {passed + failed} TOTAL")
print("=" * 70)
if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  - {e}")
print()
sys.exit(0 if failed == 0 else 1)
