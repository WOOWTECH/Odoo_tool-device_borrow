#!/usr/bin/env python3
"""
Round 1: Backend Model Tests (40 cases)
Tests tool.stage, tool.category, tool.property, tool.tool operations,
tool.loan state machine, and computed fields via XML-RPC.

Matches current module: stage-based state (computed), portal_user_ids,
2-tier permission (Internal User + Equipment Manager).
"""
import xmlrpc.client
import sys

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


def expect_error(fn, error_substr=None):
    """Run fn, expect it to raise. Return True if it does."""
    try:
        result = fn()
        if result is True:
            return "Expected error but action succeeded (returned None/True)"
        return "Expected error but succeeded"
    except xmlrpc.client.Fault as e:
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

# Find stage IDs
stages = call(M, admin_uid, 'admin', 'tool.stage', 'search_read', [[]], {'fields': ['name', 'is_closed'], 'order': 'sequence'})
stage_available = None
stage_maintenance = None
stage_retired = None
for s in stages:
    if not s['is_closed'] and not stage_available:
        stage_available = s['id']
    elif not s['is_closed'] and not stage_maintenance:
        stage_maintenance = s['id']
    elif s['is_closed'] and not stage_retired:
        stage_retired = s['id']

# Get user IDs
portal_uid_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'portal')]])[0]
testuser_uid_id = call(M, admin_uid, 'admin', 'res.users', 'search', [[('login', '=', 'testuser')]])[0]

# Create fresh test tools
test_tool_id = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'R1 Test Tool', 'code': 'R1-TEST-001'}])
test_tool2_id = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'R1 Test Tool 2', 'code': 'R1-TEST-002'}])

print("\n" + "=" * 70)
print("ROUND 1: BACKEND MODEL TESTS")
print("=" * 70)

# =====================================================
# 1A. tool.stage Tests (4 cases)
# =====================================================
print("\n--- 1A. tool.stage ---")


def test_1():
    """Create stage with all fields"""
    sid = call(M, admin_uid, 'admin', 'tool.stage', 'create', [{
        'name': 'R1 Test Stage', 'sequence': 99, 'is_closed': False, 'fold': True
    }])
    data = call(M, admin_uid, 'admin', 'tool.stage', 'read', [[sid], ['name', 'sequence', 'is_closed', 'fold']])[0]
    call(M, admin_uid, 'admin', 'tool.stage', 'unlink', [[sid]])
    if data['name'] != 'R1 Test Stage':
        return f"name mismatch: {data['name']}"
    if data['fold'] is not True:
        return "fold should be True"
    return True

test(1, "Create stage with all fields", test_1)


def test_2():
    """Duplicate stage name should fail (unique constraint)"""
    sid = call(M, admin_uid, 'admin', 'tool.stage', 'create', [{'name': 'R1 Dup Stage'}])
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.stage', 'create', [{'name': 'R1 Dup Stage'}]))
    call(M, admin_uid, 'admin', 'tool.stage', 'unlink', [[sid]])
    return r

test(2, "Duplicate stage name should fail (unique constraint)", test_2)


def test_3():
    """Stage is_closed=True marks tools as maintenance"""
    closed_stage = call(M, admin_uid, 'admin', 'tool.stage', 'create', [{'name': 'R1 Closed Stage', 'is_closed': True}])
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool2_id], {'stage_id': closed_stage}])
    state = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool2_id], ['state']])[0]['state']
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool2_id], {'stage_id': stage_available}])
    call(M, admin_uid, 'admin', 'tool.stage', 'unlink', [[closed_stage]])
    if state != 'maintenance':
        return f"Expected maintenance, got {state}"
    return True

test(3, "Stage is_closed=True computes tool state as 'maintenance'", test_3)


def test_4():
    """Stage is_closed=False keeps tool available"""
    if not stage_available:
        return "No available stage found"
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool2_id], {'stage_id': stage_available}])
    state = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool2_id], ['state']])[0]['state']
    if state != 'available':
        return f"Expected available, got {state}"
    return True

test(4, "Stage is_closed=False keeps tool state 'available'", test_4)


# =====================================================
# 1B. tool.loan State Machine Tests (14 cases)
# =====================================================
print("\n--- 1B. tool.loan State Machine ---")


