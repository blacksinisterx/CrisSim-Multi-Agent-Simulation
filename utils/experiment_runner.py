# experiment_runner.py - Automated experiment execution and management

import os
import json
import time
import random
import traceback
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.config import get_config, load_map_config
from utils.logging import CrisisLogger
from env.world import CrisisModel
from reasoning.planner import AgentPlanner

@dataclass
class ExperimentResult:
    """Results from a single experiment run."""
    experiment_id: str
    config_name: str
    strategy: str
    seed: int
    steps_completed: int
    success: bool
    error_message: str = ""
    
    # Performance metrics
    crisis_score: float = 0.0
    survivors_rescued: int = 0
    total_survivors: int = 0
    rescue_rate: float = 0.0
    response_time: float = 0.0
    coordination_efficiency: float = 0.0
    
    # Execution metrics
    total_tool_calls: int = 0
    failed_tool_calls: int = 0
    reasoning_time: float = 0.0
    execution_time: float = 0.0

@dataclass
class ExperimentSuite:
    """Configuration for a suite of experiments."""
    name: str
    description: str
    strategies: List[str]
    maps: List[str]
    seeds: List[int]
    num_runs_per_config: int = 3
    max_concurrent_runs: int = 2
    timeout_per_run: float = 300.0  # 5 minutes per run

