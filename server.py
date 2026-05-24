# server.py — Enhanced Mesa visualization for Crisis Simulation

import os
import yaml
from typing import Dict, Tuple, Iterable
from mesa.visualization.modules import CanvasGrid, ChartModule, TextElement
from mesa.visualization.ModularVisualization import ModularServer
from env.world import CrisisModel
from env.agents import DroneAgent, MedicAgent, TruckAgent, Survivor

# Configuration
MAP_PATH = "configs/map_small.yaml"  # change if needed
SEED = 42
CANVAS_W = 700  # Increased for better visibility
CANVAS_H = 700


# ---------------- Enhanced Agent Portrayal ----------------

def agent_portrayal(agent):
    """Enhanced agent portrayal with proper environment cells and fire visualization."""
    if agent is None:
        return
    
    portrayal = {"Layer": 1, "Filled": "true"}
    
    # Check if this is an environment cell (fire, building, etc.)
    if hasattr(agent, 'cell_type'):
        cell_type = agent.cell_type
        
        if cell_type == "fire":
            portrayal.update({
                "Shape": "rect",
                "Color": "#e74c3c",
                "Layer": 1,
                "w": 1.0,
                "h": 1.0,
                "stroke_color": "#c0392b",
                "stroke_width": 2,
                "text": "🔥",
                "text_color": "white"
            })
            return portrayal
            
        elif cell_type == "building":
            portrayal.update({
                "Shape": "rect",
                "Color": "#7f8c8d",
                "Layer": 0,
                "w": 0.9,
                "h": 0.9,
                "stroke_color": "#2c3e50"
            })
            return portrayal
            
        elif cell_type == "hospital":
            portrayal.update({
                "Shape": "rect",
                "Color": "#27ae60",
                "Layer": 0,
                "w": 0.95,
                "h": 0.95,
                "stroke_color": "#1e8449",
                "stroke_width": 3,
                "text": "🏥",
                "text_color": "white"
            })
            return portrayal
            
        elif cell_type == "depot":
            portrayal.update({
                "Shape": "rect",
                "Color": "#f39c12",
                "Layer": 0,
                "w": 0.9,
                "h": 0.9,
                "stroke_color": "#d68910",
                "text": "⚡",
                "text_color": "white"
            })
            return portrayal
            
        elif cell_type == "rubble":
            portrayal.update({
                "Shape": "rect",
                "Color": "#8b4513",
                "Layer": 0,
                "w": 0.8,
                "h": 0.8,
                "stroke_color": "#654321",
                "text": "🧱",
                "text_color": "white"
            })
            return portrayal

    # Agent-specific visualizations
    if isinstance(agent, DroneAgent):
        # Enhanced drone representation with scan data
        battery_level = getattr(agent, 'battery_level', 80)
        max_battery = getattr(agent, 'battery_max', 80)
        battery_ratio = battery_level / max(max_battery, 1)
        
        # Color based on battery level
        if battery_ratio > 0.5:
            color = "#00bcd4"  # Cyan
        elif battery_ratio > 0.2:
            color = "#ff9800"  # Orange
        else:
            color = "#f44336"  # Red (low battery)
            
        # Show scan results if available
        scan_results = getattr(agent, 'last_scan_results', None)
        if scan_results:
            text = f"D:{scan_results['survivors']}S {scan_results['fires']}F"
        else:
            text = f"D:{int(battery_level)}%"
            
        portrayal.update({
            "Shape": "circle",  # Using circle since triangle not loading
            "Color": color,
            "r": 0.7,
            "stroke_color": "#006064",
            "stroke_width": 2,
            "Layer": 4,
            "text": text,
            "text_color": "white"
        })

    elif isinstance(agent, MedicAgent):
        # Dynamic medic visualization based on state
        carrying = getattr(agent, "carrying", False) or getattr(agent, "current_patient", None)
        medical_supplies = getattr(agent, "medical_supplies", 10)
        
        if carrying:
            color = "#1e8449"  # Dark green when carrying
            text = "M+👤"
        else:
            color = "#2ecc71"  # Light green when available
            text = f"M:{medical_supplies}"
            
        portrayal.update({
            "Shape": "circle", 
            "Color": color,
            "r": 0.8,
            "stroke_color": "#145a32",
            "stroke_width": 2,
            "Layer": 3,
            "text": text,
            "text_color": "white"
        })

    elif isinstance(agent, TruckAgent):
        # Enhanced truck visualization - show battery but water is primary resource
        water_level = getattr(agent, "water_level", 0)
        max_water = getattr(agent, "water_capacity", 30)
        battery_level = getattr(agent, "battery_level", 100)
        
        # Color based on water level (primary resource for trucks)
        intensity = 0.3 + (0.7 * (water_level / max(max_water, 1)))
        color = f"rgba(52, 152, 219, {intensity})"
        
        # Show both water and battery, but water is primary concern
        text = f"T:{water_level}/{max_water} 🔋{battery_level}%"
        
        # Only show warning color if water is critically low (battery doesn't affect truck operation)
        if water_level <= 2:
            color = "#e74c3c"  # Red for low water
            
        portrayal.update({
            "Shape": "rect",
            "Color": color,
            "w": 0.9,
            "h": 0.9,
            "stroke_color": "#2980b9",
            "stroke_width": 2,
            "Layer": 3,
            "text": text,
            "text_color": "white"
        })

    elif isinstance(agent, Survivor):
        # FIXED: Enhanced survivor visualization with proper health status
        health = getattr(agent, "health", "stable")
        rescued = getattr(agent, "rescued", False)
        life_remaining = getattr(agent, "life_deadline", 100)
        
        if rescued:
            color = "#52c41a"  # Green for rescued
            text = "R"
            size = 0.5
        else:
            # Color based on health status AND life remaining
            if health == "critical" or life_remaining < 50:
                color = "#ff4d4f"  # Red for critical/dying
                text = "💀"
                size = 0.6
            elif health == "injured" or life_remaining < 100:
                color = "#fa8c16"  # Orange for injured
                text = "🤕" 
                size = 0.6
            else:
                color = "#f1c40f"  # Yellow for healthy
                text = "👤"
                size = 0.6
            
        portrayal.update({
            "Shape": "circle",
            "Color": color,
            "r": size,
            "stroke_color": "#000000",
            "stroke_width": 1,
            "Layer": 2,
            "text": text,
            "text_color": "black"
        })

    else:
        # Default representation for unknown agents
        portrayal.update({
            "Shape": "circle",
            "Color": "#95a5a6",
            "r": 0.5,
            "Layer": 1
        })

    return portrayal


