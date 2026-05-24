# agents.py - Enhanced Crisis Management Agents with Coordination

from mesa import Agent
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from tools.routing import shortest_path

# Import constants from world module
CELL_ROAD = "road"
CELL_FIRE = "fire"

class BaseAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.command = None
        # Enhanced Phase 1 attributes
        self.status = "idle"  # idle, moving, acting, waiting
        self.task_priority = 0  # Higher numbers = higher priority
        self.last_action_result = None
        self.coordination_requests = []  # List of requests from other agents
        self.memory = {}  # Agent memory for learning (Phase 1 baseline)
        self.reserved_positions = {}  # Track reserved positions for collision avoidance

    def set_command(self, cmd):
        self.command = cmd
        if cmd:
            self.status = "commanded"
            
    def set_reserved_positions(self, reserved_positions):
        """Set the reserved positions map for collision avoidance during execution"""
        self.reserved_positions = reserved_positions

    def step(self):
        # Enhanced step with status tracking
        if not self.command:
            self.status = "idle"
            return
            
        if self.command.get("type") == "move":
            self.status = "moving"
            self._do_move(self.command)
                
        elif self.command.get("type") == "act":
            self.status = "acting"
            self._do_act(self.command)

    def advance(self):
        # Enhanced advance with coordination processing
        self._process_coordination_requests()
        if self.status in ("moving", "acting"):
            self.status = "idle"

    def _do_act(self, cmd):
        self.last_action_result = "no_action"

    def _do_move(self, cmd):
        """Enhanced movement with proper wall/building detection and pathfinding."""
        target = cmd.get("target") or cmd.get("to")  # Support both command formats
        if not target:
            self.last_action_result = "no_target"
            return "failed"
        
        target_tuple = tuple(target)
        
        # Check if this agent has reserved the target position
        if target_tuple in self.reserved_positions:
            reserved_by = self.reserved_positions[target_tuple]
            if reserved_by != str(self.unique_id):
                # Another agent has reserved this position
                self.last_action_result = f"position_reserved_by_{reserved_by}"
                return "blocked"
        
        # Try to import routing (handle import error gracefully)
        try:
            from tools.routing import shortest_path
            # Use pathfinding to move towards target
            # Agents can move through roads, empty cells, depot, and hospital but not fire, rubble, or buildings
            path_result = shortest_path(self.model, self.pos, target, avoid=("fire", "rubble", "building"))
            
            if path_result["status"] == "ok" and len(path_result["path"]) > 1:
                # Move to next step in path
                next_pos = path_result["path"][1]
                next_pos_tuple = tuple(next_pos)
                
                # Priority check: Only move to next_pos if we have it reserved or it's not reserved
                if next_pos_tuple in self.reserved_positions:
                    reserved_by = self.reserved_positions[next_pos_tuple]
                    if reserved_by != str(self.unique_id):
                        # Next step is reserved by another agent, try alternative movement
                        self.last_action_result = f"next_step_reserved_by_{reserved_by}"
                        # Fall back to simple movement (try to find an alternative step)
                        return self._try_alternative_movement(target)
                
                # Check if next position is valid and not blocked by other agents
                cell_contents = self.model.grid.get_cell_list_contents([next_pos])
                
                # Allow movement if no blocking agents (survivors and environment cells are ok)
                blocking_agents = [a for a in cell_contents if isinstance(a, (MedicAgent, TruckAgent, DroneAgent))]
                
                if not blocking_agents:
                    self.model.grid.move_agent(self, next_pos)
                    self.last_action_result = "moved"
                    # Track energy usage for movement
                    self.model.increment_energy_used(1)
                    return "moved"
                else:
                    self.last_action_result = "path_blocked"
                    # Try alternative movement instead of giving up
                    return self._try_alternative_movement(target)
            else:
                self.last_action_result = "no_path"
                # Try alternative movement instead of giving up
                return self._try_alternative_movement(target)
                
        except ImportError:
            # Fallback to simple adjacent movement if routing not available
            x, y = self.pos
            tx, ty = target
            
            # Simple movement towards target
            dx = 1 if tx > x else (-1 if tx < x else 0)
            dy = 1 if ty > y else (-1 if ty < y else 0)
            
            new_pos = (x + dx, y + dy)
            
            # Check bounds
            if 0 <= new_pos[0] < self.model.width and 0 <= new_pos[1] < self.model.height:
                # Check if cell is passable (not building, fire, or rubble)
                cell_type = self.model.cell_types[new_pos[1]][new_pos[0]]
                if cell_type not in ("building", "fire", "rubble"):
                    self.model.grid.move_agent(self, new_pos)
                    self.last_action_result = "moved_simple"
                    # Track energy usage for movement
                    self.model.increment_energy_used(1)
                    return "moved"
                else:
                    self.last_action_result = f"blocked_by_{cell_type}"
                    return "blocked"
            else:
                self.last_action_result = "out_of_bounds"
                return "blocked"

    def _try_alternative_movement(self, target):
        """Try alternative movement when primary path is blocked by reservations."""
        x, y = self.pos
        tx, ty = target
        
        # Try all adjacent cells in order of preference toward target
        possible_moves = []
        
        # Calculate all 8 adjacent positions and their desirability
        adjacent_positions = [
            (x + 1, y),     # East
            (x - 1, y),     # West  
            (x, y + 1),     # South
            (x, y - 1),     # North
            (x + 1, y + 1), # Southeast
            (x + 1, y - 1), # Northeast
            (x - 1, y + 1), # Southwest
            (x - 1, y - 1)  # Northwest
        ]
        
        # Score each position by how much it reduces distance to target
        scored_moves = []
        current_distance = abs(tx - x) + abs(ty - y)
        
        for pos in adjacent_positions:
            new_x, new_y = pos
            new_distance = abs(tx - new_x) + abs(ty - new_y)
            distance_improvement = current_distance - new_distance
            scored_moves.append((distance_improvement, pos))
        
        # Sort by distance improvement (best first), then by position stability
        scored_moves.sort(key=lambda item: (-item[0], item[1]))
        possible_moves = [pos for score, pos in scored_moves]
        
        # Try each possible move in order of preference
        for new_pos in possible_moves:
            new_x, new_y = new_pos
            
            # Check bounds
            if not (0 <= new_x < self.model.width and 0 <= new_y < self.model.height):
                continue
                
            # Check if cell is passable
            cell_type = self.model.cell_types[new_y][new_x]
            if cell_type in ("building", "fire", "rubble"):
                continue
                
            # Check reservations
            new_pos_tuple = tuple(new_pos)
            if new_pos_tuple in self.reserved_positions:
                reserved_by = self.reserved_positions[new_pos_tuple]
                if reserved_by != str(self.unique_id):
                    continue  # This position is reserved by another agent
            
            # Check if position is blocked by other agents
            cell_contents = self.model.grid.get_cell_list_contents([new_pos])
            blocking_agents = [a for a in cell_contents if isinstance(a, (MedicAgent, TruckAgent, DroneAgent))]
            
            if not blocking_agents:
                # This position is free, move there
                self.model.grid.move_agent(self, new_pos)
                self.last_action_result = "moved_alternative"
                return "moved"
        
        # No alternative movement possible
        self.last_action_result = "all_paths_blocked"
        return "blocked"

    def _process_coordination_requests(self):
        """Process any coordination requests from other agents."""
        # Basic coordination processing (to be enhanced in Phase 2)
        if self.coordination_requests:
            self.model.agent_actions["coordination_events"] += len(self.coordination_requests)
            self.coordination_requests.clear()

    def request_coordination(self, other_agent, request_type, data=None):
        """Send coordination request to another agent."""
        if hasattr(other_agent, 'coordination_requests'):
            other_agent.coordination_requests.append({
                'from': self.unique_id,
                'type': request_type,
                'data': data or {}
            })