class ExperimentRunner:
    """Automated experiment runner with parallel execution."""
    
    def __init__(self, results_dir: str = "results/experiments"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_manager = get_config()
        self.logger = CrisisLogger("experiment_runner")
        
        # Experiment tracking
        self.current_suite: Optional[ExperimentSuite] = None
        self.all_results: List[ExperimentResult] = []
        
    def create_experiment_suite(self, suite_config: Dict[str, Any]) -> ExperimentSuite:
        """Create an experiment suite from configuration."""
        return ExperimentSuite(
            name=suite_config.get("name", "default_suite"),
            description=suite_config.get("description", ""),
            strategies=suite_config.get("strategies", ["react", "reflexion"]),
            maps=suite_config.get("maps", ["configs/map_small.yaml"]),
            seeds=suite_config.get("seeds", [42, 123, 456]),
            num_runs_per_config=suite_config.get("num_runs_per_config", 3),
            max_concurrent_runs=suite_config.get("max_concurrent_runs", 2),
            timeout_per_run=suite_config.get("timeout_per_run", 300.0)
        )
        
    def run_single_experiment(self, strategy: str, map_path: str, seed: int, 
                             experiment_id: str) -> ExperimentResult:
        """Run a single experiment with the given parameters."""
        start_time = time.time()
        result = ExperimentResult(
            experiment_id=experiment_id,
            config_name=Path(map_path).stem,
            strategy=strategy,
            seed=seed,
            steps_completed=0,
            success=False
        )
        
        try:
            # Load map configuration
            map_config = load_map_config(map_path)
            
            # Update simulation config with map settings
            sim_config = self.config_manager.sim_config
            for key, value in map_config.items():
                if hasattr(sim_config, key):
                    setattr(sim_config, key, value)
            
            # Set seed for reproducibility
            sim_config.seed = seed
            random.seed(seed)
            np.random.seed(seed)
            
            # Update strategy configuration
            self.config_manager.strategy_config.active_strategies = [strategy]
            
            # Create world and planner
            world = CrisisModel(sim_config)
            planner = AgentPlanner(world, self.config_manager.llm_config, 
                                 self.config_manager.strategy_config)
            
            # Track initial state
            initial_survivors = len([a for a in world.schedule.agents 
                                   if getattr(a, 'agent_type', None) == 'survivor'])
            result.total_survivors = initial_survivors
            
            # Run simulation
            reasoning_start = time.time()
            step = 0
            
            for step in range(sim_config.max_steps):
                try:
                    world.step()
                    
                    # Update performance metrics
                    if hasattr(world, 'crisis_score'):
                        result.crisis_score = world.crisis_score
                    
                    # Count rescued survivors
                    rescued = len([a for a in world.schedule.agents 
                                 if getattr(a, 'agent_type', None) == 'survivor' 
                                 and getattr(a, 'rescued', False)])
                    result.survivors_rescued = rescued
                    
                    # Check termination conditions
                    if world.check_simulation_end():
                        break
                        
                except Exception as e:
                    self.logger.log_error(f"Error in step {step}: {e}")
                    break
                    
            result.steps_completed = step + 1
            result.reasoning_time = time.time() - reasoning_start
            
            # Calculate final metrics
            if result.total_survivors > 0:
                result.rescue_rate = result.survivors_rescued / result.total_survivors
            
            # Extract tool call statistics from planner
            if hasattr(planner, 'get_tool_call_stats'):
                tool_stats = planner.get_tool_call_stats()
                result.total_tool_calls = tool_stats.get('total', 0)
                result.failed_tool_calls = tool_stats.get('failed', 0)
            
            result.success = True
            result.execution_time = time.time() - start_time
            
            self.logger.log_info(f"Experiment {experiment_id} completed successfully")
            
        except Exception as e:
            result.error_message = str(e)
            result.execution_time = time.time() - start_time
            
            self.logger.log_error(f"Experiment {experiment_id} failed: {e}")
            self.logger.log_error(f"Traceback: {traceback.format_exc()}")
            
        return result
        
    def run_experiment_suite(self, suite: ExperimentSuite) -> List[ExperimentResult]:
        """Run a complete experiment suite with parallel execution."""
        self.current_suite = suite
        all_results = []
        
        self.logger.log_info(f"Starting experiment suite: {suite.name}")
        self.logger.log_info(f"Total experiments: {len(suite.strategies) * len(suite.maps) * len(suite.seeds)}")
        
        # Generate all experiment configurations
        experiments = []
        exp_id = 0
        
        for strategy in suite.strategies:
            for map_path in suite.maps:
                for seed in suite.seeds:
                    exp_id += 1
                    experiment_id = f"{suite.name}_{strategy}_{Path(map_path).stem}_{seed}_{exp_id:04d}"
                    experiments.append((strategy, map_path, seed, experiment_id))
        
        # Run experiments with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=suite.max_concurrent_runs) as executor:
            # Submit all experiments
            future_to_experiment = {}
            for exp_config in experiments:
                future = executor.submit(self.run_single_experiment, *exp_config)
                future_to_experiment[future] = exp_config
                
            # Collect results as they complete
            for future in as_completed(future_to_experiment, timeout=suite.timeout_per_run):
                try:
                    result = future.result(timeout=10.0)  # Additional safety timeout
                    all_results.append(result)
                    
                    self.logger.log_info(f"Completed experiment {result.experiment_id}")
                    if result.success:
                        self.logger.log_info(f"  Crisis Score: {result.crisis_score:.2f}")
                        self.logger.log_info(f"  Rescue Rate: {result.rescue_rate:.2%}")
                    else:
                        self.logger.log_error(f"  Failed: {result.error_message}")
                        
                except Exception as e:
                    exp_config = future_to_experiment[future]
                    failed_result = ExperimentResult(
                        experiment_id=f"failed_{exp_config[3]}",
                        config_name=Path(exp_config[1]).stem,
                        strategy=exp_config[0],
                        seed=exp_config[2],
                        steps_completed=0,
                        success=False,
                        error_message=f"Execution timeout or error: {e}"
                    )
                    all_results.append(failed_result)
                    self.logger.log_error(f"Experiment {exp_config[3]} failed with timeout/error: {e}")
        
        self.all_results.extend(all_results)
        
        # Save results
        self.save_results(suite.name, all_results)
        
        self.logger.log_info(f"Experiment suite {suite.name} completed")
        self.logger.log_info(f"Total results: {len(all_results)}")
        self.logger.log_info(f"Successful runs: {sum(1 for r in all_results if r.success)}")
        
        return all_results
        
    def save_results(self, suite_name: str, results: List[ExperimentResult]):
        """Save experiment results to files."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_filename = f"{suite_name}_{timestamp}"
        
        # Save detailed results as JSON
        json_file = self.results_dir / f"{base_filename}_detailed.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(result) for result in results], f, indent=2)
            
        # Save summary statistics as CSV
        csv_file = self.results_dir / f"{base_filename}_summary.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("experiment_id,strategy,config,seed,success,crisis_score,rescue_rate,steps_completed,execution_time,reasoning_time,tool_calls,failed_calls\n")
            
            # Write data
            for result in results:
                f.write(f"{result.experiment_id},{result.strategy},{result.config_name},{result.seed},"
                       f"{result.success},{result.crisis_score:.2f},{result.rescue_rate:.3f},"
                       f"{result.steps_completed},{result.execution_time:.2f},{result.reasoning_time:.2f},"
                       f"{result.total_tool_calls},{result.failed_tool_calls}\n")
                       
        self.logger.log_info(f"Results saved to {json_file} and {csv_file}")
        
    def analyze_results(self, results: List[ExperimentResult]) -> Dict[str, Any]:
        """Analyze experiment results and generate statistics."""
        if not results:
            return {"error": "No results to analyze"}
            
        analysis = {
            "total_experiments": len(results),
            "successful_experiments": sum(1 for r in results if r.success),
            "success_rate": sum(1 for r in results if r.success) / len(results),
            "strategies_tested": list(set(r.strategy for r in results)),
            "configs_tested": list(set(r.config_name for r in results)),
        }
        
        # Per-strategy analysis
        strategy_stats = {}
        for strategy in analysis["strategies_tested"]:
            strategy_results = [r for r in results if r.strategy == strategy and r.success]
            if strategy_results:
                strategy_stats[strategy] = {
                    "runs": len(strategy_results),
                    "avg_crisis_score": np.mean([r.crisis_score for r in strategy_results]),
                    "avg_rescue_rate": np.mean([r.rescue_rate for r in strategy_results]),
                    "avg_execution_time": np.mean([r.execution_time for r in strategy_results]),
                    "avg_reasoning_time": np.mean([r.reasoning_time for r in strategy_results]),
                    "avg_tool_calls": np.mean([r.total_tool_calls for r in strategy_results]),
                }
                
        analysis["strategy_statistics"] = strategy_stats
        
        # Overall performance metrics
        successful_results = [r for r in results if r.success]
        if successful_results:
            analysis["overall_performance"] = {
                "avg_crisis_score": np.mean([r.crisis_score for r in successful_results]),
                "std_crisis_score": np.std([r.crisis_score for r in successful_results]),
                "avg_rescue_rate": np.mean([r.rescue_rate for r in successful_results]),
                "std_rescue_rate": np.std([r.rescue_rate for r in successful_results]),
                "best_crisis_score": max(r.crisis_score for r in successful_results),
                "worst_crisis_score": min(r.crisis_score for r in successful_results),
            }
            
        return analysis
        
    def load_results(self, results_file: str) -> List[ExperimentResult]:
        """Load experiment results from a JSON file."""
        filepath = self.results_dir / results_file
        if not filepath.exists():
            raise FileNotFoundError(f"Results file not found: {filepath}")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return [ExperimentResult(**item) for item in data]

def run_standard_evaluation() -> Dict[str, Any]:
    """Run a standard evaluation suite for the crisis simulation."""
    runner = ExperimentRunner()
    
    # Define standard evaluation suite
    suite_config = {
        "name": "standard_evaluation",
        "description": "Standard evaluation with multiple strategies and maps",
        "strategies": ["react", "reflexion", "mock"],  # Include mock for baseline
        "maps": ["configs/map_small.yaml"],  # Start with small map
        "seeds": [42, 123, 456, 789, 999],  # 5 different seeds
        "num_runs_per_config": 1,  # Single run per config for now
        "max_concurrent_runs": 2,
        "timeout_per_run": 180.0  # 3 minutes per run
    }
    
    suite = runner.create_experiment_suite(suite_config)
    results = runner.run_experiment_suite(suite)
    
    # Generate analysis
    analysis = runner.analyze_results(results)
    
    # Save analysis
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    analysis_file = runner.results_dir / f"standard_evaluation_{timestamp}_analysis.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
        
    return analysis

if __name__ == "__main__":
    # Run standard evaluation if executed directly
    print("Starting standard evaluation...")
    analysis = run_standard_evaluation()
    print(f"Evaluation completed. Success rate: {analysis['success_rate']:.2%}")
    
    if "overall_performance" in analysis:
        perf = analysis["overall_performance"]
        print(f"Average crisis score: {perf['avg_crisis_score']:.2f} ± {perf['std_crisis_score']:.2f}")
        print(f"Average rescue rate: {perf['avg_rescue_rate']:.2%} ± {perf['std_rescue_rate']:.2%}")
        
    print("\nPer-strategy performance:")
    if "strategy_statistics" in analysis:
        for strategy, stats in analysis["strategy_statistics"].items():
            print(f"  {strategy}: {stats['avg_crisis_score']:.2f} crisis score, "
                  f"{stats['avg_rescue_rate']:.2%} rescue rate")