def grid_portrayal(cell_value, x, y, model):
    """Enhanced grid cell portrayal for environment visualization."""
    if cell_value == "fire":
        return {
            "Shape": "rect",
            "Color": "#e74c3c",
            "w": 1,
            "h": 1,
            "Layer": 0,
            "Filled": "true"
        }
    elif cell_value == "rubble":
        return {
            "Shape": "rect",
            "Color": "#7f8c8d",
            "w": 1,
            "h": 1,
            "Layer": 0,
            "Filled": "true"
        }
    elif cell_value == "hospital":
        return {
            "Shape": "rect",
            "Color": "#27ae60",
            "w": 1,
            "h": 1,
            "Layer": 0,
            "Filled": "true",
            "stroke_color": "#1e8449",
            "stroke_width": 3
        }
    elif cell_value == "depot":
        return {
            "Shape": "rect",
            "Color": "#9b59b6",
            "w": 1,
            "h": 1,
            "Layer": 0,
            "Filled": "true",
            "stroke_color": "#6c3483",
            "stroke_width": 3
        }
    elif cell_value == "building":
        return {
            "Shape": "rect",
            "Color": "#bdc3c7",
            "w": 1,
            "h": 1,
            "Layer": 0,
            "Filled": "true"
        }
    # Road and empty cells are transparent (no portrayal needed)
    return None


# ---------------- Config helpers ----------------

