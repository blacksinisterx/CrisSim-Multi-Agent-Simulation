# reasoning/react.py
import json
import os
import logging

# Set up logging for ReAct strategy
logging.basicConfig(level=logging.INFO)
react_logger = logging.getLogger('ReAct')

def _transform_llm_command(llm_cmd: dict) -> dict:
    """
    Transform LLM command format to system expected format.
    
    LLM format: {"agent": "truck_0", "action": "clear_rubble", "target": [x, y]}
    System format: {"agent_id": "truck_0", "type": "act", "action_name": "clear_rubble"}
                   {"agent_id": "truck_0", "type": "move", "to": [x, y]}
    """
    try:
        # Pass-through: if it already matches system schema, normalize keys and return
        if llm_cmd.get("agent_id") and llm_cmd.get("type") in ("move", "act"):
            if llm_cmd["type"] == "move":
                # Normalize to always have 'to'
                to = llm_cmd.get("to") or llm_cmd.get("target")
                return {"agent_id": str(llm_cmd.get("agent_id")), "type": "move", "to": to}
            elif llm_cmd["type"] == "act":
                return {
                    "agent_id": str(llm_cmd.get("agent_id")),
                    "type": "act",
                    "action_name": llm_cmd.get("action_name") or llm_cmd.get("action"),
                    # Preserve target for acts so we can move toward it if needed
                    "to": llm_cmd.get("to") or llm_cmd.get("target")
                }

        # General normalization from LLM-oriented schema
        agent_id = llm_cmd.get("agent") or llm_cmd.get("agent_id")
        action = (llm_cmd.get("action") or llm_cmd.get("action_name") or "").lower()
        target = llm_cmd.get("target") if llm_cmd.get("target") is not None else llm_cmd.get("to")

        if not agent_id:
            return None

        agent_id = str(agent_id)

        # Movement actions
        if action == "move":
            return {"agent_id": agent_id, "type": "move", "to": target}

        # Action mappings (include common synonyms)
        action_mapping = {
            "clear_rubble": "clear_rubble",
            "extinguish_fire": "extinguish",
            "extinguish": "extinguish",
            "rescue_survivor": "pickup_survivor",
            "pickup": "pickup_survivor",
            "pickup_survivor": "pickup_survivor",
            "drop_at_hospital": "drop_at_hospital",
            "drop": "drop_at_hospital",
            "scout_area": "scan",
            "scan_area": "scan",
            "scan": "scan",
            "charge_battery": "recharge",
            "recharge": "recharge",
            "coordinate": "coordinate",
            "transport_supplies": "move"  # Treat as movement for now
        }

        mapped_action = action_mapping.get(action)
        if mapped_action:
            if mapped_action == "move":
                return {"agent_id": agent_id, "type": "move", "to": target}
            # Keep target alongside act for later feasibility checks
            out = {"agent_id": agent_id, "type": "act", "action_name": mapped_action}
            if target is not None:
                out["to"] = target
            return out

        # Default fallback: treat unknown action as act with provided name
        out = {"agent_id": agent_id, "type": "act", "action_name": action}
        if target is not None:
            out["to"] = target
        return out

    except Exception as e:
        react_logger.warning(f"Failed to transform command {llm_cmd}: {e}")
        return None

def react_plan(context, scratchpad: str = ""):
    """
    Entry point used by planner.make_plan(...):
    """
    # Check if LLM mode is enabled
    use_llm = os.getenv("LLM_PROVIDER", "ollama").lower() in ["gemini", "groq", "ollama"]
    
    if use_llm:
        try:
            provider = os.getenv("LLM_PROVIDER", "ollama").lower()
            # react_logger.info(f"Using LLM-powered ReAct strategy with {provider.upper()} provider")  # Reduced logging
            plan_dict = react_with_llm_integration(context)
        except Exception as e:
            react_logger.error(f"LLM integration failed: {e} - NO FALLBACK")
            plan_dict = {"commands": [], "strategy": "REACT_LLM_FAILED_NO_FALLBACK", "error": str(e)}
    else:
        # NO MOCK STRATEGY - return empty if no LLM
        react_logger.error("No LLM provider available - NO MOCK FALLBACK")
        plan_dict = {"commands": [], "strategy": "REACT_NO_LLM_NO_FALLBACK", "error": "No LLM provider"}
    
    return ("final", json.dumps(plan_dict))

def _distance(a, b):
    try:
        return abs(a[0]-b[0]) + abs(a[1]-b[1])
    except Exception:
        return 999999

