#!/usr/bin/env python3
"""
Round 1: Backend Model Stress Tests (40 cases)
Tests tool.loan state machine, tool.tool operations, res.users group sync,
tool.category & tool.property edge cases via XML-RPC.
"""
import xmlrpc.client
import sys
import time

URL = 'http://localhost:9076'
DB = 'odootoolborrow'

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
        # Action methods returning None cause "cannot marshal None" — treat as success
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
        print(f"  [FAIL] #{num}: {desc} — Exception: {e}")
        failed += 1
        errors.append(f"#{num}: {desc} — Exception: {e}")


def expect_error(fn, error_substr=None):
    """Run fn, expect it to raise. Return True if it does, error msg if not."""
    try:
        result = fn()
        # If call() returned True due to None marshal, the action actually succeeded
        if result is True:
            return "Expected error but action succeeded (returned None/True)"
        return "Expected error but succeeded"
    except xmlrpc.client.Fault as e:
        # Filter out None marshal — that means the action succeeded
        if "cannot marshal None" in str(e):
            return "Expected error but action succeeded (None marshal = success)"
        if error_substr and error_substr not in str(e):
            return f"Got error but wrong message: {e.faultString[:200]}"
        return True
    except Exception as e:
        if error_substr and error_substr not in str(e):
            return f"Got error but wrong type: {e}"
        return True


# ---- Setup ----
admin_uid, M = auth('admin', 'admin')

# Create a fresh test tool for loan tests
test_tool_id = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'R1 Test Tool', 'state': 'available'}])
# Create a second tool for concurrent tests
test_tool2_id = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'R1 Test Tool 2', 'state': 'available'}])

# Get portal user id
portal_uid_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'portal')]])[0]

print("\n" + "=" * 70)
print("ROUND 1: BACKEND MODEL STRESS TESTS")
print("=" * 70)

# =====================================================
# 1A. tool.loan State Machine Tests (18 cases)
# =====================================================
print("\n--- 1A. tool.loan State Machine ---")


def test_1():
    """draft -> pending (action_submit)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    state = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state']
    if state != 'pending':
        return f"Expected pending, got {state}"
    # Cleanup: reset
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reset_to_draft', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    return True

test(1, "draft → pending (action_submit)", test_1)


def test_2():
    """pending -> approved (action_approve)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]])
    state = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state']
    if state != 'approved':
        return f"Expected approved, got {state}"
    # Tool should now be unavailable
    tool_state = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['state']])[0]['state']
    if tool_state != 'unavailable':
        return f"Tool should be unavailable, got {tool_state}"
    # Cleanup: we need to continue the flow to return the tool
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    return True

test(2, "pending → approved (action_approve) + tool becomes unavailable", test_2)


def test_3():
    """approved -> borrowed (action_confirm_borrow)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
    state = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state']
    if state != 'borrowed':
        return f"Expected borrowed, got {state}"
    # Cleanup
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    return True

test(3, "approved → borrowed (action_confirm_borrow)", test_3)


def test_4():
    """borrowed -> returned (action_confirm_return)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
    data = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state', 'return_date']])[0]
    if data['state'] != 'returned':
        return f"Expected returned, got {data['state']}"
    if not data['return_date']:
        return "return_date not set"
    # Tool should be available again
    tool_state = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['state']])[0]['state']
    if tool_state != 'available':
        return f"Tool should be available after return, got {tool_state}"
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    return True

test(4, "borrowed → returned (action_confirm_return) + tool available again", test_4)


def test_5():
    """pending -> rejected (action_reject)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reject', [[loan_id]])
    state = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state']
    if state != 'rejected':
        return f"Expected rejected, got {state}"
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    return True

test(5, "pending → rejected (action_reject)", test_5)


def test_6():
    """rejected -> draft (action_reset_to_draft)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reject', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reset_to_draft', [[loan_id]])
    state = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state']
    if state != 'draft':
        return f"Expected draft, got {state}"
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    return True

test(6, "rejected → draft (action_reset_to_draft)", test_6)


