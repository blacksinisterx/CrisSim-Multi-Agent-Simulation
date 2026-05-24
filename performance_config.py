#!/usr/bin/env python3
"""
Performance optimization configuration for crisis simulation.
Simplified single-mode configuration optimized for compressed JSON output.
"""

import os

# Single optimized performance configuration
PERFORMANCE_CONFIG = {
    "max_decision_reuse": 1,           # Minimal caching for fresh decisions
    "cache_timeout": 1,                # Short cache timeout
    "use_rule_fallback": False,        # Pure LLM decisions
    "ollama_num_predict": 400,         # Match actual usage in llm_client.py (was 200)
    "ollama_temperature": 0.1,         # Low temperature for consistent multi-agent output
    "gemini_max_tokens": 1536,         # High quality token limit
    "groq_max_tokens": 1536,           # High quality token limit
    "batch_decisions": False           # Individual decision making
}

def get_performance_config():
    """Get the optimized performance configuration."""
    return PERFORMANCE_CONFIG

# Legacy compatibility functions (now just return the single config)
def set_speed_mode():
    """Legacy function - now uses optimized config."""
    print("🚀 Using optimized configuration (legacy speed mode called)")

def set_quality_mode():
    """Legacy function - now uses optimized config."""
    # print("🧠 Using optimized configuration (legacy quality mode called)")  # Reduced logging

if __name__ == "__main__":
    print("Optimized single-mode configuration:")
    print(f"Configuration: {get_performance_config()}")