def react_with_llm_integration(context: dict) -> dict:
    """
    ReAct strategy implementation with Gemini 2.5 Flash and tool calling.
    Implements Thought-Action-Observation cycles for crisis management.
    """
    try:
        from .llm_client import llm_complete_react

        # Format crisis situation for LLM
        agents = context.get("agents", [])
        fires = context.get("fires", [])
        rubble = context.get("rubble", [])
        survivors = context.get("survivors", [])
        depots = context.get("depots", [(0, 0)])
        hospitals = context.get("hospitals", [(5, 0)])

        # Create comprehensive crisis context for ReAct with detailed locations
        crisis_context = {
            "current_situation": {
                "fires_at": fires,  # Exact fire coordinates
                "rubble_at": rubble,  # Exact rubble coordinates  
                "survivors_at": survivors,  # Exact survivor coordinates
                "depots": depots,
                "hospitals": hospitals
            },
            "available_agents": []
        }
        # Propagate current tick for prompt freshness
        crisis_context["tick"] = context.get("tick", 0)

        for agent in agents:
            agent_info = {
                "id": agent.get('id'),
                "kind": agent.get('kind', 'unknown'),
                "position": agent.get('pos'),
                "status": agent.get('status', 'idle'),
                "carrying": agent.get('carrying', False),  # Include carrying status
                "last_action_result": agent.get('last_action_result', 'unknown'),  # CRITICAL: Include action feedback
                "previous_position": agent.get('previous_pos', agent.get('pos'))  # Track movement
            }

            if agent.get('kind') == 'truck':
                agent_info.update({
                    "battery": agent.get('battery_level', 0),
                    "water": agent.get('water', 0),
                    "tools": agent.get('tools', 0)
                })
            elif agent.get('kind') == 'medic':
                agent_info.update({
                    "battery": agent.get('battery_level', 0),
                    "medical_supplies": agent.get('supplies', 0)
                })
            elif agent.get('kind') == 'drone':
                agent_info.update({
                    "battery": agent.get('battery_level', 0),
                    "camera_active": agent.get('camera', False)
                })

            crisis_context["available_agents"].append(agent_info)

        # Generate ReAct plan using LLM
        provider = os.getenv("LLM_PROVIDER", "gemini").upper()
        # react_logger.info(f"Generating ReAct plan with {provider}")  # Reduced logging
        response = llm_complete_react(crisis_context)

        if response and "commands" in response:
            # Transform LLM command format to system expected format
            transformed_commands = []
            for cmd in response["commands"]:
                transformed_cmd = _transform_llm_command(cmd)
                if transformed_cmd:
                    transformed_commands.append(transformed_cmd)

            # Context-aware refinement: PRESERVE strategic actions, only convert to moves when absolutely necessary
            agent_pos = {str(a.get('id')): tuple(a.get('pos', a.get('position', (0, 0)))) for a in context.get('agents', [])}
            fire_positions = {tuple(p) for p in context.get('fires', [])}
            rubble_positions = {tuple(p) for p in context.get('rubble', [])}
            hospital_positions = {tuple(h.get('pos') if isinstance(h, dict) else h) for h in context.get('hospitals', [])}
            survivor_positions = {tuple(s.get('pos') if isinstance(s, dict) else s) for s in context.get('survivors', [])}

            refined = []
            for c in transformed_commands:
                if not isinstance(c, dict):
                    continue
                if c.get('type') == 'act':
                    aid = c.get('agent_id')
                    pos = agent_pos.get(str(aid))
                    tgt = tuple(c.get('to')) if c.get('to') else None
                    an = c.get('action_name')
                    
                    # PRESERVE strategic actions - only convert to moves in very specific cases
                    # Truck: if clear_rubble requested but no target specified, find nearest rubble/fire
                    if an == 'clear_rubble' and tgt is None:
                        # pick closest rubble else fire
                        target = None
                        if rubble_positions:
                            target = min(rubble_positions, key=lambda p: _distance(pos, p)) if pos else None
                        if target is None and fire_positions:
                            target = min(fire_positions, key=lambda p: _distance(pos, p)) if pos else None
                        if target is not None:
                            # Update the action target instead of converting to move
                            c_updated = c.copy()
                            c_updated['to'] = list(target)
                            refined.append(c_updated)
                            continue
                    # Medic: if drop_at_hospital but no target specified, find nearest hospital
                    if an == 'drop_at_hospital' and tgt is None and pos is not None and hospital_positions:
                        target = min(hospital_positions, key=lambda p: _distance(pos, p))
                        # Update the action target instead of converting to move
                        c_updated = c.copy()
                        c_updated['to'] = list(target)
                        refined.append(c_updated)
                        continue
                    
                    # Drone: avoid depot ping-pong when charged - convert scan to patrol move only in this specific case
                    if an == 'scan':
                        depot = tuple(context.get('depot', [1, 1]))
                        battery = None
                        # find battery for this agent
                        for a in context.get('agents', []):
                            if str(a.get('id')) == str(aid):
                                battery = a.get('battery_level')
                                break
                        if pos == depot and (battery is None or battery >= 80):
                            patrol = [(depot[0] + 2, depot[1]), (depot[0], depot[1] + 2)]
                            refined.append({"agent_id": aid, "type": "move", "to": list(patrol[0])})
                            continue
                
                # PRESERVE all other strategic actions as-is
                refined.append(c)
            transformed_commands = refined

            # NO MOCK FILLING - let the commands be incomplete if LLM fails
            # Only return the commands that the LLM actually provided
            transformed_commands = refined

            # react_logger.info(f"ReAct strategy generated {len(transformed_commands)} commands (no fallback filling)")
            return {"commands": transformed_commands}
        else:
            react_logger.error("Invalid LLM response - returning NO COMMANDS (no fallback)")
            return {"commands": []}

    except Exception as e:
        react_logger.error(f"ReAct LLM integration failed: {e} - NO FALLBACK")
        return {"commands": [], "strategy": "REACT_INTEGRATION_FAILED_NO_FALLBACK", "error": str(e)}