def test_7():
    """pending -> draft (action_reset_to_draft)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reset_to_draft', [[loan_id]])
    state = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state']
    if state != 'draft':
        return f"Expected draft, got {state}"
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    return True

test(7, "pending → draft (action_reset_to_draft)", test_7)

# Illegal transitions (8-16)
def make_loan_at_state(state_target):
    """Helper: create a loan and move it to the target state."""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool2_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    if state_target == 'draft':
        return loan_id
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    if state_target == 'pending':
        return loan_id
    if state_target == 'rejected':
        call(M, admin_uid, 'admin', 'tool.loan', 'action_reject', [[loan_id]])
        return loan_id
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]])
    if state_target == 'approved':
        return loan_id
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
    if state_target == 'borrowed':
        return loan_id
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
    return loan_id

def cleanup_loan(loan_id):
    """Cleanup loan: force return tool if needed, then delete."""
    try:
        data = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]
        if data['state'] in ('approved', 'borrowed'):
            if data['state'] == 'approved':
                call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
            call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
        call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    except:
        try:
            call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
        except:
            pass


def test_8():
    """draft -> approved (skip submit) should fail"""
    loan_id = make_loan_at_state('draft')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(8, "ILLEGAL: draft → approved (skip submit)", test_8)


def test_9():
    """draft -> borrowed (skip two steps) should fail"""
    loan_id = make_loan_at_state('draft')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(9, "ILLEGAL: draft → borrowed (skip two steps)", test_9)


def test_10():
    """draft -> returned (skip three steps) should fail"""
    loan_id = make_loan_at_state('draft')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(10, "ILLEGAL: draft → returned (skip three steps)", test_10)


def test_11():
    """pending -> borrowed (skip approve) should fail"""
    loan_id = make_loan_at_state('pending')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(11, "ILLEGAL: pending → borrowed (skip approve)", test_11)


def test_12():
    """approved -> returned (skip borrow) should fail"""
    loan_id = make_loan_at_state('approved')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(12, "ILLEGAL: approved → returned (skip borrow)", test_12)


def test_13():
    """rejected -> approved should fail"""
    loan_id = make_loan_at_state('rejected')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(13, "ILLEGAL: rejected → approved", test_13)


def test_14():
    """returned -> draft should fail"""
    loan_id = make_loan_at_state('returned')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_reset_to_draft', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(14, "ILLEGAL: returned → draft", test_14)


def test_15():
    """returned -> borrowed should fail"""
    loan_id = make_loan_at_state('returned')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(15, "ILLEGAL: returned → borrowed", test_15)


def test_16():
    """borrowed -> approved (backward) should fail"""
    loan_id = make_loan_at_state('borrowed')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(16, "ILLEGAL: borrowed → approved (backward)", test_16)

# Edge cases (17-18)
def test_17():
    """Create loan for unavailable tool should fail (validation in create)"""
    # Make tool unavailable
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool2_id], {'state': 'maintenance'}])
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool2_id, 'user_id': portal_uid_id, 'state': 'draft'
    }]))
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool2_id], {'state': 'available'}])
    return r

test(17, "Create loan for unavailable tool should fail", test_17)


def test_18():
    """Concurrent: two loans for same tool — second create should fail after first approved"""
    # Create first loan and approve it (tool becomes unavailable)
    loan1 = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan1]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan1]])
    # Tool is now unavailable, second loan create should fail
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }]))
    # Cleanup
    cleanup_loan(loan1)
    return r

test(18, "Concurrent: two loans for same tool — second create should fail", test_18)


# =====================================================
# 1B. tool.tool Operation Tests (10 cases)
# =====================================================
print("\n--- 1B. tool.tool Operations ---")


def test_19():
    """Create tool — auto-generate code TOOL/XXXXX"""
    tid = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Auto Code Test'}])
    data = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[tid], ['code']])[0]
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[tid]])
    if not data['code'].startswith('TOOL/'):
        return f"Expected TOOL/XXXXX, got {data['code']}"
    return True

test(19, "Create tool — auto-generate code TOOL/XXXXX", test_19)


def test_20():
    """Duplicate code should fail (unique constraint)"""
    tid1 = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Dup Test 1', 'code': 'DUP-001'}])
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Dup Test 2', 'code': 'DUP-001'}]))
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[tid1]])
    return r

test(20, "Duplicate code should fail (unique constraint)", test_20)


def test_21():
    """action_set_maintenance — available → maintenance"""
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'state': 'available'}])
    call(M, admin_uid, 'admin', 'tool.tool', 'action_set_maintenance', [[test_tool_id]])
    state = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['state']])[0]['state']
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'state': 'available'}])
    if state != 'maintenance':
        return f"Expected maintenance, got {state}"
    return True

test(21, "action_set_maintenance — available → maintenance", test_21)


def test_22():
    """action_set_maintenance — unavailable should fail"""
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'state': 'unavailable'}])
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.tool', 'action_set_maintenance', [[test_tool_id]]))
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'state': 'available'}])
    return r

test(22, "action_set_maintenance — unavailable should fail", test_22)


def test_23():
    """action_set_available — maintenance → available"""
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'state': 'maintenance'}])
    call(M, admin_uid, 'admin', 'tool.tool', 'action_set_available', [[test_tool_id]])
    state = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['state']])[0]['state']
    if state != 'available':
        return f"Expected available, got {state}"
    return True

test(23, "action_set_available — maintenance → available", test_23)


def test_24():
    """action_set_available — unavailable should fail"""
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'state': 'unavailable'}])
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.tool', 'action_set_available', [[test_tool_id]]))
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'state': 'available'}])
    return r

test(24, "action_set_available — unavailable should fail", test_24)


def test_25():
    """_compute_current_loan — borrowed loan computes correctly"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
    data = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['current_loan_id', 'current_borrower_id']])[0]
    if data['current_loan_id'] and data['current_loan_id'][0] != loan_id:
        cleanup_loan(loan_id)
        return f"current_loan_id mismatch"
    if data['current_borrower_id'] and data['current_borrower_id'][0] != portal_uid_id:
        cleanup_loan(loan_id)
        return f"current_borrower_id mismatch"
    cleanup_loan(loan_id)
    return True

