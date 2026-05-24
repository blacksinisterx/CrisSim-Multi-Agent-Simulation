# logging.py - Enhanced logging and debugging tools for Crisis Simulation

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

class CrisisLogger:
    """Enhanced logging system for crisis simulation debugging and analysis."""
    
    def __init__(self, name: str = "crisis-sim", log_dir: str = "logs"):
        self.name = name
        self.log_dir = log_dir
        
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup main logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # Metrics storage
        self.metrics_history = []
        self.decision_log = []
        self.agent_actions = []
        
    def log_step(self, step: int, model_state: Dict[str, Any]):
        """Log model state at each step."""
        self.logger.debug(f"Step {step}: {json.dumps(model_state, indent=2)}")
        
        # Store metrics for analysis
        self.metrics_history.append({
            'step': step,
            'timestamp': datetime.now().isoformat(),
            **model_state
        })
        
    def log_agent_decision(self, agent_id: str, strategy: str, decision: Dict[str, Any], 
                          context: Dict[str, Any], result: Optional[str] = None):
        """Log agent decision making process."""
        decision_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_id,
            'strategy': strategy,
            'decision': decision,
            'context': context,
            'result': result
        }
        
        self.decision_log.append(decision_entry)
        self.logger.info(f"Agent {agent_id} ({strategy}): {decision} -> {result}")
        
    def log_tool_call(self, agent_id: str, tool_name: str, parameters: Dict[str, Any], 
                     result: Dict[str, Any], success: bool = True):
        """Log tool calling activities."""
        tool_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_id,
            'tool_name': tool_name,
            'parameters': parameters,
            'result': result,
            'success': success
        }
        
        self.agent_actions.append(tool_entry)
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"Tool Call {status}: {agent_id} -> {tool_name}({parameters})")
        
    def log_crisis_event(self, event_type: str, details: Dict[str, Any]):
        """Log major crisis events (fires, rescues, deaths)."""
        self.logger.warning(f"CRISIS EVENT - {event_type}: {details}")
        
    def save_metrics_csv(self, filename: Optional[str] = None):
        """Save metrics history to CSV file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.csv"
            
        filepath = os.path.join(self.log_dir, filename)
        
        if self.metrics_history:
            df = pd.DataFrame(self.metrics_history)
            df.to_csv(filepath, index=False)
            self.logger.info(f"Metrics saved to {filepath}")
        else:
            self.logger.warning("No metrics data to save")
            
    def save_decisions_json(self, filename: Optional[str] = None):
        """Save decision log to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"decisions_{timestamp}.json"
            
        filepath = os.path.join(self.log_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(self.decision_log, f, indent=2)
            
        self.logger.info(f"Decision log saved to {filepath}")
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Generate performance summary from logged data."""
        if not self.metrics_history:
            return {"error": "No metrics data available"}
            
        df = pd.DataFrame(self.metrics_history)
        
        summary = {
            "simulation_length": len(df),
            "final_rescued": df['rescued'].iloc[-1] if 'rescued' in df.columns else 0,
            "final_deaths": df['deaths'].iloc[-1] if 'deaths' in df.columns else 0,
            "final_fires_extinguished": df['fires_extinguished'].iloc[-1] if 'fires_extinguished' in df.columns else 0,
            "final_crisis_score": df['crisis_score'].iloc[-1] if 'crisis_score' in df.columns else 0,
            "avg_crisis_score": df['crisis_score'].mean() if 'crisis_score' in df.columns else 0,
            "total_decisions": len(self.decision_log),
            "total_tool_calls": len(self.agent_actions),
            "successful_tool_calls": len([a for a in self.agent_actions if a['success']])
        }
        
        return summary


# Global logger instance for convenience
crisis_logger = CrisisLogger()

def log_step(step: int, model_state: Dict[str, Any]):
    """Convenience function for step logging."""
    crisis_logger.log_step(step, model_state)

def log_agent_decision(agent_id: str, strategy: str, decision: Dict[str, Any], 
                      context: Dict[str, Any], result: Optional[str] = None):
    """Convenience function for decision logging."""
    crisis_logger.log_agent_decision(agent_id, strategy, decision, context, result)

def log_tool_call(agent_id: str, tool_name: str, parameters: Dict[str, Any], 
                 result: Dict[str, Any], success: bool = True):
    """Convenience function for tool call logging."""
    crisis_logger.log_tool_call(agent_id, tool_name, parameters, result, success)

def log_crisis_event(event_type: str, details: Dict[str, Any]):
    """Convenience function for crisis event logging."""
    crisis_logger.log_crisis_event(event_type, details)
