#!/usr/bin/env python3
"""
Test Global State Workflow - Verify the global state architecture works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workflow_state import reset_workflow, get_workflow_summary
from tools.strategy_creation import create_search_strategy

def test_global_state_workflow():
    """Test that global state workflow functions return lightweight responses"""
    print("🧪 Testing Global State Workflow Architecture")
    
    # Reset workflow state
    reset_result = reset_workflow()
    print(f"🔄 Workflow reset: {reset_result['success']}")
    
    # Test Phase 1: Strategy Creation
    print(f"\n📊 PHASE 1: Strategy Creation")
    strategy_status = create_search_strategy(
        query="Senior Software Engineer - Backend Systems",
        location="San Francisco Bay Area",
        job_description="Build scalable backend systems with Python and microservices"
    )
    
    print(f"   Strategy Status: {strategy_status}")
    
    # Verify lightweight response
    expected_keys = {'success', 'strategy_id', 'query', 'location', 'message'}
    actual_keys = set(strategy_status.keys())
    
    # Check that response is lightweight (no large 'strategy' key)
    if 'strategy' in actual_keys:
        print(f"   ❌ FAILED: Strategy function still returning large 'strategy' object")
        return False
    
    if not expected_keys.issubset(actual_keys):
        print(f"   ❌ FAILED: Missing expected keys. Expected: {expected_keys}, Got: {actual_keys}")
        return False
    
    if not strategy_status.get('success', False):
        print(f"   ❌ FAILED: Strategy creation failed: {strategy_status}")
        return False
    
    print(f"   ✅ SUCCESS: Strategy function returns lightweight response")
    print(f"   📏 Response size: {len(str(strategy_status))} characters")
    
    # Test workflow status
    print(f"\n📊 Workflow Status Check")
    workflow_status = get_workflow_summary()
    print(f"   Workflow Status: {workflow_status}")
    
    # Verify workflow phase progression
    expected_phase = workflow_status.get('current_phase', '')
    if 'strategy' not in expected_phase:
        print(f"   ❌ FAILED: Expected strategy phase, got: {expected_phase}")
        return False
    
    print(f"   ✅ SUCCESS: Workflow is in correct phase: {expected_phase}")
    
    return True

def test_response_size_comparison():
    """Compare old vs new response sizes"""
    print(f"\n🧪 Testing Response Size Comparison")
    
    # Test strategy creation response size
    strategy_status = create_search_strategy(
        query="Test Engineer",
        location="Test Location"
    )
    
    response_size = len(str(strategy_status))
    print(f"   📏 Global State Response Size: {response_size:,} characters")
    
    # This should be dramatically smaller than before (< 1KB vs > 50KB)
    if response_size > 1000:  # 1KB threshold
        print(f"   ⚠️  WARNING: Response larger than expected ({response_size:,} chars)")
        print(f"   Expected < 1,000 characters for lightweight response")
    else:
        print(f"   ✅ SUCCESS: Response is lightweight ({response_size:,} chars)")
    
    return response_size < 5000  # Allow up to 5KB as acceptable

def test_workflow_state_persistence():
    """Test that data persists in global state across function calls"""
    print(f"\n🧪 Testing Global State Persistence")
    
    # Reset and create strategy
    reset_workflow()
    
    strategy_status = create_search_strategy(
        query="Data Engineer",
        location="New York"
    )
    
    if not strategy_status.get('success', False):
        print(f"   ❌ FAILED: Strategy creation failed")
        return False
    
    # Check workflow status shows strategy exists
    workflow_status = get_workflow_summary()
    
    # Data should be accessible through workflow state
    if workflow_status.get('current_phase') != 'strategy_created':
        print(f"   ❌ FAILED: Strategy not persisted in global state")
        print(f"   Expected phase: strategy_created, Got: {workflow_status.get('current_phase')}")
        return False
    
    print(f"   ✅ SUCCESS: Strategy persisted in global state")
    print(f"   📊 Workflow ID: {workflow_status.get('workflow_id', 'Unknown')}")
    
    return True

if __name__ == "__main__":
    print("🚀 Testing Global State Architecture")
    
    test1_pass = test_global_state_workflow()
    test2_pass = test_response_size_comparison()
    test3_pass = test_workflow_state_persistence()
    
    print(f"\n📊 Test Results:")
    print(f"   Global state workflow: {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"   Response size check: {'✅ PASS' if test2_pass else '❌ FAIL'}")
    print(f"   State persistence: {'✅ PASS' if test3_pass else '❌ FAIL'}")
    
    if test1_pass and test2_pass and test3_pass:
        print("🎉 All global state architecture tests passed!")
        print("The workflow should now handle 10+ candidates without timeouts.")
        sys.exit(0)
    else:
        print("⚠️ Some global state tests failed!")
        sys.exit(1)