def test_5():
    """draft -> pending (action_submit)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{'tool_id': test_tool_id, 'user_id': portal_uid_id}])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    data = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state', 'request_date']])[0]
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reset_to_draft', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    if data['state'] != 'pending':
        return f"Expected pending, got {data['state']}"
    if not data['request_date']:
        return "request_date not set"
    return True

test(5, "draft → pending (action_submit) + request_date set", test_5)


def test_6():
    """pending -> approved (action_approve)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{'tool_id': test_tool_id, 'user_id': portal_uid_id}])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]])
    data = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state', 'approved_date', 'approved_by']])[0]
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    if data['state'] != 'approved':
        return f"Expected approved, got {data['state']}"
    if not data['approved_date']:
        return "approved_date not set"
    if not data['approved_by']:
        return "approved_by not set"
    return True

test(6, "pending → approved + approved_date + approved_by set", test_6)


def test_7():
    """approved -> borrowed (action_confirm_borrow) + tool becomes 'borrowed'"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{'tool_id': test_tool_id, 'user_id': portal_uid_id}])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
    loan_data = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state', 'borrow_date']])[0]
    tool_state = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['state']])[0]['state']
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    if loan_data['state'] != 'borrowed':
        return f"Expected borrowed, got {loan_data['state']}"
    if not loan_data['borrow_date']:
        return "borrow_date not set"
    if tool_state != 'borrowed':
        return f"Tool should be 'borrowed', got {tool_state}"
    return True

test(7, "approved → borrowed + borrow_date set + tool state='borrowed'", test_7)


def test_8():
    """borrowed -> returned (action_confirm_return) + tool available again"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{'tool_id': test_tool_id, 'user_id': portal_uid_id}])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
    loan_data = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state', 'return_date']])[0]
    tool_state = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['state']])[0]['state']
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    if loan_data['state'] != 'returned':
        return f"Expected returned, got {loan_data['state']}"
    if not loan_data['return_date']:
        return "return_date not set"
    if tool_state != 'available':
        return f"Tool should be available after return, got {tool_state}"
    return True

test(8, "borrowed → returned + return_date set + tool available again", test_8)


def test_9():
    """pending -> rejected (action_reject)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{'tool_id': test_tool_id, 'user_id': portal_uid_id}])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reject', [[loan_id]])
    state = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state']
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    if state != 'rejected':
        return f"Expected rejected, got {state}"
    return True

test(9, "pending → rejected (action_reject)", test_9)


def test_10():
    """rejected -> draft (action_reset_to_draft)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{'tool_id': test_tool_id, 'user_id': portal_uid_id}])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reject', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reset_to_draft', [[loan_id]])
    data = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state', 'request_date', 'approved_by']])[0]
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    if data['state'] != 'draft':
        return f"Expected draft, got {data['state']}"
    if data['request_date']:
        return "request_date should be cleared"
    return True

test(10, "rejected → draft (reset clears dates)", test_10)


