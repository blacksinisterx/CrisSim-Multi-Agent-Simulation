# config.py - Configuration management system for Crisis Simulation

import os
import yaml
import json
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class SimulationConfig:
    """Configuration for crisis simulation parameters."""
    # Basic simulation settings
    width: int = 20
    height: int = 20
    seed: int = 42
    max_steps: int = 200
    
    # Agent parameters
    num_medics: int = 2
    num_trucks: int = 2
    num_drones: int = 1
    num_survivors: int = 10
    
    # World dynamics
    fire_spread_probability: float = 0.15
    aftershock_probability: float = 0.02
    hospital_service_rate: int = 2
    
    # Agent capabilities
    medic_capacity: int = 1
    truck_water_max: int = 30
    truck_tools_max: int = 10
    drone_battery_max: int = 80

@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    primary_provider: str = "gemini"
    fallback_provider: str = "groq" 
    
    # Gemini settings
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""
    
    # Groq settings  
    groq_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str = ""
    
    # Tool calling settings
    max_tool_calls: int = 10
    tool_call_timeout: float = 30.0
    enable_thinking: bool = True

@dataclass
class StrategyConfig:
    """Configuration for reasoning strategies."""
    active_strategies: list = None
    
    # ReAct settings
    react_max_iterations: int = 5
    react_enable_reflection: bool = True
    
    # Reflexion settings
    reflexion_memory_size: int = 100
    reflexion_critique_enabled: bool = True
    
    # Chain-of-Thought settings  
    cot_reasoning_depth: int = 3
    cot_enable_verification: bool = True
    
    def __post_init__(self):
        if self.active_strategies is None:
            self.active_strategies = ["react", "reflexion", "cot"]

@dataclass
class EvaluationConfig:
    """Configuration for evaluation and metrics."""
    enable_detailed_logging: bool = True
    save_decision_traces: bool = True
    
    # Performance metrics
    target_crisis_score: float = 75.0
    min_rescue_rate: float = 0.8
    max_mortality_rate: float = 0.2
    
    # Evaluation settings
    num_evaluation_seeds: int = 5
    evaluation_maps: list = None
    
    def __post_init__(self):
        if self.evaluation_maps is None:
            self.evaluation_maps = ["configs/map_small.yaml", "configs/map_medium.yaml"]

class ConfigManager:
    """Configuration management system with environment variable support."""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Default configurations
        self.sim_config = SimulationConfig()
        self.llm_config = LLMConfig()
        self.strategy_config = StrategyConfig()
        self.eval_config = EvaluationConfig()
        
        # Load from environment variables
        self._load_from_env()
        
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # LLM API keys
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            self.llm_config.gemini_api_key = gemini_key
            
        groq_key = os.getenv("GROQ_API_KEY")  
        if groq_key:
            self.llm_config.groq_api_key = groq_key
            
        # Provider selection
        llm_provider = os.getenv("LLM_PROVIDER")
        if llm_provider:
            self.llm_config.primary_provider = llm_provider
            
        # Simulation parameters
        if os.getenv("SIM_SEED"):
            self.sim_config.seed = int(os.getenv("SIM_SEED"))
            
        if os.getenv("MAX_STEPS"):
            self.sim_config.max_steps = int(os.getenv("MAX_STEPS"))
            
    def load_config_file(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            if filepath.suffix.lower() == '.yaml' or filepath.suffix.lower() == '.yml':
                return yaml.safe_load(f) or {}
            elif filepath.suffix.lower() == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {filepath.suffix}")
                
    def save_config(self, filename: str = "simulation_config.yaml"):
        """Save current configuration to file."""
        config_data = {
            "simulation": asdict(self.sim_config),
            "llm": asdict(self.llm_config),
            "strategies": asdict(self.strategy_config),
            "evaluation": asdict(self.eval_config)
        }
        
        # Remove sensitive data from saved config
        if "gemini_api_key" in config_data["llm"]:
            config_data["llm"]["gemini_api_key"] = "***"
        if "groq_api_key" in config_data["llm"]:
            config_data["llm"]["groq_api_key"] = "***"
            
        filepath = self.config_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
        print(f"Configuration saved to {filepath}")
        
    def load_from_file(self, filename: str):
        """Load configuration from existing file."""
        filepath = self.config_dir / filename
        config_data = self.load_config_file(filepath)
        
        # Update configurations
        if "simulation" in config_data:
            sim_data = config_data["simulation"]
            for key, value in sim_data.items():
                if hasattr(self.sim_config, key):
                    setattr(self.sim_config, key, value)
                    
        if "llm" in config_data:
            llm_data = config_data["llm"]
            for key, value in llm_data.items():
                if hasattr(self.llm_config, key) and key not in ["gemini_api_key", "groq_api_key"]:
                    setattr(self.llm_config, key, value)
                    
        if "strategies" in config_data:
            strategy_data = config_data["strategies"]
            for key, value in strategy_data.items():
                if hasattr(self.strategy_config, key):
                    setattr(self.strategy_config, key, value)
                    
        if "evaluation" in config_data:
            eval_data = config_data["evaluation"]
            for key, value in eval_data.items():
                if hasattr(self.eval_config, key):
                    setattr(self.eval_config, key, value)
                    
        print(f"Configuration loaded from {filepath}")
        
    def get_full_config(self) -> Dict[str, Any]:
        """Get complete configuration as dictionary."""
        return {
            "simulation": asdict(self.sim_config),
            "llm": asdict(self.llm_config),
            "strategies": asdict(self.strategy_config), 
            "evaluation": asdict(self.eval_config)
        }
        
    def validate_config(self) -> bool:
        """Validate current configuration."""
        errors = []
        
        # Check LLM configuration
        if not self.llm_config.gemini_api_key and not self.llm_config.groq_api_key:
            errors.append("No LLM API keys provided")
            
        # Check simulation parameters
        if self.sim_config.width <= 0 or self.sim_config.height <= 0:
            errors.append("Invalid grid dimensions")
            
        if self.sim_config.max_steps <= 0:
            errors.append("Invalid max_steps value")
            
        # Check strategy configuration
        valid_strategies = {"react", "reflexion", "cot", "mock"}
        if not all(s in valid_strategies for s in self.strategy_config.active_strategies):
            errors.append("Invalid strategy names provided")
            
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
            
        print("Configuration validation passed")
        return True

# Global configuration manager (lazy initialization)
_config_manager = None

def get_config() -> ConfigManager:
    """Get the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def load_map_config(map_path: str) -> Dict[str, Any]:
    """Load a map configuration file."""
    return get_config().load_config_file(map_path)