# DEAD CODE - Mock functions no longer used (all fallbacks removed)
"""
def mock_react_with_tools(context: dict) -> dict:
    # DEPRECATED: Rule-based fallback - no longer used
    return {"commands": []}
"""

# -------------------- Helpers --------------------

def _manhattan(a, b) -> int:
    """Calculate Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# DEAD CODE SECTION - Function was removed but docstring got misplaced
# This was the docstring for the removed mock_react_with_tools function:
"""
Enhanced ReAct-style planner with collision avoidance and better coordination.

- Medics:
    * Priority 1: If carrying and on a hospital tile -> drop_at_hospital
    * Priority 2: If carrying and not on hospital -> move toward nearest hospital
    * Priority 3: If not carrying and co-located with a survivor -> pickup_survivor
    * Priority 4: If not carrying -> move toward nearest survivor
- Truck:
    * Priority 1: If battery <= 20 -> return to depot to recharge
    * Priority 2: If on rubble -> clear_rubble (Assignment requirement!)
    * Priority 3: If on fire -> extinguish
    * Priority 4: Move toward nearest rubble or fire (prioritize rubble)
- Drone:
    * Priority 1: If battery <= 10 -> return to depot to recharge
    * Priority 2: If fully charged and at depot, MOVE AWAY to make room for trucks
    * Priority 3: Scan area for survivors and coordination