def test_11():
    """pending -> draft (action_reset_to_draft)"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{'tool_id': test_tool_id, 'user_id': portal_uid_id}])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_reset_to_draft', [[loan_id]])
    state = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state']
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    if state != 'draft':
        return f"Expected draft, got {state}"
    return True

test(11, "pending → draft (action_reset_to_draft)", test_11)


# Illegal transitions (12-18)
def make_loan_at_state(state_target, tool_id=None):
    """Helper: create a loan and move it to the target state."""
    tid = tool_id or test_tool2_id
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{'tool_id': tid, 'user_id': portal_uid_id}])
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
    """Cleanup loan: force return if needed, then delete."""
    try:
        data = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]
        if data['state'] == 'approved':
            call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
            call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
        elif data['state'] == 'borrowed':
            call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
        call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    except Exception:
        try:
            call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
        except Exception:
            pass


def test_12():
    """ILLEGAL: draft → approved (skip submit)"""
    loan_id = make_loan_at_state('draft')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(12, "ILLEGAL: draft → approved (skip submit)", test_12)


def test_13():
    """ILLEGAL: draft → borrowed (skip two steps)"""
    loan_id = make_loan_at_state('draft')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(13, "ILLEGAL: draft → borrowed (skip two steps)", test_13)


def test_14():
    """ILLEGAL: draft → returned (skip three steps)"""
    loan_id = make_loan_at_state('draft')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(14, "ILLEGAL: draft → returned (skip three steps)", test_14)


def test_15():
    """ILLEGAL: pending → borrowed (skip approve)"""
    loan_id = make_loan_at_state('pending')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(15, "ILLEGAL: pending → borrowed (skip approve)", test_15)


def test_16():
    """ILLEGAL: approved → returned (skip borrow)"""
    loan_id = make_loan_at_state('approved')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(16, "ILLEGAL: approved → returned (skip borrow)", test_16)


def test_17():
    """ILLEGAL: returned → draft"""
    loan_id = make_loan_at_state('returned')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_reset_to_draft', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(17, "ILLEGAL: returned → draft", test_17)


def test_18():
    """ILLEGAL: borrowed → approved (backward)"""
    loan_id = make_loan_at_state('borrowed')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(18, "ILLEGAL: borrowed → approved (backward)", test_18)


# =====================================================
# 1C. tool.tool Operation Tests (12 cases)
# =====================================================
print("\n--- 1C. tool.tool Operations ---")


def test_19():
    """Duplicate code should fail (unique constraint)"""
    tid1 = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Dup Test 1', 'code': 'R1-DUP-001'}])
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Dup Test 2', 'code': 'R1-DUP-001'}]))
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[tid1]])
    return r

test(19, "Duplicate code should fail (unique constraint)", test_19)


def test_20():
    """action_set_maintenance — available → maintenance"""
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'stage_id': stage_available}])
    call(M, admin_uid, 'admin', 'tool.tool', 'action_set_maintenance', [[test_tool_id]])
    state = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['state']])[0]['state']
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'stage_id': stage_available}])
    if state != 'maintenance':
        return f"Expected maintenance, got {state}"
    return True

test(20, "action_set_maintenance — available → maintenance", test_20)


def test_21():
    """action_set_maintenance — borrowed should fail"""
    loan_id = make_loan_at_state('borrowed', test_tool_id)
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.tool', 'action_set_maintenance', [[test_tool_id]]))
    cleanup_loan(loan_id)
    return r

test(21, "action_set_maintenance — borrowed tool should fail", test_21)


def test_22():
    """action_set_available — maintenance → available"""
    call(M, admin_uid, 'admin', 'tool.tool', 'action_set_maintenance', [[test_tool_id]])
    state1 = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['state']])[0]['state']
    call(M, admin_uid, 'admin', 'tool.tool', 'action_set_available', [[test_tool_id]])
    state2 = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['state']])[0]['state']
    if state1 != 'maintenance':
        return f"Before: expected maintenance, got {state1}"
    if state2 != 'available':
        return f"After: expected available, got {state2}"
    return True

test(22, "action_set_available — maintenance → available", test_22)


def test_23():
    """action_set_available — borrowed should fail"""
    loan_id = make_loan_at_state('borrowed', test_tool_id)
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.tool', 'action_set_available', [[test_tool_id]]))
    cleanup_loan(loan_id)
    return r

test(23, "action_set_available — borrowed tool should fail", test_23)


def test_24():
    """_compute_current_loan — borrowed loan computes correctly"""
    loan_id = make_loan_at_state('borrowed', test_tool_id)
    data = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['current_loan_id', 'current_borrower_id', 'state']])[0]
    cleanup_loan(loan_id)
    if not data['current_loan_id'] or data['current_loan_id'][0] != loan_id:
        return f"current_loan_id mismatch: {data['current_loan_id']}"
    if not data['current_borrower_id'] or data['current_borrower_id'][0] != portal_uid_id:
        return f"current_borrower_id mismatch: {data['current_borrower_id']}"
    if data['state'] != 'borrowed':
        return f"state should be 'borrowed', got {data['state']}"
    return True

test(24, "_compute_current_loan — borrowed loan computes correctly", test_24)


def test_25():
    """_compute_current_loan — no active loan = empty"""
    data = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['current_loan_id', 'current_borrower_id']])[0]
    if data['current_loan_id']:
        return f"Expected empty current_loan_id, got {data['current_loan_id']}"
    if data['current_borrower_id']:
        return f"Expected empty current_borrower_id, got {data['current_borrower_id']}"
    return True

test(25, "_compute_current_loan — no active loan = empty", test_25)


def test_26():
    """Archive tool (active=False) hides from default search"""
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool2_id], {'active': False}])
    found = call(M, admin_uid, 'admin', 'tool.tool', 'search', [[('id', '=', test_tool2_id)]])
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool2_id], {'active': True}])
    if found:
        return "Archived tool still visible in default search"
    return True

test(26, "Archive tool (active=False) hides from default search", test_26)


def test_27():
    """Create loan for tool in maintenance should fail"""
    call(M, admin_uid, 'admin', 'tool.tool', 'action_set_maintenance', [[test_tool2_id]])
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool2_id, 'user_id': portal_uid_id
    }]))
    call(M, admin_uid, 'admin', 'tool.tool', 'action_set_available', [[test_tool2_id]])
    return r

test(27, "Create loan for tool in maintenance should fail", test_27)


def test_28():
    """Concurrent: two loans for same tool — second should fail after first borrowed"""
    loan1 = make_loan_at_state('borrowed', test_tool_id)
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': testuser_uid_id
    }]))
    cleanup_loan(loan1)
    return r

test(28, "Concurrent: two loans for same tool — second create should fail", test_28)


def test_29():
    """Delete tool cascades properties"""
    temp_tool = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Cascade Test', 'code': 'R1-CASCADE'}])
    prop_id = call(M, admin_uid, 'admin', 'tool.property', 'create', [{'tool_id': temp_tool, 'name': 'Weight', 'value': '2.5kg'}])
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[temp_tool]])
    found = call(M, admin_uid, 'admin', 'tool.property', 'search', [[('id', '=', prop_id)]])
    if found:
        return "Property still exists after tool deletion"
    return True

test(29, "Delete tool cascades properties", test_29)


def test_30():
    """portal_user_ids many2many field works"""
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {
        'portal_user_ids': [(6, 0, [portal_uid_id])]
    }])
    data = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[test_tool_id], ['portal_user_ids']])[0]
    call(M, admin_uid, 'admin', 'tool.tool', 'write', [[test_tool_id], {'portal_user_ids': [(5,)]}])
    if portal_uid_id not in data['portal_user_ids']:
        return f"portal_uid not in portal_user_ids: {data['portal_user_ids']}"
    return True

test(30, "portal_user_ids many2many field works", test_30)


# =====================================================
# 1D. tool.category & tool.property Tests (6 cases)
# =====================================================
print("\n--- 1D. tool.category & tool.property ---")


def test_31():
    """Create category with description"""
    cat_id = call(M, admin_uid, 'admin', 'tool.category', 'create', [{'name': 'R1 Test Category', 'description': 'Test desc'}])
    data = call(M, admin_uid, 'admin', 'tool.category', 'read', [[cat_id], ['name', 'description']])[0]
    call(M, admin_uid, 'admin', 'tool.category', 'unlink', [[cat_id]])
    if data['name'] != 'R1 Test Category':
        return f"name mismatch: {data['name']}"
    return True

test(31, "Create category with description", test_31)


def test_32():
    """tool_count computed field"""
    cat_id = call(M, admin_uid, 'admin', 'tool.category', 'create', [{'name': 'R1 Count Cat'}])
    t1 = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Count 1', 'code': 'R1-CNT-1', 'category_id': cat_id}])
    t2 = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Count 2', 'code': 'R1-CNT-2', 'category_id': cat_id}])
    count = call(M, admin_uid, 'admin', 'tool.category', 'read', [[cat_id], ['tool_count']])[0]['tool_count']
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[t1, t2]])
    call(M, admin_uid, 'admin', 'tool.category', 'unlink', [[cat_id]])
    if count != 2:
        return f"Expected 2, got {count}"
    return True

test(32, "tool_count computed field", test_32)


def test_33():
    """Tool linked to category"""
    cat_id = call(M, admin_uid, 'admin', 'tool.category', 'create', [{'name': 'R1 Link Cat'}])
    tid = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Link Tool', 'code': 'R1-LINK', 'category_id': cat_id}])
    data = call(M, admin_uid, 'admin', 'tool.tool', 'read', [[tid], ['category_id']])[0]
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[tid]])
    call(M, admin_uid, 'admin', 'tool.category', 'unlink', [[cat_id]])
    if not data['category_id'] or data['category_id'][0] != cat_id:
        return "Category not linked"
    return True

test(33, "Tool linked to category", test_33)


def test_34():
    """tool.property required fields validation"""
    prop_id = call(M, admin_uid, 'admin', 'tool.property', 'create', [{'tool_id': test_tool_id, 'name': 'Weight', 'value': '2.5kg'}])
    if not prop_id:
        return "Failed to create property"
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.property', 'create', [{'tool_id': test_tool_id, 'name': 'NoValue'}]))
    call(M, admin_uid, 'admin', 'tool.property', 'unlink', [[prop_id]])
    return r

test(34, "tool.property required fields validation", test_34)


def test_35():
    """tool.property sequence ordering"""
    p1 = call(M, admin_uid, 'admin', 'tool.property', 'create', [{'tool_id': test_tool_id, 'name': 'A', 'value': '1', 'sequence': 20}])
    p2 = call(M, admin_uid, 'admin', 'tool.property', 'create', [{'tool_id': test_tool_id, 'name': 'B', 'value': '2', 'sequence': 5}])
    props = call(M, admin_uid, 'admin', 'tool.property', 'search_read', [[('tool_id', '=', test_tool_id)]], {'fields': ['name', 'sequence'], 'order': 'sequence, id'})
    call(M, admin_uid, 'admin', 'tool.property', 'unlink', [[p1, p2]])
    if len(props) < 2:
        return f"Expected at least 2 properties, got {len(props)}"
    if props[0]['name'] != 'B':
        return f"Expected 'B' first (seq=5), got '{props[0]['name']}'"
    return True

test(35, "tool.property sequence ordering", test_35)


def test_36():
    """Full loan lifecycle: draft → pending → approved → borrowed → returned"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{'tool_id': test_tool_id, 'user_id': portal_uid_id}])
    states = []
    states.append(call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state'])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]])
    states.append(call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state'])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_approve', [[loan_id]])
    states.append(call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state'])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_borrow', [[loan_id]])
    states.append(call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state'])
    call(M, admin_uid, 'admin', 'tool.loan', 'action_confirm_return', [[loan_id]])
    states.append(call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['state']])[0]['state'])
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    expected = ['draft', 'pending', 'approved', 'borrowed', 'returned']
    if states != expected:
        return f"Expected {expected}, got {states}"
    return True

