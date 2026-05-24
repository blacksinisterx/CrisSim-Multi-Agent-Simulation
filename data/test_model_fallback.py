#!/usr/bin/env python3
"""
Enhanced Model Fallback Testing Script
Tests all model chains with comprehensive error handling and quota management
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reasoning.llm_client import llm_call_with_cache, build_context_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('ModelFallbackTest')

def test_context():
    """Create a simple test context for API calls"""
    return {
        'agent_id': 'test_agent',
        'world_state': {
            'agents': [
                {'id': '1', 'kind': 'drone', 'pos': [2, 2], 'battery_level': 70},
                {'id': '2', 'kind': 'medic', 'pos': [2, 2], 'carrying': False}
            ],
            'hazards': [
                {'type': 'fire', 'pos': [5, 5], 'intensity': 3},
                {'type': 'rubble', 'pos': [3, 4]}
            ],
            'goals': [
                {'type': 'extinguish', 'target': [5, 5], 'urgency': 0.8}
            ],
            'tick': 10
        },
        'context': 'Fire at (5,5), agents at depot. Need immediate response plan.',
        'strategy': 'react',
        'tick': 10
    }

def test_strategy_fallback(strategy: str, max_attempts: int = 3):
    """Test a specific strategy with fallback handling"""
    logger.info(f"Testing strategy: {strategy}")
    
    context = test_context()
    context['strategy'] = strategy
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_attempts} for {strategy}")
            
            # Use our memory-aware LLM client
            result = llm_call_with_cache(
                context=context,
                strategy=strategy,
                high_importance=False
            )
            
            logger.info(f"✅ {strategy} successful on attempt {attempt + 1}")
            logger.info(f"Result type: {type(result)}")
            logger.info(f"Cache hit: {result.get('from_cache', False)}")
            
            if 'plan' in result:
                plan = result['plan']
                logger.info(f"Plan commands: {len(plan.get('commands', []))}")
                if plan.get('commands'):
                    logger.info(f"First command: {plan['commands'][0]}")
            
            return True, result
            
        except Exception as e:
            logger.error(f"❌ {strategy} attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(1)  # Brief delay before retry
            
    return False, None

def test_gemini_quota():
    """Test Gemini quota handling"""
    logger.info("🔥 Testing Gemini quota handling...")
    
    import google.generativeai as genai
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content("What is 2+2?")
        logger.info(f"✅ Gemini API working: {response.text[:50]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Gemini quota issue: {e}")
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            logger.warning("🚨 Gemini quota exceeded - fallback systems will activate")
        return False

def test_groq_models():
    """Test Groq model availability"""
    logger.info("🤖 Testing Groq model availability...")
    
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", "<YOUR_GROQ_API_KEY>"))
    
    models_to_test = [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile", 
        "llama-3.1-70b-versatile"
    ]
    
    working_models = []
    
    for model in models_to_test:
        try:
            response = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10
            )
            logger.info(f"✅ {model} working")
            working_models.append(model)
        except Exception as e:
            logger.error(f"❌ {model} failed: {e}")
    
    return working_models

def main():
    """Run comprehensive model fallback tests"""
    logger.info("🚀 Starting Enhanced Model Fallback Testing")
    logger.info("=" * 60)
    
    # Test 1: Check provider availability
    logger.info("1️⃣ Testing Provider Availability")
    gemini_working = test_gemini_quota()
    working_groq_models = test_groq_models()
    
    # Test 2: Test each strategy with fallback
    strategies = ["react", "reflexion", "cot"]
    results = {}
    
    logger.info("\n2️⃣ Testing Strategy Fallbacks")
    for strategy in strategies:
        success, result = test_strategy_fallback(strategy)
        results[strategy] = {"success": success, "result": result}
        time.sleep(2)  # Prevent rate limiting
    
    # Test 3: Summary Report
    logger.info("\n3️⃣ Summary Report")
    logger.info("=" * 40)
    logger.info(f"Gemini API: {'✅ Working' if gemini_working else '❌ Quota/Error'}")
    logger.info(f"Groq Models Working: {len(working_groq_models)}/3")
    for model in working_groq_models:
        logger.info(f"  ✅ {model}")
    
    logger.info("\nStrategy Results:")
    for strategy, result in results.items():
        status = "✅ Success" if result["success"] else "❌ Failed"
        logger.info(f"  {strategy}: {status}")
    
    # Test 4: Cache Performance  
    logger.info("\n4️⃣ Testing Cache Performance")
    context = test_context()
    
    # First call (should miss cache)
    result1 = llm_call_with_cache(context=context, strategy="react", high_importance=False)
    logger.info(f"First call - Cache hit: {result1.get('from_cache', False)}")
    
    # Second call (should hit cache)  
    result2 = llm_call_with_cache(context=context, strategy="react", high_importance=False)
    logger.info(f"Second call - Cache hit: {result2.get('from_cache', False)}")
    
    # Results summary
    logger.info("\n🎯 Final Assessment")
    if any(r["success"] for r in results.values()):
        logger.info("✅ Model fallback system is working")
        if working_groq_models:
            logger.info(f"✅ {len(working_groq_models)} Groq models available")
        if gemini_working:
            logger.info("✅ Gemini API responsive")
        else:
            logger.info("⚠️ Gemini quota reached - using Groq fallback")
    else:
        logger.error("❌ All model fallbacks failed - check API keys and quotas")
    
    return results

if __name__ == "__main__":
    results = main()
    
    # Save results to data folder
    results_file = os.path.join(os.path.dirname(__file__), "model_fallback_test_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": time.time(),
            "results": {k: {"success": v["success"]} for k, v in results.items()},
            "summary": "Model fallback testing completed"
        }, f, indent=2)
    
    logger.info(f"Results saved to: {results_file}")
