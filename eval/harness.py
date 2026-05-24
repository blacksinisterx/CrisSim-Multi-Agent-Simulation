\
import argparse, os, json, csv, sys
from pathlib import Path
from tqdm import trange
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import run_episode

def save_run_json(metrics: dict, run_id: str, map_name: str, strategy: str, seed: int, ticks: int) -> str:
    """Save individual run metrics to JSON file in results/raw/ directory."""
    # Create results/raw directory structure
    os.makedirs("results/raw", exist_ok=True)
    
    # Create filename with run details
    json_filename = f"run_{run_id}_{map_name}_{strategy}_seed{seed}.json"
    json_path = os.path.join("results", "raw", json_filename)
    
    # Prepare comprehensive run data
    run_data = {
        "run_id": run_id,
        "map": map_name,
        "strategy": strategy,
        "seed": seed,
        "ticks": ticks,
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics
    }
    
    # Save to JSON file
    with open(json_path, 'w') as f:
        json.dump(run_data, f, indent=2)
    
    print(f"  → Saved run data: {json_path}")
    return json_path

def aggregate_to_csv() -> str:
    """Aggregate all JSON files from results/raw/ into results/agg/summary.csv."""
    # Create aggregation directory
    os.makedirs("results/agg", exist_ok=True)
    
    # Assignment-required CSV columns
    csv_columns = [
        "run_id", "map", "strategy", "seed", "ticks",
        "rescued", "deaths", "avg_rescue_time", "fires_extinguished", "roads_cleared",
        "energy_used", "tool_calls", "invalid_json", "replans", "hospital_overflow_events"
    ]
    
    csv_path = os.path.join("results", "agg", "summary.csv")
    
    # Find all JSON files in results/raw/
    raw_dir = os.path.join("results", "raw")
    if not os.path.exists(raw_dir):
        print(f"Warning: No raw results directory found at {raw_dir}")
        return csv_path
    
    json_files = [f for f in os.listdir(raw_dir) if f.endswith('.json')]
    
    if not json_files:
        print(f"Warning: No JSON files found in {raw_dir}")
        return csv_path
    
    print(f"\n=== Aggregating {len(json_files)} JSON files to CSV ===")
    
    # Collect all run data
    aggregated_data = []
    
    for json_file in sorted(json_files):
        json_path = os.path.join(raw_dir, json_file)
        
        try:
            with open(json_path, 'r') as f:
                run_data = json.load(f)
            
            metrics = run_data.get('metrics', {})
            
            # Extract assignment-required fields
            csv_row = {
                "run_id": run_data.get('run_id', 'unknown'),
                "map": run_data.get('map', 'unknown'),
                "strategy": run_data.get('strategy', 'unknown'),
                "seed": run_data.get('seed', 0),
                "ticks": run_data.get('ticks', 0),
                "rescued": metrics.get('rescued', 0),
                "deaths": metrics.get('deaths', 0),
                "avg_rescue_time": metrics.get('avg_rescue_time', 0.0),
                "fires_extinguished": metrics.get('fires_extinguished', 0),
                "roads_cleared": metrics.get('roads_cleared', 0),
                "energy_used": metrics.get('energy_used', 0),
                "tool_calls": metrics.get('tool_calls', 0),
                "invalid_json": metrics.get('invalid_json', 0),
                "replans": metrics.get('replans', 0),
                "hospital_overflow_events": metrics.get('hospital_overflow_events', 0)
            }
            
            aggregated_data.append(csv_row)
            
        except Exception as e:
            print(f"Warning: Failed to process {json_file}: {e}")
            continue
    
    # Write aggregated CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(aggregated_data)
    
    print(f"✅ Aggregated {len(aggregated_data)} runs to: {csv_path}")
    
    # Print summary statistics
    if aggregated_data:
        print(f"\n=== Aggregation Summary ===")
        strategies = list(set(row['strategy'] for row in aggregated_data))
        maps = list(set(row['map'] for row in aggregated_data))
        print(f"Strategies: {strategies}")
        print(f"Maps: {maps}")
        print(f"Total runs: {len(aggregated_data)}")
        
        # Calculate averages by strategy
        for strategy in strategies:
            strategy_data = [row for row in aggregated_data if row['strategy'] == strategy]
            avg_rescued = sum(row['rescued'] for row in strategy_data) / len(strategy_data)
            avg_deaths = sum(row['deaths'] for row in strategy_data) / len(strategy_data)
            avg_energy = sum(row['energy_used'] for row in strategy_data) / len(strategy_data)
            print(f"  {strategy}: avg_rescued={avg_rescued:.1f}, avg_deaths={avg_deaths:.1f}, avg_energy={avg_energy:.1f}")
    
    return csv_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_seeds", type=int, default=3, help="Number of seeds per strategy (quick test)")
    ap.add_argument("--maps", nargs="+", default=["configs/map_medium.yaml"])
    ap.add_argument("--conditions", nargs="+", default=["react", "reflexion", "cot"])
    ap.add_argument("--ticks", type=int, default=100, help="Shorter for GUI testing")
    ap.add_argument("--memory", action="store_true", default=True, help="Enable memory optimization")
    ap.add_argument("--api_budget", type=int, default=5000, help="Lower budget for quick testing")
    ap.add_argument("--gui", action="store_true", default=False, help="Enable GUI visualization")
    ap.add_argument("--strategy", type=str, default="react", help="Single strategy for GUI testing")
    ap.add_argument("--aggregate_only", action="store_true", default=False, help="Only aggregate existing JSON files to CSV")
    args = ap.parse_args()

    # If only aggregating, run aggregation and exit
    if args.aggregate_only:
        print("=== CSV Aggregation Mode ===")
        csv_path = aggregate_to_csv()
        print(f"Aggregation complete: {csv_path}")
        return

    os.makedirs("results", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Optimized fieldnames for quick testing
    fieldnames = ["seed","provider","strategy","map","rescued","deaths","avg_rescue_time","fires_extinguished",
                  "roads_cleared","energy_used","tool_calls","invalid_json","replans","hospital_overflow_events",
                  "crisis_score","api_calls_made","api_calls_avoided","cache_hits","tokens_used","memory_enabled"]

    os.makedirs("results", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Enhanced fieldnames for memory system tracking
    fieldnames = ["seed","provider","strategy","map","rescued","deaths","avg_rescue_time","fires_extinguished",
                  "roads_cleared","energy_used","tool_calls","invalid_json","replans","hospital_overflow_events",
                  "crisis_score","api_calls_made","api_calls_avoided","cache_hits","cache_misses","tokens_used",
                  "budget_exceeded","memory_enabled"]

    for mappath in args.maps:
        mapname = Path(mappath).stem
        out_csv = f"results/{mapname}_quick_test.csv"
        
        # GUI testing mode - single strategy run
        if args.gui:
            print(f"=== GUI Testing Mode: {args.strategy.upper()} on {mapname} ===")
            
            provider = "groq" if args.strategy == "react" else "gemini"
            seed = 1001
            log_path = f"logs/gui_test_{seed}_{mapname}_{args.strategy}.txt"
            
            print(f"Running GUI test with strategy: {args.strategy}")
            print(f"Map: {mappath}")
            print(f"Provider: {provider}")
            print(f"Memory enabled: {args.memory}")
            print(f"API budget: {args.api_budget}")
            print(f"Ticks: {args.ticks}")
            print(f"Log file: {log_path}")
            
            # Run single episode with GUI
            run_id = f"gui_test_{seed}_{mapname}_{args.strategy}"
            metrics = run_episode(
                mappath, 
                seed=seed, 
                ticks=args.ticks, 
                provider=provider, 
                strategy=args.strategy, 
                log_path=log_path, 
                render=True,  # Enable GUI
                memory_enabled=args.memory,
                api_budget=args.api_budget,
                run_id=run_id
            )
            
            # Save GUI test run to JSON
            save_run_json(metrics, run_id, mapname, args.strategy, seed, args.ticks)
            
            print(f"\n=== GUI Test Results ===")
            print(f"Rescued: {metrics.get('rescued', 0)}")
            print(f"Deaths: {metrics.get('deaths', 0)}")
            print(f"Fires extinguished: {metrics.get('fires_extinguished', 0)}")
            print(f"API calls made: {metrics.get('api_calls_made', 0)}")
            print(f"Cache hits: {metrics.get('cache_hits', 0)}")
            print(f"Tokens used: {metrics.get('tokens_used', 0)}")
            
            return  # Exit after GUI test
        
        # Normal batch testing mode - Enhanced with JSON saving and CSV aggregation
        print(f"\n=== Starting Batch Evaluation ===")
        print(f"Maps: {args.maps}")
        print(f"Strategies: {args.conditions}")
        print(f"Seeds per strategy: {args.n_seeds}")
        print(f"Ticks per run: {args.ticks}")
        print(f"Memory optimization: {args.memory}")
        print(f"API budget per run: {args.api_budget}")

        # Assignment-required CSV columns for legacy compatibility
        fieldnames = ["run_id","map","strategy","seed","ticks","rescued","deaths","avg_rescue_time","fires_extinguished",
                      "roads_cleared","energy_used","tool_calls","invalid_json","replans","hospital_overflow_events"]

        for mappath in args.maps:
            mapname = Path(mappath).stem
            out_csv = f"results/{mapname}_batch_results.csv"
            
            with open(out_csv, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                # Quick test with reduced runs
                strategies = args.conditions if not args.gui else [args.strategy]
                total_runs = len(strategies) * args.n_seeds
                print(f"\nRunning {total_runs} evaluations for {mapname}")

                for strategy in strategies:
                    # Set provider based on strategy
                    if strategy == "react":
                        provider = "groq"  # Fast for ReAct iterations
                    elif strategy == "reflexion":
                        provider = "gemini"  # Better for self-reflection
                    else:  # cot
                        provider = "groq"  # Good for systematic reasoning

                    print(f"\n--- Testing {strategy.upper()} strategy with {provider} ---")
                    
                    for s in trange(args.n_seeds, desc=f"{mapname}-{strategy}"):
                        seed = 1000 + s
                        log_path = f"logs/batch_{seed}_{mapname}_{strategy}.txt"
                        run_id = f"batch_{seed}_{mapname}_{strategy}"
                        
                        # Run episode with memory optimization
                        metrics = run_episode(
                            mappath, 
                            seed=seed, 
                            ticks=args.ticks, 
                            provider=provider, 
                            strategy=strategy, 
                            log_path=log_path, 
                            render=False,  # No GUI for batch testing
                            memory_enabled=args.memory,
                            api_budget=args.api_budget,
                            run_id=run_id
                        )
                        
                        # Save individual run to JSON
                        save_run_json(metrics, run_id, mapname, strategy, seed, args.ticks)
                        
                        # Collect assignment-required metrics for CSV
                        row = {
                            "run_id": run_id,
                            "map": mapname,
                            "strategy": strategy,
                            "seed": seed,
                            "ticks": args.ticks,
                            "rescued": metrics.get("rescued", 0),
                            "deaths": metrics.get("deaths", 0),
                            "avg_rescue_time": metrics.get("avg_rescue_time", 0.0),
                            "fires_extinguished": metrics.get("fires_extinguished", 0),
                            "roads_cleared": metrics.get("roads_cleared", 0),
                            "energy_used": metrics.get("energy_used", 0),
                            "tool_calls": metrics.get("tool_calls", 0),
                            "invalid_json": metrics.get("invalid_json", 0),
                            "replans": metrics.get("replans", 0),
                            "hospital_overflow_events": metrics.get("hospital_overflow_events", 0)
                        }
                        
                        writer.writerow(row)

                # Print summary for batch test
                print(f"\n=== Batch Test Complete for {mapname} ===")
                print(f"Legacy CSV saved to: {out_csv}")
                print(f"Total runs: {total_runs}")

        # After all runs complete, aggregate to final CSV
        print(f"\n=== Final CSV Aggregation ===")
        final_csv_path = aggregate_to_csv()
        print(f"✅ All results aggregated to: {final_csv_path}")

def run_gui_test():
    """Quick GUI test function for interactive testing."""
    print("=== Interactive GUI Test ===")
    print("Usage: python -m eval.harness --gui --strategy react --maps configs/map_medium.yaml")
    print("Available strategies: react, reflexion, cot")
    print("Available maps: configs/map_small.yaml, configs/map_medium.yaml")
    
    # Set environment for GUI testing
    os.environ["LLM_PROVIDER"] = "groq"  # Fast for testing
    os.environ["STRATEGY"] = "react"     # Default strategy
    
    return True

def analyze_memory_results(csv_path: str):
    """Analyze and print memory optimization statistics."""
    if not os.path.exists(csv_path):
        print(f"Results file not found: {csv_path}")
        return
        
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    if not data:
        print("No data found in results file")
        return
        
    print(f"\n=== Memory Optimization Analysis ===")
    print(f"Total runs analyzed: {len(data)}")
    
    # Group by strategy
    by_strategy = {}
    for row in data:
        strategy = row['strategy']
        if strategy not in by_strategy:
            by_strategy[strategy] = []
        by_strategy[strategy].append(row)
    
    for strategy, runs in by_strategy.items():
        print(f"\n--- {strategy.upper()} Strategy ---")
        
        total_api_calls = sum(int(r['api_calls_made']) for r in runs)
        total_avoided = sum(int(r['api_calls_avoided']) for r in runs)
        total_tokens = sum(int(r['tokens_used']) for r in runs)
        avg_score = sum(float(r['crisis_score']) for r in runs) / len(runs)
        cache_hit_rate = sum(int(r['cache_hits']) for r in runs) / (sum(int(r['cache_hits']) for r in runs) + sum(int(r['cache_misses']) for r in runs)) if any(int(r['cache_hits']) for r in runs) else 0
        
        print(f"  Runs: {len(runs)}")
        print(f"  Total API calls made: {total_api_calls}")
        print(f"  Total API calls avoided: {total_avoided}")
        print(f"  Cache hit rate: {cache_hit_rate:.2%}")
        print(f"  Total tokens used: {total_tokens}")
        print(f"  Average crisis score: {avg_score:.2f}")
        print(f"  API efficiency: {total_avoided/(total_api_calls + total_avoided):.2%}" if total_api_calls + total_avoided > 0 else "  API efficiency: N/A")

if __name__ == "__main__":
    main()
