import argparse, os, json, yaml
from pathlib import Path
from env.world import CrisisModel
from reasoning.planner import make_plan

def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def run_episode(map_path, seed=42, ticks=200, provider="mock", strategy="react", log_path=None, render=False, memory_enabled=True, api_budget=10000, run_id=None):
    """
    Run a crisis simulation episode with specified strategy and memory optimization.
    
    Args:
        map_path: Path to map configuration
        seed: Random seed for reproducibility 
        ticks: Number of simulation steps
        provider: LLM provider ("gemini", "groq", or "mock")
        strategy: Strategy to use ("react", "reflexion", "cot")
        log_path: Path for logging output
        render: Whether to render visualization
        memory_enabled: Whether to use memory optimization
        api_budget: API token budget for this run
        run_id: Unique run identifier for JSONL logging
    """
    # Set environment variables for LLM and strategy
    os.environ["LLM_PROVIDER"] = provider
    os.environ["STRATEGY"] = strategy
    
    # Generate run_id if not provided
    if run_id is None:
        import time
        run_id = f"{seed}_{Path(map_path).stem}_{provider}_{strategy}_{int(time.time())}"
    
    # Set JSONL logging context
    os.environ["RUN_ID"] = run_id
    
    cfg = load_config(map_path)
    W = cfg.get("width", 20)
    H = cfg.get("height", 20)

    model = CrisisModel(W, H, rng_seed=seed, config=cfg, render=render)

    if log_path is None:
        log_path = f"logs/seed_{seed}_{Path(map_path).stem}_{provider}_{strategy}.txt"
    os.makedirs(Path(log_path).parent, exist_ok=True)
    logf = open(log_path, "w", buffering=1, encoding="utf-8")

    # Initialize memory tracking if enabled
    memory_stats = {
        'api_calls_made': 0,
        'api_calls_avoided': 0,
        'cache_hits': 0,
        'cache_misses': 0,
        'tokens_used': 0,
        'budget_exceeded': False
    }

    transcript = []
    for t in range(ticks):
        # Set current tick for JSONL logging
        os.environ["CURRENT_TICK"] = str(t)
        
        # Check if simulation should stop (all survivors rescued/dead)
        if not model.running:
            print(f"🛑 Simulation terminated early at step {t}")
            break
            
        state = model.summarize_state()
        
        # Use memory-aware planning if enabled
        if memory_enabled:
            try:
                from reasoning.planner import AgentPlanner
                from reasoning.memory_manager import MemoryManager
                
                # Use enhanced planner with memory
                if not hasattr(run_episode, '_planner'):
                    run_episode._planner = AgentPlanner(model, {}, {})
                    run_episode._planner.memory_manager.api_budget = api_budget
                
                plan = run_episode._planner.plan_agent_actions(None, context=state)
                
                # Update memory stats
                planner_stats = run_episode._planner.get_tool_call_stats()
                memory_stats['api_calls_made'] = planner_stats.get('api_calls_made', 0)
                memory_stats['api_calls_avoided'] = planner_stats.get('api_calls_avoided', 0)
                memory_stats['cache_hits'] = planner_stats.get('cache_hits', 0)
                memory_stats['tokens_used'] = run_episode._planner.memory_manager.get_cache_stats().get('total_tokens_used', 0)
                memory_stats['budget_exceeded'] = memory_stats['tokens_used'] > api_budget
                
            except Exception as e:
                print(f"Memory planning failed, using legacy: {e}")
                plan = make_plan(state, strategy=strategy, scratchpad="\\n".join(transcript[-10:]))
        else:
            plan = make_plan(state, strategy=strategy, scratchpad="\\n".join(transcript[-10:]))
        
        cmds = plan.get("commands", [])
        model.set_plan(cmds)

        logf.write(f"=== t={t} ===\\n")
        logf.write(json.dumps({"context": state, "plan": plan})[:2000] + "\\n")
        transcript.append(f"t={t}: plan={plan}")

        model.step()
        
        # Double-check after step execution
        if not model.running:
            print(f"🛑 Simulation auto-terminated after step {t}")
            break

    logf.close()

    # Export metrics using enhanced world metrics system
    try:
        metrics = model.export_metrics_json()
        
        # Add memory system metrics if available
        if memory_stats:
            metrics.update(memory_stats)
        
        # Set current strategy for metrics
        model.current_strategy = strategy.upper()
        
        print(f"📊 Final Metrics Summary:")
        print(f"   Rescued: {metrics['rescued']}")
        print(f"   Deaths: {metrics['deaths']}")
        print(f"   Avg Rescue Time: {metrics['avg_rescue_time']}")
        print(f"   Fires Extinguished: {metrics['fires_extinguished']}")
        print(f"   Roads Cleared: {metrics['roads_cleared']}")
        print(f"   Energy Used: {metrics['energy_used']}")
        print(f"   Tool Calls: {metrics['tool_calls']}")
        print(f"   Invalid JSON: {metrics['invalid_json']}")
        print(f"   Replans: {metrics['replans']}")
        print(f"   Hospital Overflows: {metrics['hospital_overflow_events']}")
        
        return metrics
        
    except Exception as e:
        print(f"⚠️ Metrics export failed, using fallback: {e}")
        
        # Fallback to legacy metrics collection
        hist = model.datacollector.get_model_vars_dataframe()
        rescued = int(hist["rescued"].max() if len(hist) else 0)
        deaths = int(hist["deaths"].max() if len(hist) else 0)
        fires_ext = int(hist["fires_extinguished"].max() if len(hist) else 0)
        roads_cleared = int(hist["roads_cleared"].max() if len(hist) else 0)

        metrics = {
            "rescued": model.rescued,
            "deaths": model.deaths,
            "avg_rescue_time": getattr(model, 'avg_rescue_time', 0.0),
            "fires_extinguished": getattr(model, 'fires_extinguished', fires_ext),
            "roads_cleared": getattr(model, 'roads_cleared', roads_cleared),
            "energy_used": getattr(model, 'energy_used', 0),
            "tool_calls": getattr(model, 'tool_calls', 0),
            "invalid_json": getattr(model, 'invalid_json', 0),
            "replans": getattr(model, 'replans', 0),
            "hospital_overflow_events": getattr(model, 'hospital_overflow_events', 0),
            # Memory system metrics
            **memory_stats
        }
        return metrics