"""
# END DEAD CODE SECTION


def _enhanced_mock_react_planner(context: dict) -> dict:
    commands = []
    occupied_positions = set()  # Track where agents are being commanded to move

    agents = context.get("agents", [])
    fires = [tuple(p) for p in context.get("fires", [])]
    # Support survivors as dicts with pos or raw (x,y)
    survivors_raw = context.get("survivors", [])
    survivors = []
    for s in survivors_raw:
        if isinstance(s, dict):
            pos = s.get("pos") or s.get("position")
            if pos is not None:
                survivors.append(tuple(pos))
        elif isinstance(s, (list, tuple)) and len(s) == 2:
            survivors.append(tuple(s))
    # Support hospitals as dicts with pos or raw (x,y)
    hospitals_raw = context.get("hospitals", [])
    hospital_positions = []
    for h in hospitals_raw:
        if isinstance(h, dict):
            pos = h.get("pos") or h.get("position")
            if pos is not None:
                hospital_positions.append(tuple(pos))
        elif isinstance(h, (list, tuple)) and len(h) == 2:
            hospital_positions.append(tuple(h))
    rubble_positions = [tuple(r) for r in context.get("rubble", [])]  # Add rubble
    depot_pos = tuple(context.get("depot", [1, 1]))  # Get depot position
    
    hospital_set = set(hospital_positions)
    survivor_set = set(survivors)
    fire_set = set(fires)
    rubble_set = set(rubble_positions)
    
    # Track current agent positions
    current_positions = {tuple(a.get("pos", (0, 0))) for a in agents}

    for a in agents:
        aid = a["id"]
        kind = a.get("kind")
        pos = tuple(a.get("pos", (0, 0)))
        battery = a.get("battery_level", 100)

        if kind == "truck":
            # Priority 1: Low battery -> recharge at depot (30/150 = 20% threshold)
            if battery <= 30:
                if pos == depot_pos:
                    commands.append({"agent_id": aid, "type": "act", "action_name": "recharge"})
                    continue
                else:
                    # Move toward depot
                    nxt = _greedy_step(pos, depot_pos)
                    if nxt not in occupied_positions and nxt not in current_positions:
                        occupied_positions.add(nxt)
                        commands.append({"agent_id": aid, "type": "move", "to": list(nxt)})
                    continue
            
            # Priority 2: Check if adjacent to rubble -> clear it
            adjacent_positions = [
                (pos[0] + dx, pos[1] + dy) 
                for dx in [-1, 0, 1] for dy in [-1, 0, 1] 
                if not (dx == 0 and dy == 0)  # Exclude current position
            ]
            
            # Look for adjacent rubble to clear
            adjacent_rubble = [p for p in adjacent_positions if p in rubble_set]
            if adjacent_rubble and a.get("tools", 0) > 0:
                commands.append({"agent_id": aid, "type": "act", "action_name": "clear_rubble"})
                continue
                
            # Priority 3: Check if adjacent to fire -> extinguish
            adjacent_fires = [p for p in adjacent_positions if p in fire_set]
            if adjacent_fires and a.get("water", 0) > 0:
                commands.append({"agent_id": aid, "type": "act", "action_name": "extinguish"})
                continue
                
            # Priority 4: Move toward nearest rubble or fire (prioritize rubble)
            rubble_target = _nearest_from(pos, rubble_positions)
            fire_target = _nearest_from(pos, fires)
            
            target = None
            # Always prioritize rubble clearing for assignment requirements
            if rubble_target:
                target = rubble_target
            elif fire_target:
                target = fire_target
                
            if target:
                nxt = _greedy_step(pos, target)
                if nxt != pos and nxt not in occupied_positions and nxt not in current_positions:
                    occupied_positions.add(nxt)
                    commands.append({"agent_id": aid, "type": "move", "to": list(nxt)})

        elif kind == "medic":
            carrying = bool(a.get("carrying", False))
            if carrying:
                # If on hospital -> drop
                if pos in hospital_set:
                    commands.append({"agent_id": aid, "type": "act", "action_name": "drop_at_hospital"})
                else:
                    hpos = _nearest_from(pos, hospital_positions)
                    if hpos:
                        nxt = _greedy_step(pos, hpos)
                        if nxt not in occupied_positions and nxt not in current_positions:
                            occupied_positions.add(nxt)
                            commands.append({"agent_id": aid, "type": "move", "to": list(nxt)})
            else:
                # If co-located with survivor -> pickup
                if pos in survivor_set:
                    commands.append({"agent_id": aid, "type": "act", "action_name": "pickup_survivor"})
                else:
                    s_pos = _nearest_from(pos, survivors)
                    if s_pos:
                        nxt = _greedy_step(pos, s_pos)
                        if nxt not in occupied_positions and nxt not in current_positions:
                            occupied_positions.add(nxt)
                            commands.append({"agent_id": aid, "type": "move", "to": list(nxt)})

        elif kind == "drone":
            # Priority 1: Low battery -> recharge at depot
            if battery <= 10:
                if pos == depot_pos:
                    commands.append({"agent_id": aid, "type": "act", "action_name": "recharge"})
                    continue
                else:
                    # Move toward depot
                    nxt = _greedy_step(pos, depot_pos)
                    if nxt not in occupied_positions and nxt not in current_positions:
                        occupied_positions.add(nxt)
                        commands.append({"agent_id": aid, "type": "move", "to": list(nxt)})
                    continue
            
            # Priority 2: If fully charged and at depot, MOVE AWAY to make room for trucks
            if battery >= 80 and pos == depot_pos:
                # Move to nearby patrol position to avoid blocking depot
                patrol_candidates = [
                    (depot_pos[0] + 2, depot_pos[1]), 
                    (depot_pos[0], depot_pos[1] + 2),
                    (depot_pos[0] - 1, depot_pos[1] + 2),
                    (depot_pos[0] + 1, depot_pos[1] - 1)
                ]
                for patrol_pos in patrol_candidates:
                    if patrol_pos not in occupied_positions and patrol_pos not in current_positions:
                        occupied_positions.add(patrol_pos)
                        commands.append({"agent_id": aid, "type": "move", "to": list(patrol_pos)})
                        break
                else:
                    # If all patrol positions are occupied, just scan
                    commands.append({"agent_id": aid, "type": "act", "action_name": "scan"})
                continue
            
            # Priority 3: Scan area for survivors and coordination
            commands.append({"agent_id": aid, "type": "act", "action_name": "scan"})

    return {"commands": commands}


# -------------------- Helpers --------------------

def _manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def _nearest_from(pos, points):
    if not points:
        return None
    return min(points, key=lambda p: _manhattan(pos, p))

def _greedy_step(src, dst):
    """Take one Manhattan step from src -> dst (prefers x, then y)."""
    sx, sy = src
    dx, dy = dst
    if sx < dx: 
        return (sx + 1, sy)
    if sx > dx: 
        return (sx - 1, sy)
    if sy < dy: 
        return (sx, sy + 1)
    if sy > dy: 
        return (sx, sy - 1)
    return src