class Survivor(Agent):
    def __init__(self, unique_id, model, life_deadline=200):
        super().__init__(unique_id, model)
        self.life_deadline = life_deadline
        self._picked = False
        self._dead = False

    def step(self):
        if not self._picked:
            self.life_deadline -= 1
            if self.life_deadline <= 0:
                self._dead = True

    def advance(self):
        pass


class MedicAgent(BaseAgent):
    kind = "medic"
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.carrying = False
        self.carrying_id = None
        # Enhanced Phase 1 attributes
        self.rescue_count = 0
        self.failed_rescues = 0
        self.max_capacity = 1  # Can be enhanced later
        self.medical_supplies = 10  # Assignment requirement
        self.move_speed = 1.0  # Normal speed

    def _do_move(self, cmd):
        """Enhanced movement with slowdown when carrying patient and smart resupply behavior."""
        # Check if medic should return to hospital/depot for resupply
        if self.medical_supplies <= 1 and not self.carrying:
            # Find nearest hospital or depot for resupply
            hospitals = [pos for pos, _ in self.model.hospital_queues.items()]
            depot_pos = self.model.depot
            all_supply_points = hospitals + [depot_pos]
            
            if all_supply_points:
                # Find closest supply point
                current_pos = self.pos
                closest_supply = min(all_supply_points, 
                                   key=lambda p: abs(p[0] - current_pos[0]) + abs(p[1] - current_pos[1]))
                
                # Override command to go to supply point
                cmd = {"target": closest_supply, "type": "move"}
                print(f"🏥 Medic {self.unique_id} heading to resupply (supplies: {self.medical_supplies})")
        
        # Assignment requirement: medics move slower when carrying
        if self.carrying:
            # 20% chance to skip move when carrying (reduced slowdown effect)
            if self.model.random.random() < 0.2:
                self.last_action_result = "slowed_by_patient"
                return "slowed"
        
        return super()._do_move(cmd)

    def _do_act(self, cmd):
        action = cmd.get("action_name")
        
        # Get current position for all actions
        x, y = self.pos
        
        if action == "pickup_survivor":
            self.status = "attempting_pickup"
            cell_agents = self.model.grid.get_cell_list_contents([self.pos])
            surv = next((a for a in cell_agents if isinstance(a, Survivor) and not getattr(a, "_picked", False)), None)
            
            if surv and not self.carrying and self.medical_supplies > 0:
                self.carrying = True
                self.carrying_id = surv.unique_id
                surv._picked = True  # defer removal to model.step()
                self.rescue_count += 1
                self.medical_supplies -= 1  # Use medical supply
                self.model.agent_actions["medic_rescues"] += 1
                # Track energy usage for rescue action
                self.model.increment_energy_used(2)  # Rescue actions use more energy
                self.last_action_result = "pickup_success"
                self.status = "carrying_survivor"
            else:
                self.failed_rescues += 1
                if self.medical_supplies <= 0:
                    self.last_action_result = "no_medical_supplies"
                else:
                    self.last_action_result = "pickup_failed"
                self.status = "idle"

        elif action == "drop_at_hospital":
            self.status = "attempting_dropoff"
            x, y = self.pos
            if self.model.cell_type(x, y) == "hospital" and self.carrying:
                self.model.add_to_hospital_queue(self.pos, str(self.carrying_id))
                self.carrying = False
                self.carrying_id = None
                self.last_action_result = "dropoff_success"
                self.status = "idle"
            else:
                self.last_action_result = "dropoff_failed"
                self.status = "idle"
                
        elif action == "resupply":
            # Can resupply at hospital or depot
            if self.model.cell_type(x, y) in ["hospital", "depot"] or (x, y) == self.model.depot:
                self.medical_supplies = 10
                self.last_action_result = "resupplied"
                self.status = "resupplied"
                print(f"🏥 Medic {self.unique_id} resupplied at ({x}, {y})")
            else:
                self.last_action_result = "cannot_resupply_here"

        # Auto-resupply when at hospital/depot with low supplies
        elif ((self.model.cell_type(x, y) in ["hospital", "depot"] or (x, y) == self.model.depot) 
              and self.medical_supplies < 10):
            self.medical_supplies = 10
            print(f"🏥 Medic {self.unique_id} auto-resupplied at ({x}, {y})")
            self.last_action_result = "auto_resupplied"
            self.status = "resupplied"
        else:
            self.last_action_result = "unknown_action"
    
    def step(self):
        """Execute LLM-generated command only - no autonomous behavior."""
        # Execute any LLM-generated command
        super().step()