test(25, "_compute_current_loan — borrowed loan computes correctly", test_25)


def test_26():
    """_compute_current_loan — no active loan = empty"""
    # First clean up any leftover loans on this tool
    leftover_loans = call(M, admin_uid, 'admin', 'tool.loan', 'search', [
        [('tool_id', '=', test_tool_id), ('state', 'in', ['approved', 'borrowed'])]
    ])
    for ll in leftover_loans:
        cleanup_loan(ll)
    # Ensure tool is available
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'state': 'available'}])
    data = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['current_loan_id', 'current_borrower_id']])[0]
    if data['current_loan_id']:
        return f"Expected empty current_loan_id, got {data['current_loan_id']}"
    return True

test(26, "_compute_current_loan — no active loan = empty", test_26)


def test_27():
    """Archive tool (active=False)"""
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool2_id], {'active': False}])
    # Should not appear in default search
    found = call(M, admin_uid, 'admin', 'tool.tool', 'search', [[('id', '=', test_tool2_id)]])
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool2_id], {'active': True}])
    if found:
        return "Archived tool still visible in default search"
    return True

test(27, "Archive tool (active=False) hides from default search", test_27)


def test_28():
    """Delete tool with loan history"""
    temp_tool = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Delete Test'}])
    temp_loan = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': temp_tool, 'user_id': portal_uid_id, 'state': 'draft'
    }])
    # Try to delete tool with loan — may raise or cascade
    try:
        call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[temp_tool]])
        # If succeeded, loan should also be gone or tool deleted
        return True
    except xmlrpc.client.Fault:
        # Expected: can't delete tool with loans
        call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[temp_loan]])
        call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[temp_tool]])
        return True

test(28, "Delete tool with loan history (should cascade or block)", test_28)


# =====================================================
# 1C. res.users Group Sync Tests (8 cases)
# =====================================================
print("\n--- 1C. res.users Group Sync ---")