# --- context discovery helper -----------------------------------------------
def build_state(model):
    """
    Try to reuse an existing context/export function from the project.
    Falls back to a minimal dict if none is found.
    """
    candidates = [
        ("crisis.context",        ["export_context", "build_context", "get_context", "to_dict"]),
        ("crisis.utils.context",  ["export_context", "build_context", "get_context", "to_dict"]),
        ("crisis.state",          ["export_context", "build_context", "get_context", "to_dict"]),
        ("crisis.server",         ["export_context", "build_context", "get_context", "serialize", "to_dict"]),
    ]

    # 1) Try known modules/functions
    for mod_name, fn_names in candidates:
        try:
            mod = __import__(mod_name, fromlist=["*"])
        except Exception:
            continue
        for fn in fn_names:
            if hasattr(mod, fn):
                try:
                    return getattr(mod, fn)(model)
                except TypeError:
                    # Some projects expose to_dict() with no args
                    try:
                        return getattr(mod, fn)()
                    except Exception:
                        pass
                except Exception:
                    pass

    # 2) Try a method on the model (if it exists)
    for meth in ("export_context", "to_dict", "as_dict"):
        if hasattr(model, meth) and callable(getattr(model, meth)):
            try:
                return getattr(model, meth)()
            except Exception:
                pass

    # 3) Minimal, safe fallback
    tick = getattr(model, "tick", None)
    if tick is None and hasattr(model, "schedule") and hasattr(model.schedule, "time"):
        tick = model.schedule.time

    agents_list = []
    if hasattr(model, "schedule") and hasattr(model.schedule, "agents"):
        for i, a in enumerate(model.schedule.agents):
            agents_list.append({
                "id": getattr(a, "unique_id", i),
                "type": a.__class__.__name__,
                "pos": getattr(a, "pos", None),
            })

    return {
        "tick": tick,
        "map_name": getattr(model, "map_name", getattr(getattr(model, "map", None), "name", None)),
        "agents": agents_list,
        "resources": getattr(model, "resources", {}),
        "events": getattr(model, "events", []),
        "facts": getattr(model, "facts", {}),
    }
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", type=str, default="configs/map_small.yaml")
    ap.add_argument("--provider", type=str, default="ollama", choices=["mock","groq","gemini","ollama"])
    ap.add_argument("--strategy", type=str, default="react", choices=["react", "reflexion", "cot", "chain_of_thought"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ticks", type=int, default=200)
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()
    
    print(f"🚀 Starting Crisis Simulation with {args.strategy.upper()} strategy using {args.provider.upper()} provider")
    
    m = run_episode(args.map, seed=args.seed, ticks=args.ticks, provider=args.provider, strategy=args.strategy, render=args.render)
    print(json.dumps(m, indent=2))

if __name__ == "__main__":
    main()
