# Utils package - Utility modules for crisis simulation

from .config import get_config, load_map_config, ConfigManager
from .logging import CrisisLogger

# Conditional imports for optional components
try:
    from .experiment_runner import ExperimentRunner, run_standard_evaluation
    EXPERIMENT_RUNNER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Experiment runner not available: {e}")
    EXPERIMENT_RUNNER_AVAILABLE = False

try:
    from .visualization import ResultsVisualizer, load_and_visualize_results
    VISUALIZATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Visualization not available: {e}")
    VISUALIZATION_AVAILABLE = False

# Core utilities are always available
__all__ = [
    'get_config',
    'load_map_config', 
    'ConfigManager',
    'CrisisLogger'
]

# Add optional utilities if available
if EXPERIMENT_RUNNER_AVAILABLE:
    __all__.extend(['ExperimentRunner', 'run_standard_evaluation'])
    
if VISUALIZATION_AVAILABLE:
    __all__.extend(['ResultsVisualizer', 'load_and_visualize_results'])