def load_cfg(path: str) -> Dict:
    if not os.path.exists(path):
        # No YAML — run with an empty config
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _iter_points_from_cfg(cfg: Dict) -> Iterable[Tuple[int, int]]:
    """Yield all (x,y) points referenced in the cfg to infer bounds."""
    depot = cfg.get("depot")
    if isinstance(depot, (list, tuple)) and len(depot) == 2:
        yield (int(depot[0]), int(depot[1]))

    for key in ("hospitals", "rubble", "initial_fires", "buildings"):
        for item in cfg.get(key, []) or []:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                yield (int(item[0]), int(item[1]))

    for s in (cfg.get("survivors_list") or []):
        if isinstance(s, dict) and "pos" in s and isinstance(s["pos"], (list, tuple)) and len(s["pos"]) == 2:
            yield (int(s["pos"][0]), int(s["pos"][1]))
        elif isinstance(s, (list, tuple)) and len(s) == 2:
            yield (int(s[0]), int(s[1]))


def infer_grid_size(cfg: Dict, default: Tuple[int, int] = (20, 20)) -> Tuple[int, int]:
    """Determine (width, height) from cfg, supporting multiple schema variants."""
    grid = cfg.get("grid") or {}
    if isinstance(grid, dict) and "w" in grid and "h" in grid:
        return int(grid["w"]), int(grid["h"])

    if "width" in cfg and "height" in cfg:
        return int(cfg["width"]), int(cfg["height"])

    max_x = max_y = -1
    for (x, y) in _iter_points_from_cfg(cfg):
        if x > max_x: max_x = x
        if y > max_y: max_y = y
    if max_x >= 0 and max_y >= 0:
        return max_x + 1, max_y + 1

    return default


# ---------------- Enhanced UI Panels ----------------

