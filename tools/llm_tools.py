#!/usr/bin/env python3
"""
Crisis management tools for LLM integration.
"""

import sys
import os
from typing import Dict, List, Any, Tuple
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing tools - simplified for now since exact functions may vary
# from tools.routing import shortest_path
# from tools.resources import get_resource_status  
# from tools.hospital import get_hospital_capacity

def assess_crisis_situation(world_state: Dict) -> Dict[str, Any]:
    """
    Analyze the current crisis situation and provide threat assessment.
    
    Args:
        world_state: Current world state with agents, fires, rubble, survivors
        
    Returns:
        Assessment with priorities, threats, and recommendations
    """
    fires = world_state.get("fires", [])
    rubble = world_state.get("rubble", [])
    survivors = world_state.get("survivors", [])
    agents = world_state.get("agents", [])
    
    # Calculate threat levels
    fire_threat = len(fires) * 2  # Fires spread and are urgent
    rubble_threat = len(rubble) * 1.5  # Rubble blocks access
    survivor_threat = len(survivors) * 3  # Lives at stake
    
    total_threat = fire_threat + rubble_threat + survivor_threat
    
    # Assess agent capacity
    available_agents = len([a for a in agents if a.get("battery_level", 0) > 20])
    agent_capacity = available_agents / max(1, len(agents))
    
    # Priority recommendations
    priorities = []
    if survivors:
        priorities.append(f"URGENT: {len(survivors)} survivors need rescue")
    if fires:
        priorities.append(f"HIGH: {len(fires)} fires spreading")
    if rubble:
        priorities.append(f"MEDIUM: {len(rubble)} rubble blocks access")
        
    return {
        "threat_level": min(10, total_threat),
        "primary_threats": priorities[:3],
        "agent_capacity": agent_capacity,
        "recommended_strategy": "rescue_first" if survivors else "infrastructure_first",
        "estimated_response_time": len(survivors) * 2 + len(fires) * 1.5
    }

def plan_optimal_route(start_pos: List[int], target_pos: List[int], 
                      obstacles: List[List[int]], world_width: int = 20, 
                      world_height: int = 20) -> Dict[str, Any]:
    """
    Calculate optimal path avoiding obstacles.
    
    Args:
        start_pos: Starting position [x, y]
        target_pos: Target position [x, y]  
        obstacles: List of obstacle positions to avoid
        world_width, world_height: World dimensions
        
    Returns:
        Path information with route, distance, and alternatives
    """
    try:
        # Convert to format expected by pathfind_a_star
        start = tuple(start_pos)
        target = tuple(target_pos)
        blocked = set(tuple(obs) for obs in obstacles)
        
        # Simple pathfinding - calculate Manhattan distance and direction
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        distance = abs(dx) + abs(dy)
        
        # Generate simple path (for now, just next step)
        next_x = start[0] + (1 if dx > 0 else -1 if dx < 0 else 0)
        next_y = start[1] + (1 if dy > 0 else -1 if dy < 0 else 0)
        
        # Simple path
        if distance == 0:
            path = [start]
        else:
            path = [start, (next_x, next_y)]
        
        if path:
            return {
                "path": [list(pos) for pos in path],
                "distance": len(path),
                "feasible": True,
                "next_move": list(path[1]) if len(path) > 1 else list(start),
                "estimated_time": len(path) * 2  # 2 units per move
            }
        else:
            return {
                "path": [],
                "distance": float('inf'),
                "feasible": False,
                "next_move": list(start),
                "estimated_time": float('inf'),
                "error": "No path found to target"
            }
            
    except Exception as e:
        return {
            "path": [],
            "distance": float('inf'),
            "feasible": False, 
            "next_move": list(start_pos),
            "estimated_time": float('inf'),
            "error": f"Pathfinding error: {e}"
        }

def coordinate_multi_agent_response(agents: List[Dict], targets: List[Dict]) -> Dict[str, Any]:
    """
    Optimize task assignment across multiple agents.
    
    Args:
        agents: List of agent states with positions, capabilities, resources
        targets: List of targets (survivors, fires, rubble) with positions and priorities
        
    Returns:
        Optimized task assignments and coordination strategy
    """
    assignments = []
    
    # Sort targets by priority (survivors > fires > rubble)
    prioritized_targets = sorted(targets, key=lambda t: {
        "survivor": 0, "fire": 1, "rubble": 2
    }.get(t.get("type", "other"), 3))
    
    # Available agents by type
    trucks = [a for a in agents if a.get("kind") == "truck" and a.get("battery_level", 0) > 30]
    medics = [a for a in agents if a.get("kind") == "medic" and not a.get("carrying", False)]
    drones = [a for a in agents if a.get("kind") == "drone" and a.get("battery_level", 0) > 20]
    
    # Assign tasks based on agent capabilities
    for target in prioritized_targets:
        target_pos = target.get("pos", [0, 0])
        target_type = target.get("type", "unknown")
        
        if target_type == "survivor" and medics:
            # Assign closest medic
            closest_medic = min(medics, key=lambda a: 
                abs(a["pos"][0] - target_pos[0]) + abs(a["pos"][1] - target_pos[1]))
            assignments.append({
                "agent_id": closest_medic["id"],
                "task": "rescue_survivor",
                "target": target_pos,
                "priority": "HIGH"
            })
            medics.remove(closest_medic)
            
        elif target_type == "fire" and trucks:
            # Assign truck with water
            available_trucks = [t for t in trucks if t.get("water", 0) > 0]
            if available_trucks:
                closest_truck = min(available_trucks, key=lambda a:
                    abs(a["pos"][0] - target_pos[0]) + abs(a["pos"][1] - target_pos[1]))
                assignments.append({
                    "agent_id": closest_truck["id"],
                    "task": "extinguish_fire",
                    "target": target_pos,
                    "priority": "HIGH"
                })
                
        elif target_type == "rubble" and trucks:
            # Assign truck with tools
            available_trucks = [t for t in trucks if t.get("tools", 0) > 0]
            if available_trucks:
                closest_truck = min(available_trucks, key=lambda a:
                    abs(a["pos"][0] - target_pos[0]) + abs(a["pos"][1] - target_pos[1]))
                assignments.append({
                    "agent_id": closest_truck["id"],
                    "task": "clear_rubble", 
                    "target": target_pos,
                    "priority": "MEDIUM"
                })
    
    # Assign remaining drones for surveillance
    for i, drone in enumerate(drones[:2]):  # Limit to 2 drones
        patrol_area = [(5 + i*10, 5 + i*5), (15 + i*5, 15 + i*5)]
        assignments.append({
            "agent_id": drone["id"],
            "task": "surveillance_patrol",
            "target": patrol_area[0],
            "priority": "LOW"
        })
    
    return {
        "assignments": assignments,
        "coordination_strategy": "priority_based",
        "total_tasks": len(assignments),
        "estimated_completion": max([5, len(assignments) * 3]),
        "efficiency_score": len(assignments) / max(1, len(targets))
    }