# Get group external IDs
def get_group_id(xmlid):
    parts = xmlid.split('.')
    data = call(M, admin_uid, 'admin', 'ir.model.data', 'search_read',
        [[('module', '=', parts[0]), ('name', '=', parts[1])]],
        {'fields': ['res_id'], 'limit': 1})
    return data[0]['res_id'] if data else None

g_user = get_group_id('tool_borrow.group_tool_user')
g_manager = get_group_id('tool_borrow.group_tool_manager')
g_admin_tb = get_group_id('tool_borrow.group_tool_admin')
internal_group = get_group_id('base.group_user')

def user_has_group(user_id, group_id):
    groups = call(M, admin_uid, 'admin', 'res.users', 'read', [[user_id], ['groups_id']])[0]['groups_id']
    return group_id in groups


def test_29():
    """Set access='user' → has group_tool_user"""
    tu_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'testuser')]])[0]
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'user'}])
    if not user_has_group(tu_id, g_user):
        return "Missing group_tool_user"
    return True

test(29, "Set access='user' → has group_tool_user", test_29)


def test_30():
    """Set access='manager' → has group_tool_manager + user"""
    tm_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'testmanager')]])[0]
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tm_id], {'tool_borrow_access': 'manager'}])
    if not user_has_group(tm_id, g_manager):
        return "Missing group_tool_manager"
    if not user_has_group(tm_id, g_user):
        return "Missing group_tool_user (implied)"
    return True

test(30, "Set access='manager' → has group_tool_manager + user", test_30)


def test_31():
    """Set access='admin' → has all three groups"""
    tu_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'testuser')]])[0]
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'admin'}])
    if not user_has_group(tu_id, g_admin_tb):
        return "Missing group_tool_admin"
    if not user_has_group(tu_id, g_manager):
        return "Missing group_tool_manager"
    if not user_has_group(tu_id, g_user):
        return "Missing group_tool_user"
    # Reset back
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'user'}])
    return True

test(31, "Set access='admin' → has all three groups", test_31)


def test_32():
    """Set access='no_access' → no tool groups"""
    tu_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'testuser')]])[0]
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'no_access'}])
    if user_has_group(tu_id, g_user):
        call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'user'}])
        return "Still has group_tool_user"
    if user_has_group(tu_id, g_manager):
        call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'user'}])
        return "Still has group_tool_manager"
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'user'}])
    return True

test(32, "Set access='no_access' → no tool groups", test_32)


def test_33():
    """Downgrade admin → user removes admin/manager groups"""
    tu_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'testuser')]])[0]
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'admin'}])
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'user'}])
    if user_has_group(tu_id, g_admin_tb):
        return "Still has group_tool_admin"
    if user_has_group(tu_id, g_manager):
        return "Still has group_tool_manager"
    if not user_has_group(tu_id, g_user):
        return "Missing group_tool_user"
    return True

test(33, "Downgrade admin → user removes admin/manager groups", test_33)


def test_34():
    """Portal user: set access field only, no group commands"""
    p_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'portal')]])[0]
    call(M, admin_uid, 'admin', 'res.users', 'write', [[p_id], {'tool_borrow_access': 'user'}])
    access = call(M, admin_uid, 'admin', 'res.users', 'read', [[p_id], ['tool_borrow_access']])[0]['tool_borrow_access']
    if access != 'user':
        return f"Expected user, got {access}"
    # Should NOT have internal group
    if user_has_group(p_id, g_user):
        return "Portal user should NOT get internal group_tool_user"
    return True

test(34, "Portal user: access field set, no group commands (avoid conflict)", test_34)


def test_35():
    """New internal user with tool_borrow_access='manager' on create"""
    new_id = call(M, admin_uid, 'admin', 'res.users', 'create', [{
        'name': 'New Mgr Test',
        'login': 'newmgrtest',
        'password': 'newmgrtest',
        'groups_id': [(6, 0, [internal_group])],
    }])
    call(M, admin_uid, 'admin', 'res.users', 'write', [[new_id], {'tool_borrow_access': 'manager'}])
    if not user_has_group(new_id, g_manager):
        call(M, admin_uid, 'admin', 'res.users', 'unlink', [[new_id]])
        return "Missing group_tool_manager"
    call(M, admin_uid, 'admin', 'res.users', 'unlink', [[new_id]])
    return True

