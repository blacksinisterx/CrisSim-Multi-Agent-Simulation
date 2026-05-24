# reasoning/reflexion.py
import os
import json
import logging
from typing import Dict, List, Any

# Set up logging for Reflexion strategy
logging.basicConfig(level=logging.INFO)
reflexion_logger = logging.getLogger('Reflexion')

# Memory path for reflexion learning
REFLEXION_MEMORY_PATH = "logs/reflexion_memory.json"

def reflexion_plan(context, scratchpad: str = ""):
    """
    Reflexion planning strategy entry point with learning and self-critique.
    Returns: ("final", <json string of {"commands": [...]}>)
    """
    # Check if LLM mode is enabled
    use_llm = os.getenv("LLM_PROVIDER", "ollama").lower() in ["gemini", "groq", "ollama"]
    
    if use_llm:
        try:
            provider = os.getenv("LLM_PROVIDER", "ollama").lower()
            # reflexion_logger.info(f"Using LLM-powered Reflexion strategy with {provider.upper()} provider")  # Reduced logging
            plan_dict = reflexion_with_llm_integration(context)
        except Exception as e:
            reflexion_logger.error(f"LLM integration failed: {e} - NO FALLBACK")
            plan_dict = {"commands": [], "strategy": "REFLEXION_FAILED_NO_FALLBACK", "error": str(e)}
    else:
        # NO RULE-BASED STRATEGY - return empty if no LLM
        reflexion_logger.error("No LLM provider available - NO RULE-BASED FALLBACK")
        plan_dict = {"commands": [], "strategy": "REFLEXION_NO_LLM_NO_FALLBACK", "error": "No LLM provider"}
    
    return ("final", json.dumps(plan_dict))

def reflexion_with_llm_integration(context: dict) -> dict:
    """
    Reflexion strategy with LLM-powered self-critique and learning.
    """
    try:
        from .llm_client import llm_complete_reflexion
        
        # Load previous learning experiences
        memory = load_reflexion_memory()
        
        # Format crisis situation for reflexion
        agents = context.get("agents", [])
        fires = context.get("fires", [])
        rubble = context.get("rubble", [])
        survivors = context.get("survivors", [])
        depots = context.get("depots", [(0, 0)])
        hospitals = context.get("hospitals", [(5, 0)])
        
        # Create reflexion context with learning history
        reflexion_context = {
            "current_crisis": {
                "fires": fires,
                "rubble": rubble,
                "survivors": survivors,
                "depots": depots,
                "hospitals": hospitals
            },
            "available_agents": []
        }
        
        for agent in agents:
            agent_data = {
                "id": agent.get('id'),
                "type": agent.get('kind', 'unknown'),
                "position": agent.get('pos'),
                "status": agent.get('status', 'idle')
            }
            
            if agent.get('kind') == 'truck':
                agent_data.update({
                    "battery": agent.get('battery_level', 0),
                    "water": agent.get('water', 0),
                    "tools": agent.get('tools', 0)
                })
            elif agent.get('kind') == 'medic':
                agent_data.update({
                    "battery": agent.get('battery_level', 0),
                    "medical_supplies": agent.get('supplies', 0)
                })
            elif agent.get('kind') == 'drone':
                agent_data.update({
                    "battery": agent.get('battery_level', 0),
                    "camera_active": agent.get('camera', False)
                })
            
            reflexion_context["available_agents"].append(agent_data)
        
        # Add learning history to context
        reflexion_context["learned_lessons"] = memory.get("lessons", [])
        reflexion_context["performance_history"] = memory.get("performance", [])
        
        # Generate reflexion-based plan
        reflexion_logger.info("Generating reflexion plan with learned lessons")
        response = llm_complete_reflexion(reflexion_context)
        
        if response and "commands" in response:
            reflexion_logger.info(f"Reflexion strategy generated {len(response['commands'])} commands")
            
            # Store current decision for future learning
            if "self_critique" in response:
                store_reflexion_decision(context, response)
            
            return {"commands": response["commands"]}
        else:
            reflexion_logger.error("Invalid LLM response - NO FALLBACK")
            return {"commands": [], "strategy": "REFLEXION_INVALID_RESPONSE_NO_FALLBACK", "error": "Invalid LLM response"}
            
    except Exception as e:
        reflexion_logger.error(f"Reflexion LLM integration failed: {e} - NO FALLBACK")
        return {"commands": [], "strategy": "REFLEXION_FAILED_NO_FALLBACK", "error": str(e)}