class InteractiveControlPanel(TextElement):
    """Interactive control panel with dropdowns for map and strategy selection."""
    
    def render(self, model) -> str:
        current_map = getattr(model, 'map_selection', 'small')
        current_strategy = getattr(model, 'strategy_selection', 'react')
        current_provider = getattr(model, 'provider_selection', 'ollama')
        
        return f'''
        <div style="font-family: 'Segoe UI', Arial, sans-serif; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 15px; 
                    border-radius: 10px; 
                    margin: 10px 0; 
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <h3 style="margin: 0 0 15px 0; text-align: center; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                🎮 Simulation Controls
            </h3>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px;">
                <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">
                    <h4 style="margin: 0 0 8px 0; color: #FFD700;">🗺️ Map Selection</h4>
                    <select id="mapSelector" onchange="updateSimulationSetting('map_selection', this.value)" 
                            style="width: 100%; padding: 8px; border-radius: 5px; border: none; background: #2c3e50; color: white;">
                        <option value="small" {'selected' if current_map == 'small' else ''}>Small Map</option>
                        <option value="medium" {'selected' if current_map == 'medium' else ''}>Medium Map</option>
                        <option value="hard" {'selected' if current_map == 'hard' else ''}>Hard Map</option>
                    </select>
                    <div style="margin-top: 5px; font-size: 12px;">Current: <strong>{current_map.title()}</strong></div>
                </div>
                
                <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">
                    <h4 style="margin: 0 0 8px 0; color: #90EE90;">🧠 Reasoning Strategy</h4>
                    <select id="strategySelector" onchange="updateSimulationSetting('strategy_selection', this.value)"
                            style="width: 100%; padding: 8px; border-radius: 5px; border: none; background: #2c3e50; color: white;">
                        <option value="react" {'selected' if current_strategy == 'react' else ''}>ReAct</option>
                        <option value="reflexion" {'selected' if current_strategy == 'reflexion' else ''}>Reflexion</option>
                        <option value="cot" {'selected' if current_strategy == 'cot' else ''}>Chain of Thought</option>
                    </select>
                    <div style="margin-top: 5px; font-size: 12px;">Current: <strong>{current_strategy.upper()}</strong></div>
                </div>
                
                <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">
                    <h4 style="margin: 0 0 8px 0; color: #87CEEB;">🤖 LLM Provider</h4>
                    <select id="providerSelector" onchange="updateSimulationSetting('provider_selection', this.value)"
                            style="width: 100%; padding: 8px; border-radius: 5px; border: none; background: #2c3e50; color: white;">
                        <option value="mock" {'selected' if current_provider == 'mock' else ''}>Mock (No API Limits)</option>
                        <option value="gemini" {'selected' if current_provider == 'gemini' else ''}>Gemini 1.5 Flash</option>
                        <option value="groq" {'selected' if current_provider == 'groq' else ''}>Groq</option>
                        <option value="ollama" {'selected' if current_provider == 'ollama' else ''}>Ollama (Local)</option>
                    </select>
                    <div style="margin-top: 5px; font-size: 12px;">Current: <strong>{current_provider.title()}</strong></div>
                </div>
            </div>
            
            <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; margin-top: 15px; text-align: center;">
                <button onclick="restartSimulation()" 
                        style="background: #e74c3c; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px;">
                    🔄 Restart with New Settings
                </button>
                <button onclick="pauseSimulation()" 
                        style="background: #f39c12; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px;">
                    ⏸️ Pause/Resume
                </button>
            </div>
        </div>
        
        <script>
            // Store settings in localStorage for persistence
            function updateSimulationSetting(setting, value) {{
                console.log('Updating ' + setting + ' to ' + value);
                
                // Store in localStorage
                localStorage.setItem(setting, value);
                
                // Show feedback
                const selector = document.getElementById(setting.replace('_selection', 'Selector'));
                if (selector) {{
                    selector.style.backgroundColor = '#27ae60';
                    setTimeout(() => {{
                        selector.style.backgroundColor = '#2c3e50';
                    }}, 1000);
                }}
                
                // Display update message
                showUpdateMessage(setting.replace('_', ' ').toUpperCase() + ' updated to ' + value + '. Restart simulation to apply changes.');
            }}
            
            function showUpdateMessage(message) {{
                // Create or update message div
                let msgDiv = document.getElementById('updateMessage');
                if (!msgDiv) {{
                    msgDiv = document.createElement('div');
                    msgDiv.id = 'updateMessage';
                    msgDiv.style.cssText = 'position: fixed; top: 10px; right: 10px; z-index: 9999; background: #27ae60; color: white; padding: 10px 15px; border-radius: 5px; font-weight: bold; max-width: 300px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);';
                    document.body.appendChild(msgDiv);
                }}
                msgDiv.textContent = message;
                msgDiv.style.display = 'block';
                
                // Hide after 3 seconds
                setTimeout(() => {{
                    msgDiv.style.display = 'none';
                }}, 3000);
            }}
            
            function restartSimulation() {{
                console.log('Restarting simulation...');
                showUpdateMessage('Restarting simulation with new settings...');
                
                // Reload the page after a short delay
                setTimeout(() => {{
                    window.location.reload();
                }}, 1500);
            }}
            
            function pauseSimulation() {{
                console.log('Pause/Resume toggle requested');
                showUpdateMessage('Pause/Resume functionality requires manual control via browser controls.');
            }}
            
            // Load saved settings on page load
            document.addEventListener('DOMContentLoaded', function() {{
                const settings = ['map_selection', 'strategy_selection', 'provider_selection'];
                settings.forEach(setting => {{
                    const value = localStorage.getItem(setting);
                    if (value) {{
                        const selector = document.getElementById(setting.replace('_selection', 'Selector'));
                        if (selector && selector.value !== value) {{
                            selector.value = value;
                            console.log('Restored ' + setting + ' to ' + value);
                        }}
                    }}
                }});
            }});
        </script>
        '''


