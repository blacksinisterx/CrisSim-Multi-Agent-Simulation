# utils/data_persistence.py - Data Persistence Layer

import csv
import json
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pickle
import gzip
from contextlib import contextmanager

class DataPersistence:
    """Centralized data persistence system for crisis simulation."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.data_dir / "runs").mkdir(exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "exports").mkdir(exist_ok=True)
        (self.data_dir / "checkpoints").mkdir(exist_ok=True)
        
        # Initialize SQLite database
        self.db_path = self.data_dir / "crisis_simulation.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with necessary tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Simulation runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    config TEXT NOT NULL,
                    status TEXT DEFAULT 'running',
                    total_ticks INTEGER DEFAULT 0,
                    final_score REAL DEFAULT 0.0,
                    metadata TEXT
                )
            """)
            
            # Step data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS step_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step INTEGER NOT NULL,
                    agent_id TEXT,
                    agent_type TEXT,
                    position_x INTEGER,
                    position_y INTEGER,
                    action TEXT,
                    status TEXT,
                    metrics TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
                )
            """)
            
            # Model state table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step INTEGER NOT NULL,
                    crisis_score REAL,
                    active_fires INTEGER,
                    survivors_rescued INTEGER,
                    total_deaths INTEGER,
                    state_data TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
                )
            """)
            
            # Decision logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decision_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step INTEGER NOT NULL,
                    agent_id TEXT,
                    reasoning_strategy TEXT,
                    decision TEXT,
                    confidence REAL,
                    execution_time REAL,
                    success BOOLEAN,
                    metadata TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def start_simulation_run(self, run_id: str, config: Dict[str, Any]) -> None:
        """Record the start of a new simulation run."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO simulation_runs 
                (run_id, timestamp, config, status)
                VALUES (?, ?, ?, ?)
            """, (
                run_id,
                datetime.now().isoformat(),
                json.dumps(config),
                'running'
            ))
            conn.commit()
    
    def finish_simulation_run(self, run_id: str, total_ticks: int, 
                             final_score: float, metadata: Dict[str, Any] = None) -> None:
        """Mark simulation run as completed and store final results."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE simulation_runs 
                SET status = ?, total_ticks = ?, final_score = ?, metadata = ?
                WHERE run_id = ?
            """, (
                'completed',
                total_ticks,
                final_score,
                json.dumps(metadata) if metadata else None,
                run_id
            ))
            conn.commit()
    
    def save_step_data(self, run_id: str, step: int, agent_data: List[Dict[str, Any]]) -> None:
        """Save agent data for a specific step."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            for agent in agent_data:
                cursor.execute("""
                    INSERT INTO step_data 
                    (run_id, step, agent_id, agent_type, position_x, position_y, 
                     action, status, metrics, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    step,
                    agent.get('agent_id'),
                    agent.get('agent_type'),
                    agent.get('position', {}).get('x'),
                    agent.get('position', {}).get('y'),
                    agent.get('action'),
                    agent.get('status'),
                    json.dumps(agent.get('metrics', {})),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
    
    def save_model_state(self, run_id: str, step: int, model_data: Dict[str, Any]) -> None:
        """Save model state for a specific step."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_state 
                (run_id, step, crisis_score, active_fires, survivors_rescued, 
                 total_deaths, state_data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                step,
                model_data.get('crisis_score'),
                model_data.get('active_fires'),
                model_data.get('survivors_rescued'),
                model_data.get('total_deaths'),
                json.dumps(model_data),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def save_decision_log(self, run_id: str, step: int, decision_data: Dict[str, Any]) -> None:
        """Save decision-making logs."""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO decision_logs 
                (run_id, step, agent_id, reasoning_strategy, decision, 
                 confidence, execution_time, success, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                step,
                decision_data.get('agent_id'),
                decision_data.get('reasoning_strategy'),
                decision_data.get('decision'),
                decision_data.get('confidence'),
                decision_data.get('execution_time'),
                decision_data.get('success'),
                json.dumps(decision_data.get('metadata', {})),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def export_run_data(self, run_id: str, format: str = 'csv') -> str:
        """Export simulation run data to specified format."""
        export_dir = self.data_dir / "exports" / run_id
        export_dir.mkdir(exist_ok=True)
        
        if format.lower() == 'csv':
            return self._export_to_csv(run_id, export_dir)
        elif format.lower() == 'json':
            return self._export_to_json(run_id, export_dir)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_to_csv(self, run_id: str, export_dir: Path) -> str:
        """Export run data to CSV files."""
        with self.get_db_connection() as conn:
            # Export step data
            df_steps = pd.read_sql_query("""
                SELECT * FROM step_data WHERE run_id = ?
                ORDER BY step, agent_id
            """, conn, params=[run_id])
            df_steps.to_csv(export_dir / "step_data.csv", index=False)
            
            # Export model state
            df_model = pd.read_sql_query("""
                SELECT * FROM model_state WHERE run_id = ?
                ORDER BY step
            """, conn, params=[run_id])
            df_model.to_csv(export_dir / "model_state.csv", index=False)
            
            # Export decision logs
            df_decisions = pd.read_sql_query("""
                SELECT * FROM decision_logs WHERE run_id = ?
                ORDER BY step, timestamp
            """, conn, params=[run_id])
            df_decisions.to_csv(export_dir / "decisions.csv", index=False)
        
        return str(export_dir)
    
    def _export_to_json(self, run_id: str, export_dir: Path) -> str:
        """Export run data to JSON format."""
        with self.get_db_connection() as conn:
            # Get run metadata
            run_info = conn.execute("""
                SELECT * FROM simulation_runs WHERE run_id = ?
            """, [run_id]).fetchone()
            
            if not run_info:
                raise ValueError(f"Run {run_id} not found")
            
            # Compile all data
            export_data = {
                'run_info': dict(run_info),
                'step_data': [],
                'model_state': [],
                'decisions': []
            }
            
            # Get step data
            steps = conn.execute("""
                SELECT * FROM step_data WHERE run_id = ?
                ORDER BY step, agent_id
            """, [run_id]).fetchall()
            export_data['step_data'] = [dict(step) for step in steps]
            
            # Get model state
            states = conn.execute("""
                SELECT * FROM model_state WHERE run_id = ?
                ORDER BY step
            """, [run_id]).fetchall()
            export_data['model_state'] = [dict(state) for state in states]
            
            # Get decisions
            decisions = conn.execute("""
                SELECT * FROM decision_logs WHERE run_id = ?
                ORDER BY step, timestamp
            """, [run_id]).fetchall()
            export_data['decisions'] = [dict(decision) for decision in decisions]
        
        # Save to compressed JSON
        export_file = export_dir / f"{run_id}_complete.json.gz"
        with gzip.open(export_file, 'wt', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        return str(export_file)
    
    def create_checkpoint(self, run_id: str, step: int, model_state: Any) -> str:
        """Create a checkpoint for resuming simulation."""
        checkpoint_file = self.data_dir / "checkpoints" / f"{run_id}_step_{step}.pkl.gz"
        
        checkpoint_data = {
            'run_id': run_id,
            'step': step,
            'model_state': model_state,
            'timestamp': datetime.now().isoformat()
        }
        
        with gzip.open(checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint_data, f)
        
        return str(checkpoint_file)
    
    def load_checkpoint(self, checkpoint_file: str) -> Dict[str, Any]:
        """Load checkpoint data for resuming simulation."""
        with gzip.open(checkpoint_file, 'rb') as f:
            return pickle.load(f)
    
    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """Get summary statistics for a simulation run."""
        with self.get_db_connection() as conn:
            # Basic run info
            run_info = conn.execute("""
                SELECT * FROM simulation_runs WHERE run_id = ?
            """, [run_id]).fetchone()
            
            if not run_info:
                return {}
            
            # Get final statistics
            final_state = conn.execute("""
                SELECT * FROM model_state 
                WHERE run_id = ? 
                ORDER BY step DESC LIMIT 1
            """, [run_id]).fetchone()
            
            # Count decisions by strategy
            decision_stats = conn.execute("""
                SELECT reasoning_strategy, COUNT(*) as count,
                       AVG(confidence) as avg_confidence,
                       AVG(execution_time) as avg_time
                FROM decision_logs 
                WHERE run_id = ?
                GROUP BY reasoning_strategy
            """, [run_id]).fetchall()
            
            return {
                'run_info': dict(run_info),
                'final_state': dict(final_state) if final_state else {},
                'decision_stats': [dict(stat) for stat in decision_stats]
            }
    
    def cleanup_old_runs(self, days_old: int = 30) -> int:
        """Clean up old simulation runs and associated data."""
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff_date).isoformat()
        
        with self.get_db_connection() as conn:
            # Get runs to delete
            old_runs = conn.execute("""
                SELECT run_id FROM simulation_runs 
                WHERE timestamp < ? AND status = 'completed'
            """, [cutoff_iso]).fetchall()
            
            old_run_ids = [row['run_id'] for row in old_runs]
            
            if not old_run_ids:
                return 0
            
            # Delete associated data
            placeholders = ','.join('?' * len(old_run_ids))
            
            conn.execute(f"""
                DELETE FROM decision_logs WHERE run_id IN ({placeholders})
            """, old_run_ids)
            
            conn.execute(f"""
                DELETE FROM model_state WHERE run_id IN ({placeholders})
            """, old_run_ids)
            
            conn.execute(f"""
                DELETE FROM step_data WHERE run_id IN ({placeholders})
            """, old_run_ids)
            
            conn.execute(f"""
                DELETE FROM simulation_runs WHERE run_id IN ({placeholders})
            """, old_run_ids)
            
            conn.commit()
            
            return len(old_run_ids)

# Global data persistence instance
data_persistence = DataPersistence()

def get_data_persistence() -> DataPersistence:
    """Get the global data persistence instance."""
    return data_persistence
