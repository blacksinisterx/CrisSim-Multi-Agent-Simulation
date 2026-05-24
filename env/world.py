# world.py - Enhanced Crisis Management Mesa Model

from mesa import Model, Agent
from mesa.space import MultiGrid
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector
import random
import logging
from collections import deque
from .agents import DroneAgent, MedicAgent, TruckAgent, Survivor
from .dynamics import spread_fires, trigger_aftershocks

logger = logging.getLogger(__name__)

CELL_ROAD = "road"
CELL_BUILDING = "building"
CELL_RUBBLE = "rubble"
CELL_FIRE = "fire"
CELL_HOSPITAL = "hospital"
CELL_DEPOT = "depot"
CELL_EMPTY = "empty"

class EnvironmentCell(Agent):
    """Agent representing environment cells (fires, buildings, etc.) for visualization."""
    def __init__(self, unique_id, model, cell_type):
        super().__init__(unique_id, model)
        self.cell_type = cell_type
    
    def step(self):
        # Environment cells don't move, just exist for visualization
        pass

class CrisisModel(Model):
    """
    Mesa model containing the world grid, agents, and per-tick dynamics.
    Reasoning/planning is orchestrated by main.py; this model exposes helpers
    to summarize state and to apply per-tick plans.
    """
    def __init__(self, width, height, rng_seed=42, config=None, render=False, 
                 map_selection="small", strategy_selection="react", provider_selection="ollama"):
        super().__init__()
        self.random = random.Random(rng_seed)
        self.width = width
        self.height = height
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = SimultaneousActivation(self)
        self.render = render
        self.running = True
        self.total_survivors = None  # will compute first step
        
        # Store GUI selections for potential use in model logic
        self.map_selection = map_selection
        self.strategy_selection = strategy_selection
        self.provider_selection = provider_selection
    
        # Params - ULTRA-CONSERVATIVE fire spread
        self.p_fire_spread = 0.025  # Slightly increased from 0.01 to 0.025 for more realistic fire spread
        self.p_aftershock = 0.02
        self.hospital_service_rate = 2  # patients per tick per hospital
        self.hospital_queues = {}  # {(x,y): [survivor_ids...]}
        # Timing / rescue-time tracking
        self.time = 0                      # simulation ticks since start
        self._rescue_times = []            # list of tick-times when survivors get admitted
        self.avg_rescue_time = 0.0         # rolling average (in ticks)

        # Assignment-Required Metrics (consolidated)
        self.rescued = 0
        self.deaths = 0
        self.fires_extinguished = 0
        self.roads_cleared = 0
        self.energy_used = 0
        self.tool_calls = 0
        self.invalid_json = 0
        self.replans = 0
        self.hospital_overflow_events = 0
        
        # Additional metrics for enhanced analysis
        self.battery_recharges = 0
        self.rubble_cleared_total = 0
        self.active_fires = 0
        self.total_decisions = 0
        self.optimal_decisions = 0
        self.crisis_score = 0.0
        self.current_strategy = "Mock"  # Will be set by reasoning system
        
        # Agent performance tracking
        self.agent_actions = {
            "medic_rescues": 0,
            "truck_fires_fought": 0,
            "drone_recon": 0,
            "coordination_events": 0
        }

        # Map initialization
        self.cell_types = [[CELL_EMPTY for _ in range(width)] for _ in range(height)]
        config = config or {}  # Ensure config is never None
        self._init_from_config(config)

        # Agents
        self._spawn_initial_agents()
        self._place_survivors(config.get("survivors", 10))
        # Cache how many survivors were spawned at start (fallback to None if types differ)
        try:
            self.total_survivors = sum(1 for a in self.schedule.agents if isinstance(a, Survivor))
        except Exception:
            self.total_survivors = None  # we'll infer on the first step if needed

        # Enhanced DataCollector with new metrics
        self.datacollector = DataCollector(model_reporters={
            "rescued": "rescued",
            "deaths": "deaths",
            "fires_extinguished": "fires_extinguished",
            "roads_cleared": "roads_cleared",
            "energy_used": "energy_used",
            "tool_calls": "tool_calls",
            "invalid_json": "invalid_json",
            "replans": "replans",
            "hospital_overflow_events": "hospital_overflow_events",
            # New Phase 1 metrics
            "active_fires": "active_fires",
            "total_decisions": "total_decisions",
            "optimal_decisions": "optimal_decisions",
            "crisis_score": "crisis_score",
            "medic_rescues": lambda m: m.agent_actions["medic_rescues"],
            "truck_fires_fought": lambda m: m.agent_actions["truck_fires_fought"],
            "drone_recon": lambda m: m.agent_actions["drone_recon"],
            "coordination_events": lambda m: m.agent_actions["coordination_events"],
            # Assignment requirement metrics
            "battery_recharges": "battery_recharges",
            "rubble_cleared": "rubble_cleared_total",  # Map to chart field name
            "rubble_cleared_total": "rubble_cleared_total",
        })

        # Plan from planner applied each tick
        self.pending_commands = []  # list of {"agent_id": str, "type": "move|act", ...}

    def _init_from_config(self, cfg):
        W, H = self.width, self.height
        # Default: everything road except explicit types
        for y in range(H):
            for x in range(W):
                self.cell_types[y][x] = CELL_ROAD

        def set_cell(x, y, val):
            if 0 <= x < W and 0 <= y < H:
                self.cell_types[y][x] = val
                
                # FIXED: Create environment cell agents for visualization
                if val in [CELL_FIRE, CELL_BUILDING, CELL_HOSPITAL, CELL_DEPOT, CELL_RUBBLE]:
                    env_cell = EnvironmentCell(self.next_id(), self, val)
                    self.schedule.add(env_cell)
                    self.grid.place_agent(env_cell, (x, y))

        depot = cfg.get("depot", [1,1])
        set_cell(depot[0], depot[1], CELL_DEPOT)
        self.depot = tuple(depot)

        for h in cfg.get("hospitals", []):
            set_cell(h[0], h[1], CELL_HOSPITAL)
            self.hospital_queues[tuple(h)] = []

        for r in cfg.get("rubble", []):
            set_cell(r[0], r[1], CELL_RUBBLE)

        for f in cfg.get("initial_fires", []):
            set_cell(f[0], f[1], CELL_FIRE)

        for b in cfg.get("buildings", []):
            if isinstance(b, list) and len(b) == 2 and all(isinstance(v, int) for v in b):
                set_cell(b[0], b[1], CELL_BUILDING)

    def _spawn_initial_agents(self):
        # 1 drone, 2 medics, 1 truck to start (tweak as desired)
        d = DroneAgent(self.next_id(), self, battery_max=80)
        m1 = MedicAgent(self.next_id(), self)
        m2 = MedicAgent(self.next_id(), self)
        t = TruckAgent(self.next_id(), self, mode="water", water_max=30, tools_max=10)

        for a in (d, m1, m2, t):
            self.schedule.add(a)
            self.grid.place_agent(a, self.depot)

    def _place_survivors(self, n):
        """FIXED: Better survivor placement avoiding impassable terrain."""
        placed = 0
        attempts = 0
        while placed < n and attempts < n*50:
            x = self.random.randrange(self.width)
            y = self.random.randrange(self.height)
            ct = self.cell_types[y][x]
            
            # Only place on passable terrain, avoid fires and special locations
            if ct in (CELL_ROAD, CELL_BUILDING):
                # Check if cell is already occupied by environment agents
                cell_contents = self.grid.get_cell_list_contents([(x, y)])
                has_environment_cell = any(isinstance(agent, EnvironmentCell) for agent in cell_contents)
                
                if not has_environment_cell:  # Don't place on fires, rubble, etc.
                    s = Survivor(self.next_id(), self, life_deadline=self.random.randint(120, 260))
                    self.schedule.add(s)
                    self.grid.place_agent(s, (x, y))
                    placed += 1
            attempts += 1

    # ----------------- Per-tick orchestration -----------------
    def set_plan(self, commands):
        """Accept list of per-agent command dicts generated by planner."""
        self.pending_commands = commands or []
    def step(self):
        """Apply pending plan, update dynamics, and collect metrics."""
        # --- Apply planner commands to agents for this tick ---

        # --- AUTO-PLAN in GUI mode ---
        if getattr(self, "render", False):
            try:
                # Use the selected strategy and provider instead of hardcoded mock
                from reasoning.planner import make_plan
                import os
                
                # Export context for planning
                ctx = self.summarize_state()
                
                # Use the selected strategy and provider from GUI
                strategy = getattr(self, 'strategy_selection', 'react')
                provider = getattr(self, 'provider_selection', 'ollama')  # Default to ollama for local inference
                
                # Set environment variables for the LLM client
                os.environ["LLM_PROVIDER"] = provider
                os.environ["STRATEGY"] = strategy
                
                # Track this as a tool call (LLM planning request)
                self.increment_tool_calls()
                
                # print(f"🧠 Using {strategy.upper()} strategy with {provider.upper()} provider")  # Reduced logging
                
                # NO MORE MOCK FALLBACKS - use LLM providers directly or fail
                # Generate plan using selected parameters
                plan = make_plan(
                    context=ctx,
                    strategy=strategy
                )
                
                # Check if plan contains error indicators
                if isinstance(plan, dict):
                    if plan.get("error") or not plan.get("commands"):
                        if "invalid" in str(plan.get("error", "")).lower() or "json" in str(plan.get("error", "")).lower():
                            self.increment_invalid_json()
                        if "replan" in str(plan.get("error", "")).lower() or "retry" in str(plan.get("error", "")).lower():
                            self.increment_replans()
                
                self.pending_commands = plan.get("commands", [])
                self.current_strategy = strategy.upper()
                
            except Exception as e:
                print(f"❌ Planning error: {e}")
                # Track planning failure
                self.increment_invalid_json()  # Planning errors often relate to JSON parsing
                # Fallback to empty commands if planning fails
                self.pending_commands = []
        # --- end auto-plan block ---

        # --- VALIDATION & NORMALIZATION LAYER ---
        self.pending_commands = self._validate_and_complete_plan(self.pending_commands)
        
        # Store validated commands for testing/debugging
        self._last_validated_commands = self.pending_commands.copy()

        # existing code that maps self.pending_commands to each agent, then:
        # self.schedule.step()
        # spread_fires / trigger_aftershocks / hospital queues / removals / datacollector

        self.time += 1
        cmd_map = {}
        reserved_positions = {}  # Track which positions are reserved by move commands
        
        print(f"🎯 Processing {len(self.pending_commands)} commands this step")
        for i, cmd in enumerate(self.pending_commands):
            print(f"   Command {i+1}: {cmd}")
        
        for cmd in self.pending_commands:
            aid = cmd.get("agent_id")
            if aid is not None:
                cmd_map[aid] = cmd
                
                # Reserve target positions for move commands to prevent conflicts
                if cmd.get("type") == "move" and cmd.get("to"):
                    target_pos = tuple(cmd["to"])
                    if target_pos in reserved_positions:
                        # Conflict detected - prioritize first command (could add priority logic here)
                        print(f"⚠️  Position {target_pos} conflict between agents {reserved_positions[target_pos]} and {aid}")
                    else:
                        reserved_positions[target_pos] = aid
        
        for agent in self.schedule.agents:
            if hasattr(agent, "set_command"):
                acmd = cmd_map.get(str(agent.unique_id))
                agent.set_command(acmd)
                # Debug logging for command assignment
                if acmd:
                    print(f"🎯 Agent {agent.unique_id} assigned command: {acmd}")
                else:
                    print(f"⚠️ Agent {agent.unique_id} received NO command")
                # Pass reserved positions to agent for collision checking
                if hasattr(agent, 'set_reserved_positions'):
                    agent.set_reserved_positions(reserved_positions)

        # --- Run one scheduler cycle (SimultaneousActivation: step() then advance()) ---
        self.schedule.step()

        # --- World dynamics (fires, aftershocks) ---
        fe = spread_fires(self)
        self.fires_extinguished += fe.get("extinguished", 0)
        ac = trigger_aftershocks(self)
        self.roads_cleared += ac.get("roads_cleared", 0)
        
        # --- Update active fires count for enhanced metrics ---
        self.active_fires = sum(
            1 for y in range(self.height) for x in range(self.width)
            if self.cell_type(x, y) in ("fire", CELL_FIRE)
        )
        
        # --- Collect battery recharges and rubble metrics from agents ---
        self.battery_recharges = 0
        self.rubble_cleared_total = 0
        for agent in self.schedule.agents:
            if hasattr(agent, 'battery_recharges'):
                self.battery_recharges += agent.battery_recharges
            if hasattr(agent, 'rubble_cleared'):
                self.rubble_cleared_total += agent.rubble_cleared
        
        # --- Update crisis score (basic calculation for Phase 1) ---
        self._update_crisis_score()

        # --- Hospital service (queues -> rescued) ---
        self._process_hospital_queues()

        # === DEFERRED REMOVALS ===
        # Remove survivors that were picked up (flagged) or died this tick.
        to_remove = []
        for a in list(self.schedule.agents):
            if isinstance(a, Survivor):
                if getattr(a, "_dead", False):
                    self.deaths += 1
                    to_remove.append(a)
                elif getattr(a, "_picked", False):
                    to_remove.append(a)
        for a in to_remove:
            try:
                self.grid.remove_agent(a)
            except Exception:
                pass
            try:
                self.schedule.remove(a)
            except Exception:
                pass
        # === end deferred removals ===

        # --- Metrics collection ---
        self.datacollector.collect(self)

        # --- Clear the applied plan for next tick ---
        self.pending_commands = []
        
        # --- Enhanced Stop conditions with immediate survivor check ---
        # Count remaining survivors on map in real-time
        remaining_survivors = sum(1 for a in self.schedule.agents if isinstance(a, Survivor))
        
        # Count survivors in medic transport
        carried_survivors = sum(1 for a in self.schedule.agents 
                              if hasattr(a, 'carrying') and getattr(a, 'carrying', False))
        
        # Count survivors in hospital queues
        queued_survivors = sum(len(q) for q in self.hospital_queues.values())
        
        total_active_survivors = remaining_survivors + carried_survivors + queued_survivors
        
        # AUTO-TERMINATE: If no survivors left anywhere, stop immediately
        if total_active_survivors == 0:
            self.running = False
            print(f"🏁 AUTO-TERMINATION: No survivors remaining! Rescued: {self.rescued}, Deaths: {self.deaths}")
            print(f"📊 Final stats - Survivors on map: {remaining_survivors}, Carried: {carried_survivors}, Queued: {queued_survivors}")
            return  # Exit immediately
        
        # Compute total survivors once for percentage tracking
        if self.total_survivors is None:
            self.total_survivors = (
                remaining_survivors + carried_survivors + queued_survivors + self.rescued + self.deaths
            )

        # Stop when all survivors resolved or after reasonable time limit
        if self.rescued + self.deaths >= self.total_survivors and self.total_survivors > 0:
            self.running = False
            print(f"🏁 Simulation complete! Rescued: {self.rescued}, Deaths: {self.deaths}, Total: {self.total_survivors}")

        # or stop at a reasonable cap to prevent infinite runs
        MAX_TICKS = 500
        if self.time >= MAX_TICKS:
            self.running = False
            print(f"⏰ Simulation ended at time limit ({MAX_TICKS} steps)")

        # Also check for agent battery depletion - if all agents are out of battery, end
        active_agents = [a for a in self.schedule.agents if hasattr(a, 'battery_level')]
        if active_agents and all(getattr(a, 'battery_level', 100) <= 0 for a in active_agents):
            self.running = False
            print("🔋 Simulation ended: All agents out of battery!")

    def extinguish_fire_at(self, x, y):
        """Remove fire cell agent when fire is extinguished."""
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.cell_types[y][x] == CELL_FIRE:
                self.cell_types[y][x] = CELL_ROAD  # Convert back to road
                
                # Remove the fire environment agent
                cell_contents = self.grid.get_cell_list_contents([(x, y)])
                for agent in cell_contents:
                    if isinstance(agent, EnvironmentCell) and agent.cell_type == CELL_FIRE:
                        self.grid.remove_agent(agent)
                        self.schedule.remove(agent)
                        break

    def add_fire_at(self, x, y):
        """Add fire cell agent when fire spreads."""
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.cell_types[y][x] != CELL_FIRE:
                self.cell_types[y][x] = CELL_FIRE
                
                # Add fire environment agent for visualization
                fire_cell = EnvironmentCell(self.next_id(), self, CELL_FIRE)
                self.schedule.add(fire_cell)
                self.grid.place_agent(fire_cell, (x, y))

    def add_rubble_at(self, x, y):
        """Add rubble cell agent when aftershock creates rubble."""
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.cell_types[y][x] != CELL_RUBBLE:
                self.cell_types[y][x] = CELL_RUBBLE
                
                # Add rubble environment agent for visualization
                rubble_cell = EnvironmentCell(self.next_id(), self, CELL_RUBBLE)
                self.schedule.add(rubble_cell)
                self.grid.place_agent(rubble_cell, (x, y))

    def clear_rubble_at(self, x, y):
        """Remove rubble cell agent when rubble is cleared."""
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.cell_types[y][x] == CELL_RUBBLE:
                self.cell_types[y][x] = CELL_ROAD  # Convert back to road
                
                # Remove the rubble environment agent
                cell_contents = self.grid.get_cell_list_contents([(x, y)])
                for agent in cell_contents:
                    if isinstance(agent, EnvironmentCell) and agent.cell_type == CELL_RUBBLE:
                        self.grid.remove_agent(agent)
                        self.schedule.remove(agent)
                        break

    def _process_hospital_queues(self):
        """
        Each tick, every hospital serves up to `hospital_service_rate` survivors (FIFO).
        Records time-to-admission in ticks and updates avg_rescue_time.
        """
        rate = int(self.hospital_service_rate) if self.hospital_service_rate is not None else 0
        for hpos, q in self.hospital_queues.items():
            served = 0
            while q and served < rate:
                _sid = q.pop(0)  # FIFO list
                self.rescued += 1
                # record this admission time (ticks since start)
                self._rescue_times.append(self.time)
                # update rolling average
                self.avg_rescue_time = (
                    sum(self._rescue_times) / float(len(self._rescue_times))
                )
                served += 1
            if len(q) > 10:
                self.hospital_overflow_events += 1



    def summarize_state(self):
        agents = []
        for a in self.schedule.agents:
            if hasattr(a, "kind"):
                agents.append({
                    "id": str(a.unique_id),
                    "kind": a.kind,
                    "pos": list(a.pos) if hasattr(a, "pos") else None,
                    "battery_level": getattr(a, "battery_level", None),  # Fixed field name
                    "water": getattr(a, "water", None),
                    "tools": getattr(a, "tools", None),
                    "carrying": getattr(a, "carrying", False),
                    "last_action_result": getattr(a, "last_action_result", None),  # CRITICAL: Include action feedback for learning
                    "status": getattr(a, "status", "idle"),  # Include agent status
                    "supplies": getattr(a, "supplies", None),  # For medics
                    "previous_pos": getattr(a, "previous_pos", None),  # Track position changes
                })
        hospitals = [{"pos": list(pos), "queue_len": len(q)} for pos, q in self.hospital_queues.items()]
        fires, rubble, survivors = [], [], []
        for y in range(self.height):
            for x in range(self.width):
                ct = self.cell_types[y][x]
                if ct == CELL_FIRE: fires.append([x,y])
                if ct == CELL_RUBBLE: rubble.append([x,y])
        for a in self.schedule.agents:
            if isinstance(a, Survivor):
                survivors.append({"id": str(a.unique_id), "pos": list(a.pos), "deadline": a.life_deadline})

        return {
            "grid": {"w": self.width, "h": self.height},
            "depot": list(self.depot),
            "tick": self.time,
            "agents": agents,
            "hospitals": hospitals,
            "fires": fires,
            "rubble": rubble,
            "survivors": survivors
        }

    def hospital_queue_state(self):
        return {
            "queues": [{"hospital": list(k), "len": len(v)} for k,v in self.hospital_queues.items()],
            "service_rate": self.hospital_service_rate
        }

    def cell_type(self, x, y):
        """Get the cell type at coordinates (x, y)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cell_types[y][x]
        return None

    def add_to_hospital_queue(self, pos, survivor_id: str):
        """
        Enqueue a survivor at the hospital located at `pos` (x,y).
        If the exact pos is not a hospital key, fallback to the nearest hospital.
        """
        key = tuple(pos)
        if key not in self.hospital_queues:
            # fallback to nearest hospital by Manhattan distance
            if not self.hospital_queues:
                return
            px, py = key
            nearest = min(
                self.hospital_queues.keys(),
                key=lambda hp: abs(hp[0] - px) + abs(hp[1] - py)
            )
            key = nearest
        self.hospital_queues[key].append(str(survivor_id))

    def _validate_and_complete_plan(self, commands):
        """
        Validation & normalization layer:
        1. Normalize command schemas (agent vs agent_id, target vs to)
        2. Convert infeasible ACTs to MOVEs when target is distant  
        3. Fill missing agents with mock commands
        4. Ensure exactly one command per agent
        """
        if not commands:
            commands = []
        
        # Get all agent IDs that should have commands
        all_agents = [a for a in self.schedule.agents if hasattr(a, "kind")]
        all_agent_ids = {str(a.unique_id) for a in all_agents}
        agent_positions = {str(a.unique_id): tuple(a.pos) for a in all_agents}
        
        # Step 1: Normalize command schemas
        normalized_commands = []
        for cmd in commands:
            if not isinstance(cmd, dict):
                continue
            
            # Normalize agent_id key
            agent_id = cmd.get("agent_id") or cmd.get("agent")
            if not agent_id:
                continue
            agent_id = str(agent_id)
            
            # Normalize move commands
            if cmd.get("type") == "move":
                target = cmd.get("to") or cmd.get("target")
                if target:
                    normalized_commands.append({
                        "agent_id": agent_id,
                        "type": "move", 
                        "to": list(target)
                    })
            
            # Normalize act commands - NO DISTANCE VALIDATION OR CONVERSION
            elif cmd.get("type") == "act":
                action_name = cmd.get("action_name") or cmd.get("action")
                target = cmd.get("to") or cmd.get("target")
                
                # Accept the LLM command as-is - no rule-based fallback validation
                act_cmd = {
                    "agent_id": agent_id,
                    "type": "act",
                    "action_name": action_name
                }
                if target:
                    act_cmd["to"] = target
                normalized_commands.append(act_cmd)
        
        # Step 2: Report missing agents but NO FALLBACK
        commanded_agents = {cmd.get("agent_id") for cmd in normalized_commands}
        missing_agents = all_agent_ids - commanded_agents
        
        if missing_agents:
            print(f"❌ Missing agents (NO FALLBACK): {sorted(missing_agents)}")
            logger.warning(f"Missing agent commands: {sorted(missing_agents)} - NO RULE-BASED FALLBACK APPLIED")
            # NO FALLBACK - let the system handle incomplete commands
        
        print(f"✅ Plan validation complete: {len(normalized_commands)} commands for {len(all_agent_ids)} agents")
        return normalized_commands


    def _process_hospital_queues(self):
        """
        Each tick, every hospital serves up to `hospital_service_rate` survivors (FIFO).
        Increments self.rescued and tracks rescue times for metrics.
        """
        rate = int(self.hospital_service_rate) if self.hospital_service_rate is not None else 0
        for hpos, q in self.hospital_queues.items():
            served = 0
            while q and served < rate:
                survivor_id = q.pop(0)  # FIFO list
                self.rescued += 1
                served += 1
                
                # Track rescue time - current time represents when rescue is completed
                # For now, use current simulation time as rescue completion time
                self.add_rescue_time(self.time)
                
            # Track hospital overflow events
            if len(q) > 10:
                self.hospital_overflow_events += 1

    def _update_crisis_score(self):
        """
        Calculate crisis score based on current simulation state.
        Higher scores indicate better crisis management performance.
        This is a basic implementation for Phase 1, will be enhanced in Phase 4.
        """
        if self.total_survivors is None or self.total_survivors == 0:
            self.crisis_score = 0.0
            return
            
        # Base score components (0-100 scale)
        rescue_efficiency = (self.rescued / self.total_survivors) * 40  # 40% weight
        mortality_penalty = (self.deaths / self.total_survivors) * -30  # -30% penalty
        fire_control = max(0, (self.fires_extinguished / max(1, self.active_fires + self.fires_extinguished)) * 20)  # 20% weight
        time_penalty = max(0, (100 - self.time) / 100) * 10  # 10% weight for speed
        
        # Combine components
        raw_score = rescue_efficiency + mortality_penalty + fire_control + time_penalty
        
        # Normalize to 0-100 range and apply smoothing
        self.crisis_score = max(0.0, min(100.0, raw_score))

    def is_blocked(self, x, y):
        return self.cell_type(x,y) in (CELL_FIRE, CELL_RUBBLE, CELL_BUILDING)

    def increment_tool_calls(self):
        """Increment tool calls counter when LLM makes a planning request."""
        self.tool_calls += 1

    def increment_invalid_json(self):
        """Increment invalid JSON counter when LLM returns malformed response."""
        self.invalid_json += 1

    def increment_replans(self):
        """Increment replans counter when LLM needs to retry planning."""
        self.replans += 1

    def increment_energy_used(self, amount=1):
        """Increment energy used counter for agent actions."""
        self.energy_used += amount

    def calculate_avg_rescue_time(self):
        """Calculate average rescue time from collected rescue events."""
        if self._rescue_times:
            self.avg_rescue_time = sum(self._rescue_times) / len(self._rescue_times)
        else:
            self.avg_rescue_time = 0.0

    def add_rescue_time(self, time_taken):
        """Add a rescue time measurement."""
        self._rescue_times.append(time_taken)
        self.calculate_avg_rescue_time()

    def export_metrics_json(self) -> dict:
        """
        Export all assignment-required metrics as JSON.
        
        Returns:
            dict: Complete metrics dictionary ready for JSON export
        """
        # Ensure avg_rescue_time is current
        self.calculate_avg_rescue_time()
        
        metrics = {
            # Core assignment metrics
            "rescued": self.rescued,
            "deaths": self.deaths,
            "avg_rescue_time": round(self.avg_rescue_time, 2),
            "fires_extinguished": self.fires_extinguished,
            "roads_cleared": self.roads_cleared,
            "energy_used": self.energy_used,
            "tool_calls": self.tool_calls,
            "invalid_json": self.invalid_json,
            "replans": self.replans,
            "hospital_overflow_events": self.hospital_overflow_events,
            
            # Additional analysis metrics
            "battery_recharges": self.battery_recharges,
            "rubble_cleared_total": self.rubble_cleared_total,
            "active_fires": self.active_fires,
            "total_decisions": self.total_decisions,
            "optimal_decisions": self.optimal_decisions,
            "crisis_score": round(self.crisis_score, 2),
            "current_strategy": self.current_strategy,
            
            # Agent performance
            "agent_actions": self.agent_actions.copy(),
            
            # Simulation metadata
            "total_survivors": self.total_survivors or 0,
            "simulation_time": self.time,
            "simulation_completed": not self.running
        }
        
        return metrics

    def export_metrics_jsonl(self, file_path: str):
        """
        Export metrics in JSONL format for assignment requirements.
        
        Args:
            file_path: Path to save the JSONL metrics file
        """
        import json
        from pathlib import Path
        
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Get metrics
        metrics = self.export_metrics_json()
        
        # Save as JSONL (one line)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False)
            f.write('\n')
        
        print(f"📊 Metrics exported to: {file_path}")
        return metrics

import yaml, os

def load_map_config(path: str):
    """
    Load a YAML map config and return it as a Python dict.
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)

