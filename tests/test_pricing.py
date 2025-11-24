#!/usr/bin/env python3

from __future__ import annotations

import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Try to import pytest, but make it optional
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create a dummy fixture decorator for when pytest is not available
    def pytest_fixture(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    pytest = type('pytest', (), {'fixture': pytest_fixture})

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cai.util import COST_TRACKER, calculate_model_cost


if PYTEST_AVAILABLE:
    @pytest.fixture(autouse=True)
    def setup_test():
        """Clear the pricing cache before each test"""
        COST_TRACKER.model_pricing_cache.clear()
        yield
        COST_TRACKER.model_pricing_cache.clear()
else:
    def setup_test():
        """Clear the pricing cache before each test"""
        COST_TRACKER.model_pricing_cache.clear()


def test_local_models_return_zero_cost():
    """Test that local models return zero cost"""
    if not PYTEST_AVAILABLE:
        setup_test()
        
    local_models = [
        "qwen3:14b",
        "qwen3:32b", 
        "qwen2.5:14b",
        "qwen2.5:7b",
        "qwen2.5:72b",
        "llama3.1:8b",
        "llama3.1:70b",
        "mistral:7b",
        "mistral:latest",
        "codellama:13b",
        "llama3.1",
        "ollama/qwen2.5",
        "deepseek-coder:6.7b",
        "phi3:mini",
        "gemma:7b",
        "vicuna:13b",
        "alpaca:7b",
        "orca-mini:3b",
        "neural-chat:7b",
        "starling-lm:7b",
        "zephyr:7b",
        "openchat:7b",
        "wizard-coder:15b",
        "sqlcoder:7b",
        "magicoder:7b",
        "dolphin-mixtral:8x7b",
        "nous-hermes2:10.7b",
        "yi:34b",
        "qwq:32b",
        "alias01:14b",
        "alias01:14b-ctx-32000",
        "alias00:14b"
    ]
    
    print("\n" + "="*80)
    print("LOCAL MODELS PRICING TEST")
    print("="*80)
    
    for model in local_models:
        with patch('requests.get') as mock_get:
            # Mock LiteLLM API to return empty response (model not found)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}  # Empty response, model not found
            mock_get.return_value = mock_response
            
            pricing = COST_TRACKER.get_model_pricing(model)
            cost = calculate_model_cost(model, 100, 50)
            
            # Show pricing information
            print(f"Model: {model:<25} | Pricing: {pricing} | Cost (100/50 tokens): ${cost:.6f}")
            
            if PYTEST_AVAILABLE:
                assert pricing == (0.0, 0.0), f"Model {model} should have zero pricing, got {pricing}"
                assert cost == 0.0, f"Model {model} should have zero cost, got {cost}"
            else:
                if pricing != (0.0, 0.0):
                    raise AssertionError(f"Model {model} should have zero pricing, got {pricing}")
                if cost != 0.0:
                    raise AssertionError(f"Model {model} should have zero cost, got {cost}")
    
    print("="*80)


def test_paid_models_return_nonzero_cost():
    """Test that known paid models return non-zero cost"""
    if not PYTEST_AVAILABLE:
        setup_test()
        
    paid_models_with_expected_pricing = {
        "gpt-4": {"input_cost_per_token": 0.00003, "output_cost_per_token": 0.00006},
        "gpt-4o": {"input_cost_per_token": 0.0000025, "output_cost_per_token": 0.00001},
        "claude-3-sonnet-20240229": {"input_cost_per_token": 0.000003, "output_cost_per_token": 0.000015},
        "claude-3-5-sonnet-20241022": {"input_cost_per_token": 0.000003, "output_cost_per_token": 0.000015}
    }
    
    print("\n" + "="*80)
    print("PAID MODELS PRICING TEST")
    print("="*80)
    
    for model, expected_pricing in paid_models_with_expected_pricing.items():
        with patch('requests.get') as mock_get:
            # Mock LiteLLM API to return pricing for paid models
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                model: expected_pricing
            }
            mock_get.return_value = mock_response
            
            pricing = COST_TRACKER.get_model_pricing(model)
            cost = calculate_model_cost(model, 100, 50)
            
            # Show pricing information
            print(f"Model: {model:<30} | Pricing: {pricing} | Cost (100/50 tokens): ${cost:.6f}")
            
            if PYTEST_AVAILABLE:
                assert pricing[0] > 0 or pricing[1] > 0, f"Model {model} should have non-zero pricing, got {pricing}"
                assert cost > 0, f"Model {model} should have non-zero cost, got {cost}"
            else:
                if not (pricing[0] > 0 or pricing[1] > 0):
                    raise AssertionError(f"Model {model} should have non-zero pricing, got {pricing}")
                if not (cost > 0):
                    raise AssertionError(f"Model {model} should have non-zero cost, got {cost}")
    
    print("="*80)


