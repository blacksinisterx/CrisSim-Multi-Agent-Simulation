"""
Memory Management System for Crisis Simulation API Optimization

Implements situation hashing, plan caching, and API call tracking to minimize
token usage while maintaining performance across 45 evaluation runs.
"""

import json
import hashlib
import time
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Centralized memory management for crisis simulation with API optimization.
    
    Features:
    - Situation hashing for plan reuse
    - LRU cache with TTL expiry
    - API call tracking and budgeting
    - Cross-episode learning persistence
    """
    
    def __init__(self, 
                 cache_size: int = 500,
                 default_ttl_ticks: int = 5,
                 logs_dir: str = "logs"):
        self.cache_size = cache_size
        self.default_ttl_ticks = default_ttl_ticks
        self.logs_dir = logs_dir
        
        # Plan cache (LRU with TTL)
        self.plan_cache: OrderedDict = OrderedDict()
        
        # API usage tracking
        self.api_events: List[Dict] = []
        self.total_tokens_used = 0
        self.total_calls_made = 0
        
        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Budget enforcement
        self.max_tokens_per_run = 10000  # Conservative per-run limit
        self.max_calls_per_run = 6
        self.current_run_tokens = 0
        self.current_run_calls = 0
        
        # Ensure logs directory exists
        os.makedirs(logs_dir, exist_ok=True)
        
        # Load persistent data
        self._load_persistent_data()
    
    def situation_hash(self, context: Dict[str, Any]) -> str:
        """
        Create canonical hash for situation to enable plan reuse.
        
        Uses tolerant hashing - similar situations get same hash for reuse.
        """
        try:
            # Extract key situation features
            agents = context.get('agents', [])
            hazards = context.get('hazards', [])
            goals = context.get('goals', [])
            tick = context.get('tick', 0)
            map_id = context.get('map_id', 'unknown')
            
            # Create canonical representation
            canonical_agents = []
            for agent in agents:
                canonical_agents.append({
                    'id': agent.get('id', agent.get('agent_id')),
                    'pos': [round(p, 1) for p in agent.get('pos', [0, 0])],
                    'battery_q': round(agent.get('battery_level', 100) / 10) * 10,  # Quantize battery
                    'role': agent.get('kind', agent.get('type', 'unknown'))
                })
            
            canonical_hazards = []
            for hazard in hazards:
                canonical_hazards.append({
                    'type': hazard.get('type', 'unknown'),
                    'pos': [round(p, 1) for p in hazard.get('pos', [0, 0])],
                    'severity': round(hazard.get('severity', 1.0), 1)
                })
            
            canonical_goals = []
            for goal in goals:
                canonical_goals.append({
                    'type': goal.get('type', 'unknown'),
                    'target': goal.get('target', [0, 0]),
                    'urgency': round(goal.get('urgency', 0.5), 1)
                })
            
            # Time bucket for temporal tolerance
            time_bucket = tick // 5  # Group ticks in buckets of 5
            
            # Create canonical string
            canonical = f"{map_id}|agents:{sorted(canonical_agents, key=lambda x: x['id'])}|hazards:{sorted(canonical_hazards, key=lambda x: str(x['pos']))}|goals:{sorted(canonical_goals, key=lambda x: str(x['target']))}|time:{time_bucket}"
            
            # Return SHA-256 hash
            return hashlib.sha256(canonical.encode()).hexdigest()[:16]  # Use first 16 chars
            
        except Exception as e:
            logger.warning(f"Error creating situation hash: {e}")
            # Fallback to simple hash
            return hashlib.sha256(str(context).encode()).hexdigest()[:16]
    
    def get_cached_plan(self, situation_hash: str, current_tick: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached plan if valid and not expired.
        """
        if situation_hash not in self.plan_cache:
            self.cache_misses += 1
            return None
        
        plan_entry = self.plan_cache[situation_hash]
        
        # Check TTL expiry
        if current_tick > plan_entry.get('valid_until_tick', 0):
            logger.debug(f"Plan expired for hash {situation_hash}")
            del self.plan_cache[situation_hash]
            self.cache_misses += 1
            return None
        
        # Move to end (LRU)
        self.plan_cache.move_to_end(situation_hash)
        self.cache_hits += 1
        
        logger.debug(f"Cache hit for situation {situation_hash}")
        return plan_entry
    
    def store_plan(self, 
                   situation_hash: str,
                   actions: List[Dict],
                   current_tick: int,
                   confidence: float = 0.8,
                   token_cost: int = 0,
                   ttl_ticks: Optional[int] = None) -> str:
        """
        Store plan in cache with TTL and metadata.
        """
        if ttl_ticks is None:
            ttl_ticks = self.default_ttl_ticks
        
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{situation_hash[:8]}"
        
        plan_entry = {
            'plan_id': plan_id,
            'situation_hash': situation_hash,
            'actions': actions,
            'valid_until_tick': current_tick + ttl_ticks,
            'confidence': confidence,
            'token_cost': token_cost,
            'created_at': datetime.now().isoformat(),
            'usage_count': 0
        }
        
        # Add to cache
        self.plan_cache[situation_hash] = plan_entry
        self.plan_cache.move_to_end(situation_hash)
        
        # Enforce cache size limit
        while len(self.plan_cache) > self.cache_size:
            oldest = next(iter(self.plan_cache))
            del self.plan_cache[oldest]
        
        logger.debug(f"Stored plan {plan_id} with TTL {ttl_ticks} ticks")
        return plan_id
    
    def increment_plan_usage(self, situation_hash: str, success: bool = True) -> None:
        """
        Track plan usage and success rate.
        """
        if situation_hash in self.plan_cache:
            plan = self.plan_cache[situation_hash]
            plan['usage_count'] = plan.get('usage_count', 0) + 1
            
            # Update confidence based on success
            if success:
                plan['confidence'] = min(1.0, plan['confidence'] * 1.1)
            else:
                plan['confidence'] = max(0.1, plan['confidence'] * 0.9)
    
    def track_api_call(self, 
                      model: str,
                      tokens_in: int,
                      tokens_out: int,
                      reason_tag: str,
                      success: bool = True) -> str:
        """
        Track API usage for budget monitoring.
        """
        call_id = f"call_{len(self.api_events) + 1}_{int(time.time())}"
        
        event = {
            'call_id': call_id,
            'model': model,
            'tokens_in': tokens_in,
            'tokens_out': tokens_out,
            'total_tokens': tokens_in + tokens_out,
            'timestamp': datetime.now().isoformat(),
            'reason_tag': reason_tag,
            'success': success
        }
        
        self.api_events.append(event)
        self.total_tokens_used += tokens_in + tokens_out
        self.total_calls_made += 1
        self.current_run_tokens += tokens_in + tokens_out
        self.current_run_calls += 1
        
        logger.info(f"API call {call_id}: {tokens_in + tokens_out} tokens ({reason_tag})")
        
        return call_id
    
    def can_make_api_call(self) -> Tuple[bool, str]:
        """
        Check if we can make an API call within budget constraints.
        """
        if self.current_run_calls >= self.max_calls_per_run:
            return False, f"Reached max calls per run ({self.max_calls_per_run})"
        
        if self.current_run_tokens >= self.max_tokens_per_run:
            return False, f"Reached max tokens per run ({self.max_tokens_per_run})"
        
        return True, "Within budget"
    
    def reset_run_counters(self) -> None:
        """
        Reset per-run counters for new episode/run.
        """
        self.current_run_tokens = 0
        self.current_run_calls = 0
        logger.info("Reset run counters for new episode")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': hit_rate,
            'cache_size': len(self.plan_cache),
            'max_cache_size': self.cache_size,
            'total_api_calls': self.total_calls_made,
            'total_tokens': self.total_tokens_used,
            'current_run_calls': self.current_run_calls,
            'current_run_tokens': self.current_run_tokens
        }
    
    def should_call_llm(self, 
                       situation_hash: str,
                       current_tick: int,
                       last_plan_success_rate: float = 1.0,
                       high_importance: bool = False) -> Tuple[bool, str]:
        """
        Decide whether to call LLM based on caching and confidence thresholds.
        """
        # Check budget first
        can_call, budget_reason = self.can_make_api_call()
        if not can_call:
            return False, f"Budget constraint: {budget_reason}"
        
        # Check for cached plan
        cached_plan = self.get_cached_plan(situation_hash, current_tick)
        if cached_plan is None:
            return True, "Cache miss - no plan available"
        
        # Check confidence threshold
        confidence_threshold = 0.6
        if high_importance:
            confidence_threshold = 0.8  # Higher threshold for critical situations
        
        if cached_plan['confidence'] < confidence_threshold:
            return True, f"Low confidence ({cached_plan['confidence']:.2f} < {confidence_threshold})"
        
        # Check plan success rate
        if last_plan_success_rate < 0.5:
            return True, f"Poor plan performance ({last_plan_success_rate:.2f})"
        
        # High importance events override caching
        if high_importance:
            return True, "High importance event detected"
        
        return False, f"Using cached plan (confidence: {cached_plan['confidence']:.2f})"
    
    def _load_persistent_data(self) -> None:
        """
        Load persistent memory data from disk.
        """
        try:
            # Load API usage history
            api_file = os.path.join(self.logs_dir, "api_usage.json")
            if os.path.exists(api_file):
                with open(api_file, 'r') as f:
                    data = json.load(f)
                    self.api_events = data.get('events', [])
                    self.total_tokens_used = data.get('total_tokens', 0)
                    self.total_calls_made = data.get('total_calls', 0)
            
            # Load cache statistics
            cache_stats_file = os.path.join(self.logs_dir, "cache_stats.json")
            if os.path.exists(cache_stats_file):
                with open(cache_stats_file, 'r') as f:
                    data = json.load(f)
                    self.cache_hits = data.get('cache_hits', 0)
                    self.cache_misses = data.get('cache_misses', 0)
                    
        except Exception as e:
            logger.warning(f"Error loading persistent data: {e}")
    
    def save_persistent_data(self) -> None:
        """
        Save persistent memory data to disk.
        """
        try:
            # Save API usage
            api_file = os.path.join(self.logs_dir, "api_usage.json")
            with open(api_file, 'w') as f:
                json.dump({
                    'events': self.api_events,
                    'total_tokens': self.total_tokens_used,
                    'total_calls': self.total_calls_made,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
            
            # Save cache statistics
            cache_stats_file = os.path.join(self.logs_dir, "cache_stats.json")
            with open(cache_stats_file, 'w') as f:
                json.dump(self.get_cache_stats(), f, indent=2)
                
            # Save current plan cache
            plan_cache_file = os.path.join(self.logs_dir, "plan_cache.json")
            with open(plan_cache_file, 'w') as f:
                json.dump({
                    'cache': dict(self.plan_cache),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving persistent data: {e}")

# Global memory manager instance
_memory_manager = None

def get_memory_manager(**kwargs) -> MemoryManager:
    """
    Get or create global memory manager instance.
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(**kwargs)
    return _memory_manager

def reset_memory_manager() -> None:
    """
    Reset global memory manager (useful for testing).
    """
    global _memory_manager
    _memory_manager = None
