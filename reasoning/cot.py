# reasoning/cot.py
import json
import os
import logging

# Set up logging for Chain-of-Thought strategy
logging.basicConfig(level=logging.INFO)
cot_logger = logging.getLogger('ChainOfThought')

def cot_plan(context, scratchpad: str = ""):
    """
    Chain-of-Thought planning strategy entry point.
    Returns: ("final", <json string of {"commands": [...]}>)
    """
    # Check if LLM mode is enabled
    use_llm = os.getenv("LLM_PROVIDER", "ollama").lower() in ["gemini", "groq", "ollama"]
    
    if use_llm:
        try:
            provider = os.getenv("LLM_PROVIDER", "ollama").lower()
            # cot_logger.info(f"Using LLM-powered Chain-of-Thought strategy with {provider.upper()} provider")  # Reduced logging
            plan_dict = cot_with_llm_integration(context)
        except Exception as e:
            cot_logger.error(f"LLM integration failed: {e} - NO FALLBACK")
            plan_dict = {"commands": [], "strategy": "COT_FAILED_NO_FALLBACK", "error": str(e)}
    else:
        # NO RULE-BASED STRATEGY - return empty if no LLM
        cot_logger.error("No LLM provider available - NO RULE-BASED FALLBACK")
        plan_dict = {"commands": [], "strategy": "COT_NO_LLM_NO_FALLBACK", "error": "No LLM provider"}
    
    return ("final", json.dumps(plan_dict))

def cot_with_llm_integration(context: dict) -> dict:
    """
    Chain-of-Thought strategy with step-by-step reasoning using Gemini 2.5 Flash.
    """
    try:
        from .llm_client import llm_complete_cot
        
        # Format crisis situation for step-by-step reasoning
        agents = context.get("agents", [])
        fires = context.get("fires", [])
        rubble = context.get("rubble", [])
        survivors = context.get("survivors", [])
        depots = context.get("depots", [(0, 0)])
        hospitals = context.get("hospitals", [(5, 0)])
        
        # Create detailed context for CoT reasoning
        cot_context = {
            "emergency_situation": {
                "fires": fires,
                "rubble": rubble,
                "survivors": survivors,
                "depots": depots,
                "hospitals": hospitals,
                "total_threats": len(fires) + len(rubble),
                "lives_at_risk": len(survivors)
            },
            "response_capabilities": []
        }
        
        for agent in agents:
            agent_capability = {
                "id": agent.get('id'),
                "type": agent.get('kind', 'unknown'),
                "location": agent.get('pos'),
                "operational_status": agent.get('status', 'idle')
            }
            
            # Add type-specific capabilities
            if agent.get('kind') == 'truck':
                agent_capability.update({
                    "battery_level": agent.get('battery_level', 0),
                    "water_capacity": agent.get('water', 0),
                    "tools_available": agent.get('tools', 0),
                    "primary_role": "fire_suppression_and_rubble_clearing"
                })
            elif agent.get('kind') == 'medic':
                agent_capability.update({
                    "battery_level": agent.get('battery_level', 0),
                    "medical_supplies": agent.get('supplies', 0),
                    "primary_role": "survivor_rescue_and_medical_care"
                })
            elif agent.get('kind') == 'drone':
                agent_capability.update({
                    "battery_level": agent.get('battery_level', 0),
                    "surveillance_active": agent.get('camera', False),
                    "primary_role": "reconnaissance_and_coordination"
                })
            
            cot_context["response_capabilities"].append(agent_capability)
        
        # Generate Chain-of-Thought plan
        cot_logger.info("Generating step-by-step reasoning with Gemini 2.5 Flash")
        response = llm_complete_cot(cot_context)
        
        if response and "commands" in response:
            cot_logger.info(f"CoT strategy completed reasoning with {len(response['commands'])} commands")
            return {"commands": response["commands"]}
        else:
            cot_logger.error("Invalid LLM response - NO FALLBACK")
            return {"commands": [], "strategy": "COT_INVALID_RESPONSE_NO_FALLBACK", "error": "Invalid LLM response"}
            
    except Exception as e:
        cot_logger.error(f"Chain-of-Thought LLM integration failed: {e} - NO FALLBACK")
        return {"commands": [], "strategy": "COT_FAILED_NO_FALLBACK", "error": str(e)}