def test_private_model_alias0_with_pricing_json():
    """Test that alias0 works correctly when defined in pricing.json"""
    if not PYTEST_AVAILABLE:
        setup_test()
        
    # Create a pricing.json with alias0 configuration
    pricing_config = {
        "alias0": {
            "max_tokens": 128000,
            "max_input_tokens": 200000,
            "max_output_tokens": 128000,
            "input_cost_per_token": 5e-06,
            "output_cost_per_token": 5e-05,
            "litellm_provider": "openai",
            "mode": "chat",
            "supports_function_calling": True,
            "supports_vision": True
        }
    }
    
    print("\n" + "="*80)
    print("PRIVATE MODEL (alias0) PRICING TEST")
    print("="*80)
    
    # Mock the file reading to simulate pricing.json with alias0
    with patch('pathlib.Path') as mock_path:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_file.read.return_value = json.dumps(pricing_config)
            mock_open.return_value = mock_file
            
            # Mock json.load to return our config
            with patch('json.load', return_value=pricing_config):
                pricing = COST_TRACKER.get_model_pricing("alias0")
                cost = calculate_model_cost("alias0", 100, 50)
                
                expected_pricing = (5e-06, 5e-05)
                expected_cost = 100 * 5e-06 + 50 * 5e-05  # 0.0030
                
                # Show pricing information
                print(f"Model: alias0                  | Pricing: {pricing} | Cost (100/50 tokens): ${cost:.6f}")
                print(f"Expected pricing: {expected_pricing} | Expected cost: ${expected_cost:.6f}")
                
                if PYTEST_AVAILABLE:
                    assert pricing == expected_pricing, f"alias0 should have pricing {expected_pricing}, got {pricing}"
                    assert abs(cost - expected_cost) < 1e-10, f"alias0 should have cost {expected_cost}, got {cost}"
                else:
                    if pricing != expected_pricing:
                        raise AssertionError(f"alias0 should have pricing {expected_pricing}, got {pricing}")
                    if abs(cost - expected_cost) >= 1e-10:
                        raise AssertionError(f"alias0 should have cost {expected_cost}, got {cost}")
    
    print("="*80)


def test_reset_cost_for_local_model():
    """Test the reset_cost_for_local_model function"""
    if not PYTEST_AVAILABLE:
        setup_test()
    
    print("\n" + "="*80)
    print("RESET COST FOR LOCAL MODEL TEST")
    print("="*80)
        
    # Test with a free model
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Model not found, will return (0.0, 0.0)
        mock_get.return_value = mock_response
        
        result = COST_TRACKER.reset_cost_for_local_model("qwen3:14b")
        pricing = COST_TRACKER.get_model_pricing("qwen3:14b")
        
        print(f"Model: qwen3:14b (free)        | Pricing: {pricing} | Reset result: {result}")
        
        if PYTEST_AVAILABLE:
            assert result == True, "qwen3:14b should be identified as a free model"
        else:
            if result != True:
                raise AssertionError("qwen3:14b should be identified as a free model")
    
    # Test with a paid model
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "gpt-4": {
                "input_cost_per_token": 0.00003,
                "output_cost_per_token": 0.00006
            }
        }
        mock_get.return_value = mock_response
        
        result = COST_TRACKER.reset_cost_for_local_model("gpt-4")
        pricing = COST_TRACKER.get_model_pricing("gpt-4")
        
        print(f"Model: gpt-4 (paid)            | Pricing: {pricing} | Reset result: {result}")
        
        if PYTEST_AVAILABLE:
            assert result == False, "gpt-4 should not be identified as a free model"
        else:
            if result != False:
                raise AssertionError("gpt-4 should not be identified as a free model")
    
    print("="*80)


def test_model_not_found_anywhere_returns_zero():
    """Test that models not found anywhere return zero cost"""
    if not PYTEST_AVAILABLE:
        setup_test()
        
    unknown_model = "unknown-model-12345"
    
    print("\n" + "="*80)
    print("UNKNOWN MODEL PRICING TEST")
    print("="*80)
    
    with patch('pathlib.Path') as mock_path:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False  # No pricing.json
        mock_path.return_value = mock_path_instance
        
        with patch('requests.get') as mock_get:
            # Mock LiteLLM API to return empty response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}  # Model not found
            mock_get.return_value = mock_response
            
            pricing = COST_TRACKER.get_model_pricing(unknown_model)
            cost = calculate_model_cost(unknown_model, 100, 50)
            
            # Show pricing information
            print(f"Model: {unknown_model:<20} | Pricing: {pricing} | Cost (100/50 tokens): ${cost:.6f}")
            
            if PYTEST_AVAILABLE:
                assert pricing == (0.0, 0.0), f"Unknown model should have zero pricing, got {pricing}"
                assert cost == 0.0, f"Unknown model should have zero cost, got {cost}"
            else:
                if pricing != (0.0, 0.0):
                    raise AssertionError(f"Unknown model should have zero pricing, got {pricing}")
                if cost != 0.0:
                    raise AssertionError(f"Unknown model should have zero cost, got {cost}")
    
    print("="*80)