class DetailedStatsPanel(TextElement):
    """Enhanced statistics panel with comprehensive crisis metrics."""
    
    def render(self, model) -> str:
        # Core survivor statistics
        survivors_on_map = sum(
            1 for a in model.schedule.agents
            if a.__class__.__name__ == "Survivor"
            and not getattr(a, "_picked", False)
            and not getattr(a, "_dead", False)
        )

        survivors_being_carried = sum(
            1 for a in model.schedule.agents
            if a.__class__.__name__ == "MedicAgent" and getattr(a, "carrying", False)
        )

        survivors_in_queue = sum(len(q) for q in getattr(model, "hospital_queues", {}).values())
        
        # Agent counts
        medics_active = sum(1 for a in model.schedule.agents if isinstance(a, MedicAgent))
        trucks_active = sum(1 for a in model.schedule.agents if isinstance(a, TruckAgent))
        drones_active = sum(1 for a in model.schedule.agents if isinstance(a, DroneAgent))
        
        # Crisis metrics
        current_fires = getattr(model, 'active_fires', 0)
        avg_rescue_time = getattr(model, 'avg_rescue_time', 0.0)
        
        # Total survivors calculation
        total_survivors = getattr(model, "total_survivors", None)
        if total_survivors is None:
            total_survivors = survivors_on_map + survivors_being_carried + survivors_in_queue + model.rescued + model.deaths

        # Calculate efficiency metrics
        rescue_rate = (model.rescued / total_survivors * 100) if total_survivors > 0 else 0
        mortality_rate = (model.deaths / total_survivors * 100) if total_survivors > 0 else 0
        
        return f'''
        <div style="font-family: 'Segoe UI', Arial, sans-serif; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 15px; 
                    border-radius: 10px; 
                    margin: 10px 0; 
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <h3 style="margin: 0 0 10px 0; text-align: center; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                🚨 Crisis Simulation Dashboard - Step {getattr(model, 'time', 0)}
            </h3>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
                <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">
                    <h4 style="margin: 0 0 8px 0; color: #FFD700;">👥 Survivor Status</h4>
                    <div>✅ Rescued: <strong>{model.rescued}</strong></div>
                    <div>🚑 Being Carried: <strong>{survivors_being_carried}</strong></div>
                    <div>⏳ In Hospital Queue: <strong>{survivors_in_queue}</strong></div>
                    <div>🗺️ Still On Map: <strong>{survivors_on_map}</strong></div>
                    <div>💀 Deaths: <strong style="color: #FF6B6B;">{model.deaths}</strong></div>
                    <div>📊 Total: <strong>{total_survivors}</strong></div>
                </div>
                
                <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">
                    <h4 style="margin: 0 0 8px 0; color: #90EE90;">🚁 Active Agents</h4>
                    <div>🏥 Medics: <strong>{medics_active}</strong></div>
                    <div>🚒 Fire Trucks: <strong>{trucks_active}</strong></div>
                    <div>🛸 Drones: <strong>{drones_active}</strong></div>
                    <div style="margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.3); padding-top: 8px;">
                        <div>🔥 Active Fires: <strong style="color: #FF4500;">{current_fires}</strong></div>
                        <div>🔥 Fires Extinguished: <strong>{model.fires_extinguished}</strong></div>
                    </div>
                </div>
            </div>
            
            <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; margin-top: 15px;">
                <h4 style="margin: 0 0 8px 0; color: #87CEEB;">📈 Performance Metrics</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
                    <div>🎯 Rescue Rate: <strong style="color: #90EE90;">{rescue_rate:.1f}%</strong></div>
                    <div>⚠️ Mortality Rate: <strong style="color: #FF6B6B;">{mortality_rate:.1f}%</strong></div>
                    <div>⏱️ Avg Rescue Time: <strong>{avg_rescue_time:.1f} steps</strong></div>
                </div>
            </div>
            
            <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; margin-top: 15px;">
                <h4 style="margin: 0 0 8px 0; color: #FFC107;">🔋 Assignment Features</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
                    <div>🔋 Battery Recharges: <strong style="color: #00bcd4;">{getattr(model, 'battery_recharges', 0)}</strong></div>
                    <div>🧱 Rubble Cleared: <strong style="color: #8b4513;">{getattr(model, 'rubble_cleared_total', 0)}</strong></div>
                    <div>🏥 Hospital Overflows: <strong style="color: #ff6b6b;">{getattr(model, 'hospital_overflow_events', 0)}</strong></div>
                </div>
            </div>
        </div>
        '''


