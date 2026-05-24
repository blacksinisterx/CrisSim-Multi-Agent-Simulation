# planner.py - Agent planning system with strategy integration and memory optimization

import json
import time
import os
import logging
from typing import Dict, List, Any, Optional

# Import memory system
from reasoning.memory_manager import MemoryManager
from reasoning.llm_client import llm_call_with_cache, build_context_summary

# Set up logging for planner
logging.basicConfig(level=logging.INFO)
planner_logger = logging.getLogger('Planner')

class AgentPlanner:
    """Agent planner with multiple reasoning strategies and memory optimization."""
    
    def __init__(self, world, llm_config, strategy_config):
        self.world = world
        self.llm_config = llm_config
        self.strategy_config = strategy_config
        
        # Initialize memory manager for API optimization
        self.memory_manager = MemoryManager()
        
        self.tool_call_stats = {
            'total': 0,
            'failed': 0,
            'successful': 0,
            'react_calls': 0,
            'reflexion_calls': 0,
            'cot_calls': 0,
            'cache_hits': 0,
            'api_calls_made': 0,
            'api_calls_avoided': 0
        }
        
        # Get active strategy from environment or config
        self.active_strategy = os.getenv("STRATEGY", "react").lower()
        planner_logger.info(f"Planner initialized with strategy: {self.active_strategy}, Memory enabled: True")
        
    def get_tool_call_stats(self):
        """Get comprehensive tool call and memory statistics."""
        stats = self.tool_call_stats.copy()
        stats.update(self.memory_manager.get_cache_stats())
        return stats
        
    def plan_agent_actions(self, agent=None, context: str = "") -> Dict[str, Any]:
        """Plan actions for a specific agent using memory-optimized strategy."""
        self.tool_call_stats['total'] += 1
        
        try:
            # Build context summary for memory system
            world_state = {
                'agents': [vars(a) for a in self.world.agents] if hasattr(self.world, 'agents') else [],
                'hazards': getattr(self.world, 'hazards', []),
                'goals': getattr(self.world, 'goals', []),
                'tick': getattr(self.world, 'current_tick', 0)
            }
            
            # Use memory-aware LLM calling
            plan_result = llm_call_with_cache(
                context={
                    'agent_id': getattr(agent, 'id', 'unknown') if agent else 'multi_agent',
                    'world_state': world_state,
                    'context': context,
                    'strategy': self.active_strategy,
                    'tick': getattr(self.world, 'current_tick', 0)
                },
                strategy=self.active_strategy,
                high_importance=False
            )
            
            # Update statistics
            if plan_result.get('from_cache', False):
                self.tool_call_stats['cache_hits'] += 1
                self.tool_call_stats['api_calls_avoided'] += 1
            else:
                self.tool_call_stats['api_calls_made'] += 1
            
            # Update strategy-specific stats
            if self.active_strategy == "react":
                self.tool_call_stats['react_calls'] += 1
            elif self.active_strategy == "reflexion":
                self.tool_call_stats['reflexion_calls'] += 1
            elif self.active_strategy in ["cot", "chain_of_thought"]:
                self.tool_call_stats['cot_calls'] += 1
                
            self.tool_call_stats['successful'] += 1
            return plan_result.get('plan', {"commands": []})
            
        except Exception as e:
            self.tool_call_stats['failed'] += 1
            planner_logger.error(f"Memory-aware planning failed for strategy {self.active_strategy}: {e}")
            
            # NO FALLBACK - return error  
            planner_logger.error(f"Memory planning failed: {e}")
            return {"commands": [], "error": f"MEMORY_PLANNING_FAILED: {str(e)}", "success": False}
        
    # DEAD CODE - fallback functions removed per user requirement
    # _legacy_plan_fallback and _mock_plan functions eliminated
        else:
            return {"commands": ["wait", "request_assistance"]}
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get detailed memory system statistics."""
        return self.memory_manager.get_cache_stats()

def make_plan(context, strategy="react", scratchpad=""):
    """
    Legacy planning function for fallback compatibility.
    New code should use AgentPlanner.plan_agent_actions() with memory optimization.
    """
    try:
        if strategy == "react":
            from reasoning.react import react_plan
            kind, payload = react_plan(context, scratchpad=scratchpad)
        elif strategy == "reflexion":
            from reasoning.reflexion import reflexion_plan
            kind, payload = reflexion_plan(context, scratchpad=scratchpad)
        elif strategy == "cot" or strategy == "chain_of_thought":
            from reasoning.cot import cot_plan
            kind, payload = cot_plan(context, scratchpad=scratchpad)
        else:
            # Default to ReAct for backward compatibility
            planner_logger.warning(f"Unknown strategy '{strategy}', defaulting to ReAct")
            from reasoning.react import react_plan
            kind, payload = react_plan(context, scratchpad=scratchpad)
        
        if kind == "final":
            try:
                return json.loads(payload)
            except Exception as e:
                planner_logger.error(f"Failed to parse strategy response: {e}")
                return {"commands": []}
        else:
            # For future extension with multi-step planning
            planner_logger.warning(f"Non-final plan kind '{kind}' not yet supported")
            return {"commands": []}
            
    except Exception as e:
        planner_logger.error(f"Strategy {strategy} failed: {e}")
        return {"commands": []}