def load_reflexion_memory() -> Dict[str, Any]:
    """Load reflexion memory from disk."""
    try:
        os.makedirs(os.path.dirname(REFLEXION_MEMORY_PATH), exist_ok=True)
        if os.path.exists(REFLEXION_MEMORY_PATH):
            with open(REFLEXION_MEMORY_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        reflexion_logger.warning(f"Failed to load reflexion memory: {e}")
    
    return {
        "lessons": [],
        "performance": [],
        "simple_rules": []
    }

def save_reflexion_memory(memory: Dict[str, Any]):
    """Save reflexion memory to disk."""
    try:
        os.makedirs(os.path.dirname(REFLEXION_MEMORY_PATH), exist_ok=True)
        with open(REFLEXION_MEMORY_PATH, 'w') as f:
            json.dump(memory, f, indent=2)
    except Exception as e:
        reflexion_logger.error(f"Failed to save reflexion memory: {e}")

def store_reflexion_decision(context: dict, response: dict):
    """Store current decision for future learning."""
    memory = load_reflexion_memory()
    
    decision_record = {
        "context_summary": {
            "fires": len(context.get("fires", [])),
            "rubble": len(context.get("rubble", [])),
            "survivors": len(context.get("survivors", []))
        },
        "decision": response.get("self_critique", ""),
        "commands_count": len(response.get("commands", []))
    }
    
    memory.setdefault("performance", []).append(decision_record)
    # Keep only last 10 decisions
    memory["performance"] = memory["performance"][-10:]
    
    save_reflexion_memory(memory)

def update_simple_learning(context: dict, commands: List[dict]):
    """Update simple learning rules based on context."""
    memory = load_reflexion_memory()
    rules = memory.setdefault("simple_rules", [])
    
    # Learn from situation patterns
    if context.get("survivors") and "survivors_first" not in rules:
        rules.append("survivors_first")
        reflexion_logger.info("Learned rule: survivors_first")
    
    if context.get("rubble") and "rubble_blocking" not in rules:
        rules.append("rubble_blocking")  
        reflexion_logger.info("Learned rule: rubble_blocking")
    
    memory["simple_rules"] = list(set(rules))  # Remove duplicates
    save_reflexion_memory(memory)

def critique_and_update(transcript: str):
    """Legacy function for compatibility - enhanced with reflexion learning."""
    reflexion_logger.info("Processing crisis transcript for learning")
    
    try:
        from .llm_client import llm_complete
        
        prompt = (
            "As a crisis management expert using Reflexion methodology, analyze this transcript. "
            "Identify exactly 3 key mistakes and 3 concrete improvement rules for future crises. "
            "Focus on decision quality, coordination efficiency, and life-saving effectiveness. "
            "Format: MISTAKES: 1. ... 2. ... 3. ... RULES: 1. ... 2. ... 3. ..."
        )
        
        analysis = llm_complete(prompt + "\n\nTranscript:\n" + transcript, strategy="reflexion")
        
        # Store in reflexion memory
        memory = load_reflexion_memory()
        memory.setdefault("lessons", []).append({
            "transcript_analysis": analysis,
            "timestamp": json.dumps({"transcript_length": len(transcript)})
        })
        
        # Keep only last 5 lessons
        memory["lessons"] = memory["lessons"][-5:]
        save_reflexion_memory(memory)
        
        reflexion_logger.info("Updated reflexion memory with transcript analysis")
        return analysis
        
    except Exception as e:
        reflexion_logger.error(f"Critique and update failed: {e}")
        return "Failed to analyze transcript - LLM unavailable"