class EnhancedLegendPanel(TextElement):
    """Enhanced legend with visual indicators and detailed explanations."""
    
    def render(self, model) -> str:
        return '''
        <div style="font-family: 'Segoe UI', Arial, sans-serif; 
                    background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%); 
                    color: white; 
                    padding: 15px; 
                    border-radius: 10px; 
                    margin: 10px 0; 
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <h3 style="margin: 0 0 10px 0; text-align: center; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                🗺️ Crisis Simulation Legend
            </h3>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">
                    <h4 style="margin: 0 0 8px 0; color: #FFD700;">🤖 Agents</h4>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#2ecc71;border-radius:50%;margin-right:8px;"></span>
                        <strong>Medic</strong> (green circle, dark when carrying)
                    </div>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#3498db;margin-right:8px;"></span>
                        <strong>Fire Truck</strong> (blue square)
                    </div>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-bottom:12px solid #00bcd4;margin-right:8px;"></span>
                        <strong>Drone</strong> (cyan triangle)
                    </div>
                </div>
                
                <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">
                    <h4 style="margin: 0 0 8px 0; color: #FFD700;">👥 Survivors & Environment</h4>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#f1c40f;border-radius:50%;margin-right:8px;"></span>
                        <strong>Healthy Survivor</strong> (yellow)
                    </div>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#fa8c16;border-radius:50%;margin-right:8px;"></span>
                        <strong>Injured Survivor</strong> (orange)
                    </div>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#e74c3c;border-radius:50%;margin-right:8px;"></span>
                        <strong>Critical Survivor</strong> (red)
                    </div>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#e74c3c;margin-right:8px;"></span>
                        <strong>Fire</strong> (red square with 🔥)
                    </div>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#8b4513;margin-right:8px;"></span>
                        <strong>Rubble/Blockage</strong> (brown with 🧱)
                    </div>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#27ae60;border:2px solid #1e8449;margin-right:8px;"></span>
                        <strong>Hospital</strong> (green with border)
                    </div>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#f39c12;margin-right:8px;"></span>
                        <strong>Depot</strong> (orange with ⚡)
                    </div>
                    <div style="margin: 4px 0;">
                        <span style="display:inline-block;width:12px;height:12px;background:#7f8c8d;margin-right:8px;"></span>
                        <strong>Building/Wall</strong> (gray)
                    </div>
                </div>
            </div>
        </div>
        '''