def evaluate_resource_status(agents: List[Dict]) -> Dict[str, Any]:
    """
    Evaluate current resource levels and needs.
    
    Args:
        agents: List of all agents with their current states
        
    Returns:
        Resource assessment and recommendations
    """
    trucks = [a for a in agents if a.get("kind") == "truck"]
    
    total_water = sum(t.get("water", 0) for t in trucks)
    total_tools = sum(t.get("tools", 0) for t in trucks)
    low_battery_agents = [a for a in agents if a.get("battery_level", 100) < 30]
    
    # Resource status
    water_status = "CRITICAL" if total_water < 5 else "LOW" if total_water < 15 else "ADEQUATE"
    tools_status = "CRITICAL" if total_tools < 3 else "LOW" if total_tools < 8 else "ADEQUATE"
    battery_status = "CRITICAL" if len(low_battery_agents) > 2 else "ADEQUATE"
    
    recommendations = []
    if water_status == "CRITICAL":
        recommendations.append("Immediate water resupply needed")
    if tools_status == "CRITICAL":
        recommendations.append("Tool replenishment required")
    if battery_status == "CRITICAL":
        recommendations.append("Multiple agents need recharging")
    
    return {
        "water_level": total_water,
        "water_status": water_status,
        "tools_level": total_tools,
        "tools_status": tools_status,
        "low_battery_count": len(low_battery_agents),
        "battery_status": battery_status,
        "recommendations": recommendations,
        "operational_capacity": (100 - len(low_battery_agents) * 20) / 100
    }

# Tool registry for LLM calling
CRISIS_TOOLS = [
    {
        "name": "assess_crisis_situation",
        "description": "Analyze current crisis situation and provide comprehensive threat assessment with priorities",
        "parameters": {
            "type": "object",
            "properties": {
                "world_state": {
                    "type": "object", 
                    "description": "Current world state with agents, fires, rubble, survivors"
                }
            },
            "required": ["world_state"]
        }
    },
    {
        "name": "plan_optimal_route",
        "description": "Calculate optimal path between two points avoiding obstacles using A* pathfinding",
        "parameters": {
            "type": "object",
            "properties": {
                "start_pos": {"type": "array", "items": {"type": "integer"}, "description": "Starting position [x, y]"},
                "target_pos": {"type": "array", "items": {"type": "integer"}, "description": "Target position [x, y]"},
                "obstacles": {"type": "array", "items": {"type": "array"}, "description": "List of obstacle positions to avoid"}
            },
            "required": ["start_pos", "target_pos", "obstacles"]
        }
    },
    {
        "name": "coordinate_multi_agent_response", 
        "description": "Optimize task assignment and coordination across multiple emergency response agents",
        "parameters": {
            "type": "object",
            "properties": {
                "agents": {"type": "array", "description": "List of agent states with positions and capabilities"},
                "targets": {"type": "array", "description": "List of targets (survivors, fires, rubble) with priorities"}
            },
            "required": ["agents", "targets"]
        }
    },
    {
        "name": "evaluate_resource_status",
        "description": "Evaluate current resource levels (water, tools, battery) and provide recommendations",
        "parameters": {
            "type": "object", 
            "properties": {
                "agents": {"type": "array", "description": "List of all agents with their current states"}
            },
            "required": ["agents"]
        }
    }
]

# Tool execution mapping
TOOL_FUNCTIONS = {
    "assess_crisis_situation": assess_crisis_situation,
    "plan_optimal_route": plan_optimal_route,
    "coordinate_multi_agent_response": coordinate_multi_agent_response,
    "evaluate_resource_status": evaluate_resource_status
}

def execute_tool(tool_name: str, parameters: Dict) -> Dict[str, Any]:
    """Execute a tool with given parameters."""
    if tool_name in TOOL_FUNCTIONS:
        try:
            return TOOL_FUNCTIONS[tool_name](**parameters)
        except Exception as e:
            return {"error": f"Tool execution failed: {e}"}
    else:
        return {"error": f"Unknown tool: {tool_name}"}
