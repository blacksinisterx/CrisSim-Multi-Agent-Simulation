# config_simple.py - Simplified configuration for testing

import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SimulationConfig:
    """Simple simulation configuration."""
    width: int = 20
    height: int = 20
    seed: int = 42
    max_steps: int = 200
    num_medics: int = 2
    num_trucks: int = 2
    num_drones: int = 1
    num_survivors: int = 10

class SimpleConfigManager:
    """Simplified configuration manager."""
    
    def __init__(self):
        self.sim_config = SimulationConfig()
        
    def validate_config(self) -> bool:
        """Simple validation."""
        return (self.sim_config.width > 0 and 
                self.sim_config.height > 0 and
                self.sim_config.max_steps > 0)

# Test the simple config
if __name__ == "__main__":
    config = SimpleConfigManager()
    print(f"Config created: {config.sim_config.width}x{config.sim_config.height}")
    print(f"Validation: {'✅ Pass' if config.validate_config() else '❌ Fail'}")