class TruckAgent(BaseAgent):
    kind = "truck"
    def __init__(self, unique_id, model, mode="water", water_max=30, tools_max=10):
        super().__init__(unique_id, model)
        self.mode = mode
        self.water_max = water_max
        self.tools_max = tools_max
        self.water = water_max
        self.tools = tools_max
        # Enhanced Phase 1 attributes
        self.fires_fought = 0
        self.rubble_cleared = 0
        self.efficiency = 1.0
        # Assignment requirements
        self.battery_level = 150  # Increased from 100 to 150 for more operational time
        self.battery_max = 150
        self.battery_recharges = 0

    def _do_move(self, cmd):
        """Enhanced movement with smart depot return based on WATER level only."""
        # Check if truck should return to depot automatically (only based on water, not battery)
        if self.water <= 2:  # Smart return threshold - only water matters for trucks
            depot_pos = self.model.depot
            current_pos = self.pos
            
            # If not at depot and need water, override command to go to depot
            if current_pos != depot_pos:
                cmd = {"target": depot_pos, "type": "move"}
                print(f"🚚 Truck {self.unique_id} auto-returning to depot (water: {self.water})")
        
        # Battery doesn't affect truck operation - only water does
        # Movement only consumes water for fire suppression, not battery for movement
        result = super()._do_move(cmd)
        
        # Trucks don't consume battery for movement - battery is just for display
        # Only water consumption matters for truck operations
        return result

    def _do_act(self, cmd):
        action = cmd.get("action_name")
        x, y = self.pos
        
        # For trucks, only water level matters operationally (battery is just for display)
        # Battery depletion doesn't stop truck operations, only low water does
        
        if action == "recharge":
            # FIXED: Must be exactly at depot to recharge (battery display only)
            if (x, y) == self.model.depot:
                self.battery_level = self.battery_max
                self.battery_recharges += 1
                self.last_action_result = "recharged"
                self.status = "recharged"
                print(f"🔋 Truck {self.unique_id} recharged at depot ({x}, {y})")
            else:
                self.last_action_result = "must_be_at_depot"
                self.status = "idle"
                print(f"❌ Truck {self.unique_id} cannot recharge at ({x}, {y}), must be at depot {self.model.depot}")

        # Auto-refill water when at depot (battery refill for display only)
        elif (x, y) == self.model.depot and (self.water < self.water_max):
            # Always refill battery for display purposes
            if self.battery_level < self.battery_max:
                self.battery_level = self.battery_max
                self.battery_recharges += 1
                print(f"🔋 Truck {self.unique_id} recharged battery for display")
            # Water refill is operationally important
            if self.water < self.water_max:
                self.water = self.water_max
                print(f"💧 Truck {self.unique_id} auto-refilled water at depot")
            self.last_action_result = "auto_resupplied"
            self.status = "resupplied"

        elif action == "extinguish" and self.water > 0:
            self.status = "fighting_fire"
            # Trucks only consume water, not battery (battery is display only)
            
            # Check current position and adjacent cells for fires
            fire_positions = []
            
            # Check current position
            if self.model.cell_type(x, y) in ("fire", "CELL_FIRE"):
                fire_positions.append((x, y))
            
            # Check adjacent positions for fires
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue  # Skip current position
                    fx, fy = x + dx, y + dy
                    if (0 <= fx < self.model.width and 0 <= fy < self.model.height and
                        self.model.cell_type(fx, fy) in ("fire", "CELL_FIRE")):
                        fire_positions.append((fx, fy))
            
            if fire_positions:
                # Extinguish the first fire found (prioritize closest)
                target_x, target_y = fire_positions[0]
                self.model.extinguish_fire_at(target_x, target_y)
                self.water -= 1
                self.fires_fought += 1
                self.model.agent_actions["truck_fires_fought"] += 1
                self.model.fires_extinguished += 1
                # Track energy usage for fire extinguishing
                self.model.increment_energy_used(3)  # Fire fighting uses significant energy
                self.last_action_result = f"fire_extinguished_at_{target_x}_{target_y}"
                print(f"🔥 Truck extinguished fire at ({target_x}, {target_y}) from ({x}, {y})")
            else:
                self.last_action_result = "no_fire_in_range"

        elif action == "clear_rubble" and self.tools > 0:
            self.status = "clearing_rubble"
            # Rubble clearing consumes 5 battery
            self.battery_level = max(0, self.battery_level - 5)
            
            # Check current position and adjacent cells for rubble
            rubble_positions = []
            
            # Check current position
            if self.model.cell_type(x, y) in ("rubble", "CELL_RUBBLE"):
                rubble_positions.append((x, y))
            
            # Check adjacent positions for rubble
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue  # Skip current position
                    rx, ry = x + dx, y + dy
                    if (0 <= rx < self.model.width and 0 <= ry < self.model.height and
                        self.model.cell_type(rx, ry) in ("rubble", "CELL_RUBBLE")):
                        rubble_positions.append((rx, ry))
            
            if rubble_positions:
                # Clear the first rubble found
                target_x, target_y = rubble_positions[0]
                self.model.clear_rubble_at(target_x, target_y)
                self.tools -= 1
                self.rubble_cleared += 1
                self.model.roads_cleared += 1
                # Track energy usage for rubble clearing
                self.model.increment_energy_used(4)  # Rubble clearing is energy intensive
                self.last_action_result = f"rubble_cleared_at_{target_x}_{target_y}"
                print(f"🧱 Truck cleared rubble at ({target_x}, {target_y}) from ({x}, {y})")
            else:
                self.last_action_result = "no_rubble_in_range"
                print(f"❌ No rubble in range of ({x}, {y})")
                
        elif action == "refill_water":
            # Can refill at depot or hospital
            if (x, y) == self.model.depot or self.model.cell_type(x, y) == "hospital":
                self.water = self.water_max
                self.last_action_result = "water_refilled"
                self.status = "refilled"
            else:
                self.last_action_result = "cannot_refill_here"
        else:
            self.last_action_result = "invalid_action"