test(36, "Full lifecycle: draft→pending→approved→borrowed→returned", test_36)


# =====================================================
# 1E. Edge Cases (4 cases)
# =====================================================
print("\n--- 1E. Edge Cases ---")


def test_37():
    """Submit already pending loan should fail"""
    loan_id = make_loan_at_state('pending')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_submit', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(37, "Submit already pending loan should fail", test_37)


def test_38():
    """Reject already rejected loan should fail"""
    loan_id = make_loan_at_state('rejected')
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.loan', 'action_reject', [[loan_id]]))
    cleanup_loan(loan_id)
    return r

test(38, "Reject already rejected loan should fail", test_38)


def test_39():
    """Tool copy with copy=False on required code field fails without code"""
    tid = call(M, admin_uid, 'admin', 'tool.tool', 'create', [{'name': 'Copy Test', 'code': 'R1-COPY-001'}])
    # copy=False on required field means copy fails without providing code
    r = expect_error(lambda: call(M, admin_uid, 'admin', 'tool.tool', 'copy', [[tid]]))
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[tid]])
    return r

test(39, "Tool copy with copy=False on required code — fails without code", test_39)


def test_40():
    """Loan notes field accepts text"""
    loan_id = call(M, admin_uid, 'admin', 'tool.loan', 'create', [{
        'tool_id': test_tool_id, 'user_id': portal_uid_id, 'notes': 'Test notes 測試備註'
    }])
    data = call(M, admin_uid, 'admin', 'tool.loan', 'read', [[loan_id], ['notes']])[0]
    call(M, admin_uid, 'admin', 'tool.loan', 'unlink', [[loan_id]])
    if 'Test notes' not in (data['notes'] or ''):
        return f"Notes not saved correctly: {data['notes']}"
    return True

test(40, "Loan notes field accepts text (including CJK)", test_40)


# =====================================================
# Cleanup
# =====================================================
try:
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[test_tool_id]])
except Exception:
    pass
try:
    call(M, admin_uid, 'admin', 'tool.tool', 'unlink', [[test_tool2_id]])
except Exception:
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