def test_model_not_in_pricing_json_falls_back_to_litellm():
    """Test that models not in pricing.json fall back to LiteLLM API"""
    if not PYTEST_AVAILABLE:
        setup_test()
        
    # Create a pricing.json with only alias0
    pricing_config = {
        "alias0": {
            "input_cost_per_token": 5e-06,
            "output_cost_per_token": 5e-05
        }
    }
    
    print("\n" + "="*80)
    print("PRICING.JSON vs LITELLM FALLBACK TEST")
    print("="*80)
    
    with patch('pathlib.Path') as mock_path:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file
            
            with patch('json.load', return_value=pricing_config):
                with patch('requests.get') as mock_get:
                    # Mock LiteLLM API response for gpt-4
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "gpt-4": {
                            "input_cost_per_token": 0.00003,
                            "output_cost_per_token": 0.00006
                        }
                    }
                    mock_get.return_value = mock_response
                    
                    # Test that gpt-4 (not in pricing.json) uses LiteLLM
                    pricing = COST_TRACKER.get_model_pricing("gpt-4")
                    expected_gpt4_pricing = (0.00003, 0.00006)
                    cost_gpt4 = calculate_model_cost("gpt-4", 100, 50)
                    
                    # Test that alias0 (in pricing.json) uses local pricing
                    pricing_alias0 = COST_TRACKER.get_model_pricing("alias0")
                    expected_alias0_pricing = (5e-06, 5e-05)
                    cost_alias0 = calculate_model_cost("alias0", 100, 50)
                    
                    # Show pricing information
                    print(f"Model: gpt-4 (from LiteLLM)     | Pricing: {pricing} | Cost (100/50 tokens): ${cost_gpt4:.6f}")
                    print(f"Model: alias0 (from pricing.json) | Pricing: {pricing_alias0} | Cost (100/50 tokens): ${cost_alias0:.6f}")
                    
                    if PYTEST_AVAILABLE:
                        assert pricing == expected_gpt4_pricing, f"gpt-4 should use LiteLLM pricing, got {pricing}"
                        assert pricing_alias0 == expected_alias0_pricing, f"alias0 should use local pricing, got {pricing_alias0}"
                    else:
                        if pricing != expected_gpt4_pricing:
                            raise AssertionError(f"gpt-4 should use LiteLLM pricing, got {pricing}")
                        if pricing_alias0 != expected_alias0_pricing:
                            raise AssertionError(f"alias0 should use local pricing, got {pricing_alias0}")
    
    print("="*80)


# Fallback for direct execution
def run_all_tests():
    """Run all tests and report results - for direct execution"""
    print("Running pricing tests...")
    print("=" * 50)
    print("NOTE: This will show detailed pricing information for all models tested")
    print("=" * 50)
    
    test_functions = [
        test_local_models_return_zero_cost,
        test_paid_models_return_nonzero_cost,
        test_private_model_alias0_with_pricing_json,
        test_reset_cost_for_local_model,
        test_model_not_found_anywhere_returns_zero,
        test_model_not_in_pricing_json_falls_back_to_litellm
    ]
    
    passed = 0
    failed = 0
    
    # Setup
    COST_TRACKER.model_pricing_cache.clear()
    
    for test_func in test_functions:
        try:
            COST_TRACKER.model_pricing_cache.clear()  # Clear before each test
            print(f"\n🧪 Running: {test_func.__name__}")
            test_func()
            print(f"✅ PASSED: {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {test_func.__name__}")
            print(f"  - Exception: {e}")
            failed += 1
        print()
    
    print("=" * 80)
    print(f"FINAL TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed == 0:
        print("🎉 All tests passed! ✅")
        print("\nSUMMARY:")
        print("- Local models correctly return zero cost")
        print("- Paid models correctly return non-zero cost") 
        print("- Private models (alias0) work with pricing.json")
        print("- Reset cost function works correctly")
        print("- Unknown models default to zero cost")
        print("- Fallback from pricing.json to LiteLLM works")
        return True
    else:
        print("💥 Some tests failed! ❌")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1) 