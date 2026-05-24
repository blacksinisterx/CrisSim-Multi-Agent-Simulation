#!/usr/bin/env python3
"""
Enhanced ReAct strategy with LLM integration for crisis management.
"""

import json
import sys
import os
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .llm_client import llm_complete, llm_complete_with_tools
try:
    from tools.llm_tools import CRISIS_TOOLS, execute_tool
except ImportError:
    # Fallback if tools not available
    CRISIS_TOOLS = []
    def execute_tool(name, params):
        return {"error": "Tools not available"}

def react_with_llm(context: Dict) -> Dict[str, List[Dict]]:
    """
    ReAct strategy using LLM for intelligent crisis management.
    
    This implements the Thought-Action-Observation cycle:
    1. THOUGHT: Analyze the crisis situation
    2. ACTION: Use tools to gather information and plan
    3. OBSERVATION: Process results and decide on agent commands
    """
    
    # Extract context information
    agents = context.get("agents", [])
    fires = context.get("fires", [])
    rubble = context.get("rubble", [])
    survivors = context.get("survivors", [])
    depot = context.get("depot", [1, 1])
    
    # Format crisis situation for LLM
    crisis_prompt = f"""
CRISIS SITUATION ANALYSIS:

Current Emergency State:
- {len(fires)} active fires at positions: {fires}
- {len(rubble)} rubble blockages at: {rubble}  
- {len(survivors)} survivors needing rescue at: {survivors}
- Emergency depot located at: {depot}

Available Response Agents:
"""
    
    for agent in agents:
        agent_info = f"- {agent.get('kind', 'unknown')} (ID: {agent.get('id')}) at {agent.get('pos')}"
        if agent.get('kind') == 'truck':
            agent_info += f" [Battery: {agent.get('battery_level', 0)}, Water: {agent.get('water', 0)}, Tools: {agent.get('tools', 0)}]"
        elif agent.get('battery_level'):
            agent_info += f" [Battery: {agent.get('battery_level')}]"
        if agent.get('carrying'):
            agent_info += " [CARRYING SURVIVOR]"
        crisis_prompt += agent_info + "\n"
    
    crisis_prompt += """
TASK: Using ReAct methodology, analyze this crisis and provide specific agent commands.

Think through:
1. What is the most urgent threat requiring immediate attention?
2. Which agents are best positioned to handle each threat?
3. What sequence of actions will maximize lives saved and minimize damage?
4. How should agents coordinate to avoid conflicts and maximize efficiency?

Provide response as JSON with:
{
  "thought_process": "your reasoning about the situation",
  "priority_actions": ["list of immediate priorities"], 
  "commands": [
    {
      "agent_id": "agent_id",
      "type": "move" or "act",
      "to": [x, y] (for move commands),
      "action_name": "action" (for act commands),
      "reasoning": "why this action"
    }
  ],
  "strategy": "overall approach being taken"
}
"""
    
    try:
        # Get LLM response
        llm_response = llm_complete(crisis_prompt, strategy="react", temperature=0.3)
        
        # Parse JSON response
        try:
            response_data = json.loads(llm_response)
        except json.JSONDecodeError:
            # If JSON parsing fails, extract commands section
            if '"commands"' in llm_response:
                start = llm_response.find('"commands"')
                commands_section = llm_response[start:]
                response_data = {"commands": []}
            else:
                response_data = {"commands": []}
        
        commands = response_data.get("commands", [])
        
        # Validate and filter commands
        valid_commands = []
        for cmd in commands:
            if isinstance(cmd, dict) and "agent_id" in cmd and "type" in cmd:
                # Ensure agent exists
                agent_exists = any(a.get("id") == cmd["agent_id"] for a in agents)
                if agent_exists:
                    valid_commands.append(cmd)
        
        # If no valid commands from LLM, return error - NO FALLBACK
        if not valid_commands:
            print("⚠️ LLM provided no valid commands - NO FALLBACK")
            return {
                "commands": [],
                "error": "LLM_NO_VALID_COMMANDS",
                "success": False
            }
        
        print(f"🧠 LLM ReAct generated {len(valid_commands)} commands")
        if response_data.get("thought_process"):
            print(f"💭 LLM Reasoning: {response_data['thought_process'][:200]}...")
            
        return {"commands": valid_commands}
        
    except Exception as e:
        print(f"❌ LLM ReAct error: {e}")
        # NO FALLBACK - return error
        return {
            "commands": [],
            "error": f"REACT_LLM_FAILED: {str(e)}",
            "success": False
        }

# DEAD CODE - fallback function removed per user requirement
# _fallback_react function eliminated

def react_with_tools_llm(context: Dict) -> Dict[str, List[Dict]]:
    """
    Enhanced ReAct with tool calling for complex crisis analysis.
    """
    
    # Prepare context for tool usage
    world_state = {
        "agents": context.get("agents", []),
        "fires": [{"pos": f, "type": "fire"} for f in context.get("fires", [])],
        "rubble": [{"pos": r, "type": "rubble"} for r in context.get("rubble", [])],
        "survivors": [{"pos": s, "type": "survivor"} for s in context.get("survivors", [])]
    }
    
    # Messages for tool calling
    messages = [
        {
            "role": "user",
            "content": f"""
Analyze this crisis situation and use available tools to make optimal decisions:

Current State: {json.dumps(world_state, indent=2)}

Use the assess_crisis_situation tool to evaluate threats, then coordinate_multi_agent_response to assign tasks.
Provide specific agent commands based on tool analysis.
"""
        }
    ]
    
    try:
        # Use LLM with tools
        tool_response = llm_complete_with_tools(messages, CRISIS_TOOLS, strategy="react")
        
        # Process tool calls if any
        if tool_response.get("tool_calls"):
            for tool_call in tool_response["tool_calls"]:
                tool_name = tool_call.get("name")
                tool_params = tool_call.get("parameters", {})
                
                print(f"🔧 Executing tool: {tool_name}")
                tool_result = execute_tool(tool_name, tool_params)
                print(f"📊 Tool result: {tool_result}")
        
        # Parse commands from response
        content = tool_response.get("content", "{}")
        try:
            response_data = json.loads(content)
            commands = response_data.get("commands", [])
            
            if commands:
                print(f"🛠️ Tool-enhanced ReAct generated {len(commands)} commands")
                return {"commands": commands}
                
        except json.JSONDecodeError:
            pass
        
        # Fall back to basic ReAct if tool calling doesn't work
        return react_with_llm(context)
        
    except Exception as e:
        print(f"❌ Tool-enhanced ReAct error: {e}")
        # NO FALLBACK - return error
        return {
            "commands": [],
            "error": f"TOOL_REACT_LLM_FAILED: {str(e)}",
            "success": False
        }