class DroneAgent(BaseAgent):
    kind = "drone"
    def __init__(self, unique_id, model, battery_max=80):
        super().__init__(unique_id, model)
        self.battery_max = battery_max
        self.battery_level = battery_max
        # Enhanced Phase 1 attributes
        self.scan_count = 0
        self.coordination_events = 0
        self.efficiency = 1.0
        self.battery_recharges = 0  # Assignment requirement

    def _do_move(self, cmd):
        """Enhanced movement with battery consumption and smart patrol behavior."""
        # Check if drone should return to depot automatically for recharge
        if self.battery_level <= 20:  # Smart return threshold for drones
            depot_pos = self.model.depot
            current_pos = self.pos
            
            # If not at depot and need recharge, override command to go to depot
            if current_pos != depot_pos:
                cmd = {"target": depot_pos, "type": "move"}
                print(f"🚁 Drone {self.unique_id} auto-returning to depot (battery: {self.battery_level})")
        
        if self.battery_level <= 0:
            self.status = "battery_depleted"
            self.last_action_result = "no_battery"
            return
            
        # Normal movement consumes 1 battery
        result = super()._do_move(cmd)
        if result != "blocked":
            self.battery_level = max(0, self.battery_level - 1)
        return result

    def _do_act(self, cmd):
        action = cmd.get("action_name")
        
        if self.battery_level <= 0:
            self.status = "battery_depleted"
            self.last_action_result = "no_battery"
            return
            
        # Get current position for all actions
        x, y = self.pos
            
        if action == "recharge":
            # FIXED: Must be exactly at depot to recharge
            if (x, y) == self.model.depot:
                self.battery_level = self.battery_max
                self.battery_recharges += 1
                self.last_action_result = "recharged"
                self.status = "recharged"
                print(f"🔋 Drone {self.unique_id} recharged at depot ({x}, {y})")
            else:
                self.last_action_result = "must_be_at_depot"
                self.status = "idle"
                print(f"❌ Drone {self.unique_id} cannot recharge at ({x}, {y}), must be at depot {self.model.depot}")

        # Auto-recharge when at depot with low battery
        elif (x, y) == self.model.depot and self.battery_level < self.battery_max:
            self.battery_level = self.battery_max
            self.battery_recharges += 1
            print(f"🔋 Drone {self.unique_id} auto-recharged at depot")
            self.last_action_result = "auto_recharged"
            self.status = "recharged"
                
        elif self.battery_level <= 5:  # Low battery warning
            self.status = "low_battery_warning"
            self.last_action_result = "need_recharge_soon"
                
        elif action == "scan":
            self.status = "scanning"
            # Scanning consumes 2 battery and reveals nearby area
            self.battery_level = max(0, self.battery_level - 2)
            self.scan_count += 1
            self.model.agent_actions["drone_recon"] += 1
            # Track energy usage for scanning
            self.model.increment_energy_used(2)  # Scanning uses moderate energy
            
            # ENHANCED: Drone scanning reveals survivors and fires in 3x3 area
            x, y = self.pos
            scan_results = {"survivors": 0, "fires": 0, "clear": 0}
            
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    scan_x, scan_y = x + dx, y + dy
                    if 0 <= scan_x < self.model.width and 0 <= scan_y < self.model.height:
                        # Check cell type directly
                        if self.model.cell_type(scan_x, scan_y) == CELL_FIRE:
                            scan_results["fires"] += 1
                        elif self.model.cell_type(scan_x, scan_y) == CELL_ROAD:
                            scan_results["clear"] += 1
                        
                        # Check for survivors
                        cell_contents = self.model.grid.get_cell_list_contents([(scan_x, scan_y)])
                        for agent in cell_contents:
                            if isinstance(agent, Survivor):
                                scan_results["survivors"] += 1
            
            self.last_scan_results = scan_results
            self.last_action_result = f"scan_complete: {scan_results['survivors']}S {scan_results['fires']}F {scan_results['clear']}C"
            
        elif action == "coordinate":
            self.status = "coordinating"
            # Coordination consumes 1 battery
            self.battery_level = max(0, self.battery_level - 1)
            self.coordination_events += 1
            self.model.agent_actions["coordination_events"] += 1
            self.last_action_result = "coordination_sent"
        else:
            self.last_action_result = "unknown_action"