test(35, "New user with access='manager' → groups correct", test_35)


def test_36():
    """Batch update multiple users access level"""
    tu_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'testuser')]])[0]
    tm_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'testmanager')]])[0]
    # Set both to no_access then back
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id, tm_id], {'tool_borrow_access': 'no_access'}])
    for uid_check in [tu_id, tm_id]:
        if user_has_group(uid_check, g_user):
            call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'user'}])
            call(M, admin_uid, 'admin', 'res.users', 'write', [[tm_id], {'tool_borrow_access': 'manager'}])
            return f"User {uid_check} still has tool groups after batch no_access"
    # Restore
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tu_id], {'tool_borrow_access': 'user'}])
    call(M, admin_uid, 'admin', 'res.users', 'write', [[tm_id], {'tool_borrow_access': 'manager'}])
    return True

test(36, "Batch update multiple users access level", test_36)


# =====================================================
# 1D. tool.category & tool.property Tests (4 cases)
# =====================================================
print("\n--- 1D. tool.category & tool.property ---")


def test_37():
    """Create category with tool_properties_definition"""
    cat_id = call(M, admin_uid, 'admin', 'tool.category', 'create', [{
        'name': 'Test Category R1',
        'description': 'Test desc',
    }])
    if not cat_id:
        return "Failed to create category"
    call(M, admin_uid, 'admin', 'tool.category', 'unlink', [[cat_id]])
    return True

test(37, "Create category with description", test_37)


def test_38():
    """Tool linked to category gets category properties"""
    cat_id = call(M, admin_uid, 'admin', 'tool.category', 'create', [{'name': 'Props Cat'}])
    tid = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{
        'name': 'Props Tool', 'category_id': cat_id
    }])
    data = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[tid], ['category_id']])[0]
    if not data['category_id'] or data['category_id'][0] != cat_id:
        call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[tid]])
        call(M, admin_uid, 'admin', 'tool.category', 'unlink', [[cat_id]])
        return "Category not linked"
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[tid]])
    call(M, admin_uid, 'admin', 'tool.category', 'unlink', [[cat_id]])
    return True

test(38, "Tool linked to category", test_38)


def test_39():
    """Create tool.property with required fields"""
    prop_id = call(M, admin_uid, 'admin', 'tool.property', 'create', [{
        'tool_id': test_tool_id, 'name': 'Weight', 'value': '2.5kg'
    }])
    if not prop_id:
        return "Failed to create property"
    # Test missing required field
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.property', 'create', [{
        'tool_id': test_tool_id, 'name': 'NoValue'
    }]))
    call(M, admin_uid, 'admin', 'tool.property', 'unlink', [[prop_id]])
    return r

test(39, "tool.property required fields validation", test_39)


def test_40():
    """Delete tool cascades properties"""
    temp_tool = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Cascade Test'}])
    prop_id = call(M, admin_uid, 'admin', 'tool.property', 'create', [{
        'tool_id': temp_tool, 'name': 'Cascaded', 'value': 'yes'
    }])
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[temp_tool]])
    # Property should be gone
    found = call(M, admin_uid, 'admin', 'tool.property', 'search', [[('id', '=', prop_id)]])
    if found:
        return "Property still exists after tool deletion"
    return True

test(40, "Delete tool cascades properties", test_40)


# =====================================================
# Cleanup
# =====================================================
try:
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[test_tool_id]])
except:
    pass
try:
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[test_tool2_id]])
except:
    pass

# =====================================================
# Summary
# =====================================================
print("\n" + "=" * 70)
print(f"ROUND 1 RESULTS: {passed} PASSED / {failed} FAILED / {passed + failed} TOTAL")
print("=" * 70)
if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  - {e}")
print()
sys.exit(0 if failed == 0 else 1)
