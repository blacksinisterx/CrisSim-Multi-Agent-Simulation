# utils/config_manager.py - Configuration Management System

import yaml
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class SimulationConfig:
    """Configuration class for simulation parameters."""
    # Simulation parameters
    width: int = 20
    height: int = 20
    max_ticks: int = 300
    seed: int = 42
    
    # Agent parameters
    num_medics: int = 2
    num_trucks: int = 1
    num_drones: int = 1
    
    # Environment parameters
    fire_spread_probability: float = 0.15
    aftershock_probability: float = 0.02
    hospital_service_rate: int = 2
    
    # Resource parameters
    medic_capacity: int = 1
    truck_water_max: int = 30
    truck_tools_max: int = 10
    drone_battery_max: int = 80
    
    # Reasoning parameters
    strategy: str = "mock"
    llm_provider: str = "ollama"
    llm_temperature: float = 0.1
    max_tool_calls: int = 10

@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: int = 30
    rate_limit_rpm: int = 60
    fallback_provider: Optional[str] = "groq"
    fallback_model: Optional[str] = "llama-3.3-70b-versatile"

@dataclass
class EvaluationConfig:
    """Configuration for evaluation and metrics."""
    crisis_score_weights: Dict[str, float] = None
    decision_quality_threshold: float = 0.7
    performance_metrics: list = None
    output_format: str = "csv"
    save_detailed_logs: bool = True
    
    def __post_init__(self):
        if self.crisis_score_weights is None:
            self.crisis_score_weights = {
                "rescue_efficiency": 0.4,
                "mortality_penalty": -0.3,
                "fire_control": 0.2,
                "time_penalty": 0.1
            }
        
        if self.performance_metrics is None:
            self.performance_metrics = [
                "rescued", "deaths", "fires_extinguished", 
                "crisis_score", "decision_quality"
            ]

class ConfigManager:
    """Centralized configuration management system."""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Load default configurations
        self.simulation = SimulationConfig()
        self.llm = LLMConfig()
        self.evaluation = EvaluationConfig()
        
        # Load from environment variables
        self._load_from_env()
    
    def load_config_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
                return yaml.safe_load(f) or {}
            elif config_path.suffix.lower() == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
    
    def save_config(self, config_name: str, config_type: str = "simulation"):
        """Save current configuration to file."""
        config_file = self.config_dir / f"{config_name}.yaml"
        
        if config_type == "simulation":
            config_dict = asdict(self.simulation)
        elif config_type == "llm":
            config_dict = asdict(self.llm)
        elif config_type == "evaluation":
            config_dict = asdict(self.evaluation)
        else:
            raise ValueError(f"Unknown configuration type: {config_type}")
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def update_from_file(self, config_path: str, config_type: str = "simulation"):
        """Update configuration from file."""
        config_data = self.load_config_file(config_path)
        
        if config_type == "simulation":
            for key, value in config_data.items():
                if hasattr(self.simulation, key):
                    setattr(self.simulation, key, value)
        elif config_type == "llm":
            for key, value in config_data.items():
                if hasattr(self.llm, key):
                    setattr(self.llm, key, value)
        elif config_type == "evaluation":
            for key, value in config_data.items():
                if hasattr(self.evaluation, key):
                    setattr(self.evaluation, key, value)
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # LLM configuration from environment
        if os.getenv("LLM_PROVIDER"):
            self.llm.provider = os.getenv("LLM_PROVIDER")
        
        if os.getenv("GEMINI_API_KEY"):
            self.llm.api_key = os.getenv("GEMINI_API_KEY")
        elif os.getenv("GROQ_API_KEY"):
            self.llm.api_key = os.getenv("GROQ_API_KEY")
        
        # Simulation parameters from environment
        if os.getenv("CRISIS_SIM_SEED"):
            self.simulation.seed = int(os.getenv("CRISIS_SIM_SEED"))
        
        if os.getenv("CRISIS_SIM_STRATEGY"):
            self.simulation.strategy = os.getenv("CRISIS_SIM_STRATEGY")
    
    def get_map_config(self, map_name: str) -> Dict[str, Any]:
        """Load map configuration by name."""
        map_file = self.config_dir / f"{map_name}.yaml"
        if map_file.exists():
            return self.load_config_file(map_file)
        
        # Fallback to default map configurations
        map_file = self.config_dir / "map_small.yaml"
        if map_file.exists():
            return self.load_config_file(map_file)
        
        # Return basic default if no map files exist
        return {
            "width": 20,
            "height": 20,
            "depot": [1, 1],
            "hospitals": [[17, 2], [15, 15]],
            "initial_fires": [[8, 3], [12, 12]],
            "survivors": 15
        }
    
    def validate_config(self) -> bool:
        """Validate current configuration for completeness and consistency."""
        issues = []
        
        # Validate simulation config
        if self.simulation.width <= 0 or self.simulation.height <= 0:
            issues.append("Grid dimensions must be positive")
        
        if self.simulation.max_ticks <= 0:
            issues.append("Max ticks must be positive")
        
        # Validate LLM config
        if self.llm.provider in ["gemini", "groq"] and not self.llm.api_key:
            issues.append(f"API key required for provider: {self.llm.provider}")
        
        # Validate evaluation config
        if abs(sum(self.evaluation.crisis_score_weights.values())) > 1.1:
            issues.append("Crisis score weights should sum to approximately 1.0")
        
        if issues:
            print("Configuration validation issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        
        return True

# Global configuration manager instance
config_manager = ConfigManager()

def get_config() -> ConfigManager:
    """Get the global configuration manager instance."""
    return config_manager