class CrisisScorePanel(TextElement):
    """New panel to display crisis score and decision quality metrics."""
    
    def render(self, model) -> str:
        # Calculate crisis score (this will be enhanced in Phase 4)
        crisis_score = getattr(model, 'crisis_score', 0.0)
        
        # Decision quality metrics (placeholders for now)
        total_decisions = getattr(model, 'total_decisions', 0)
        optimal_decisions = getattr(model, 'optimal_decisions', 0)
        decision_quality = (optimal_decisions / total_decisions * 100) if total_decisions > 0 else 0
        
        # Get actual strategy being used (not mock)
        current_strategy = getattr(model, 'strategy_selection', 'react').upper()
        current_provider = getattr(model, 'provider_selection', 'ollama').upper()
        current_map = getattr(model, 'map_selection', 'small').title()
        
        return f'''
        <div style="font-family: 'Segoe UI', Arial, sans-serif; 
                    background: linear-gradient(135deg, #fd79a8 0%, #e84393 100%); 
                    color: white; 
                    padding: 15px; 
                    border-radius: 10px; 
                    margin: 10px 0; 
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <h3 style="margin: 0 0 10px 0; text-align: center; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                🎯 Current Simulation Configuration
            </h3>
            
            <div style="background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <h4 style="margin: 0 0 8px 0; color: #FFD700;">🎮 Active Settings</h4>
                        <div>Map: <strong>{current_map}</strong></div>
                        <div>Strategy: <strong>{current_strategy}</strong></div>
                        <div>Provider: <strong>{current_provider}</strong></div>
                        <div style="margin-top: 8px; color: #90EE90;">
                            ✅ Live AI Decision Making Active
                        </div>
                    </div>
                    <div>
                        <h4 style="margin: 0 0 8px 0; color: #90EE90;">📊 Performance Score</h4>
                        <div style="font-size: 24px; font-weight: bold; text-align: center; 
                                    background: rgba(255,255,255,0.2); padding: 10px; border-radius: 5px;">
                            {crisis_score:.2f}
                        </div>
                        <div style="margin-top: 5px; font-size: 12px; text-align: center;">
                            Decision Quality: {decision_quality:.1f}%
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''


# ---------------- Enhanced Launch Function ----------------

def find_available_port(start_port=8521, max_attempts=10):
    """Find an available port starting from start_port."""
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    
    raise OSError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")

def launch(port: int = None):
    """Launch the enhanced Mesa visualization server with automatic port detection."""
    if port is None:
        port = find_available_port(8521)
    
    print(f"🌐 Crisis Simulation UI: http://127.0.0.1:{port}")
    # print("📊 Features: Real-time metrics, enhanced visualization, agent tracking")  # Reduced startup logging
    # print("🎮 Controls: Use browser interface to start/stop/step simulation")
    # print("⏹️  Press Ctrl+C to stop the server")
    
    cfg = load_cfg(MAP_PATH)
    width, height = infer_grid_size(cfg, default=(20, 20))

    # Enhanced grid with better visualization
    grid = CanvasGrid(agent_portrayal, width, height, CANVAS_W, CANVAS_H)
    
    # Enhanced chart module with more metrics
    charts = ChartModule(
        [
            {"Label": "rescued", "Color": "#2ecc71"},
            {"Label": "deaths", "Color": "#e74c3c"},
            {"Label": "fires_extinguished", "Color": "#3498db"},
            {"Label": "active_fires", "Color": "#f39c12"},
        ],
        data_collector_name="datacollector",
        canvas_height=300,
        canvas_width=500
    )
    
    # Enhanced battery and operations chart
    battery_charts = ChartModule(
        [
            {"Label": "battery_recharges", "Color": "#9b59b6"},
            {"Label": "rubble_cleared", "Color": "#8b4513"},
            {"Label": "drone_recon", "Color": "#1abc9c"},
            {"Label": "medic_rescues", "Color": "#f1c40f"},
        ],
        data_collector_name="datacollector", 
        canvas_height=250,
        canvas_width=500
    )

    # Initialize enhanced UI panels
    control_panel = InteractiveControlPanel()
    legend_panel = EnhancedLegendPanel()
    stats_panel = DetailedStatsPanel()
    crisis_panel = CrisisScorePanel()

    # Create server with enhanced layout and user controls
    # Read settings from URL parameters (set by JavaScript localStorage)
    import urllib.parse
    
    # Default values - prioritize Ollama for better performance
    default_map = "small"
    default_strategy = "react" 
    default_provider = "ollama"  # Default to local Ollama for faster response
    
    server = ModularServer(
        CrisisModel,
        [control_panel, legend_panel, stats_panel, crisis_panel, grid, charts, battery_charts],
        "🚨 Crisis Simulation - Agentic AI Dashboard",
        {
            "width": width, 
            "height": height, 
            "rng_seed": SEED, 
            "config": cfg, 
            "render": True,
            # Enhanced parameter handling with localStorage integration
            "map_selection": default_map,
            "strategy_selection": default_strategy, 
            "provider_selection": default_provider
        },
    )
    
    server.port = port
    
    try:
        server.launch()
    except OSError as e:
        if "10048" in str(e) or "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use. Finding another port...")
            new_port = find_available_port(port + 1)
            print(f"🔄 Retrying with port {new_port}...")
            server.port = new_port
            server.launch()
        else:
            print(f"❌ Server error: {e}")
            raise


if __name__ == "__main__":
    launch()  # Use automatic port detection
