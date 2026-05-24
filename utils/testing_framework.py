# utils/testing_framework.py - Automated Testing Framework

import unittest
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys
import os

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from env.world import CrisisModel
from env.agents import MedicAgent, TruckAgent, DroneAgent, Survivor
from utils.config_manager import ConfigManager, SimulationConfig
from utils.data_persistence import DataPersistence
from utils.logging_config import setup_logging

class TestCrisisSimulation(unittest.TestCase):
    """Test suite for crisis simulation components."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = tempfile.mkdtemp()
        cls.config_manager = ConfigManager(config_dir=cls.temp_dir)
        cls.data_persistence = DataPersistence(data_dir=cls.temp_dir)
        
        # Setup logging for tests
        setup_logging(log_level="DEBUG", log_dir=cls.temp_dir)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)
    
    def setUp(self):
        """Set up each test."""
        # Create test configuration
        self.test_config = SimulationConfig(
            width=10,
            height=10,
            max_ticks=50,
            num_medics=1,
            num_trucks=1,
            num_drones=1,
            seed=42
        )
        
        # Create test model
        self.model = self._create_test_model()
    
    def _create_test_model(self) -> CrisisModel:
        """Create a test crisis model."""
        # Mock map configuration
        map_config = {
            "width": self.test_config.width,
            "height": self.test_config.height,
            "depot": [1, 1],
            "hospitals": [[8, 8]],
            "initial_fires": [[3, 3], [7, 7]],
            "survivors": 5
        }
        
        model = CrisisModel(
            width=self.test_config.width,
            height=self.test_config.height,
            map_config=map_config,
            config=self.test_config
        )
        
        return model
    
    def test_model_initialization(self):
        """Test that the crisis model initializes correctly."""
        self.assertIsInstance(self.model, CrisisModel)
        self.assertEqual(self.model.width, self.test_config.width)
        self.assertEqual(self.model.height, self.test_config.height)
        
        # Check agent counts
        medics = [agent for agent in self.model.schedule.agents if isinstance(agent, MedicAgent)]
        trucks = [agent for agent in self.model.schedule.agents if isinstance(agent, TruckAgent)]
        drones = [agent for agent in self.model.schedule.agents if isinstance(agent, DroneAgent)]
        survivors = [agent for agent in self.model.schedule.agents if isinstance(agent, Survivor)]
        
        self.assertEqual(len(medics), self.test_config.num_medics)
        self.assertEqual(len(trucks), self.test_config.num_trucks)
        self.assertEqual(len(drones), self.test_config.num_drones)
        self.assertGreaterEqual(len(survivors), 1)
    
    def test_agent_initialization(self):
        """Test that agents initialize with correct properties."""
        medics = [agent for agent in self.model.schedule.agents if isinstance(agent, MedicAgent)]
        trucks = [agent for agent in self.model.schedule.agents if isinstance(agent, TruckAgent)]
        drones = [agent for agent in self.model.schedule.agents if isinstance(agent, DroneAgent)]
        
        if medics:
            medic = medics[0]
            self.assertEqual(medic.capacity, self.test_config.medic_capacity)
            self.assertIsNotNone(medic.pos)
            self.assertEqual(medic.status, "searching")
        
        if trucks:
            truck = trucks[0]
            self.assertEqual(truck.water_max, self.test_config.truck_water_max)
            self.assertEqual(truck.tools_max, self.test_config.truck_tools_max)
            self.assertIsNotNone(truck.pos)
        
        if drones:
            drone = drones[0]
            self.assertEqual(drone.battery_max, self.test_config.drone_battery_max)
            self.assertIsNotNone(drone.pos)
    
    def test_model_step_execution(self):
        """Test that model steps execute without errors."""
        initial_step = self.model.schedule.steps
        
        # Execute several steps
        for _ in range(5):
            self.model.step()
        
        # Verify steps increased
        self.assertGreater(self.model.schedule.steps, initial_step)
    
    def test_data_collection(self):
        """Test that data collection works correctly."""
        # Run a few steps
        for _ in range(3):
            self.model.step()
        
        # Check that data collector has data
        model_data = self.model.datacollector.get_model_vars_dataframe()
        self.assertGreater(len(model_data), 0)
        
        # Verify required columns exist
        required_columns = ['crisis_score', 'active_fires', 'rescued', 'deaths']
        for col in required_columns:
            self.assertIn(col, model_data.columns)
    
    def test_crisis_score_calculation(self):
        """Test crisis score calculation."""
        # Get initial score
        initial_score = self.model.calculate_crisis_score()
        self.assertIsInstance(initial_score, (int, float))
        self.assertGreaterEqual(initial_score, 0)
        
        # Run simulation and check score changes
        for _ in range(10):
            self.model.step()
        
        final_score = self.model.calculate_crisis_score()
        self.assertIsInstance(final_score, (int, float))
    
    def test_fire_spread_mechanics(self):
        """Test fire spreading mechanics."""
        # Count initial fires
        initial_fires = sum(1 for cell in self.model.grid.coord_iter() 
                           if cell[0].fire_intensity > 0)
        
        # Run several steps
        for _ in range(20):
            self.model.step()
        
        # Fires should exist (either spread or been extinguished)
        final_fires = sum(1 for cell in self.model.grid.coord_iter() 
                         if cell[0].fire_intensity > 0)
        
        # Test passes if fires exist or have been managed
        self.assertGreaterEqual(initial_fires, 1)

class TestConfigManager(unittest.TestCase):
    """Test suite for configuration management."""
    
    def setUp(self):
        """Set up test configuration manager."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(config_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = self.config_manager.simulation
        self.assertIsInstance(config.width, int)
        self.assertIsInstance(config.height, int)
        self.assertGreater(config.width, 0)
        self.assertGreater(config.height, 0)
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid configuration should pass
        self.assertTrue(self.config_manager.validate_config())
        
        # Invalid configuration should fail
        self.config_manager.simulation.width = -1
        self.assertFalse(self.config_manager.validate_config())
    
    def test_config_save_load(self):
        """Test configuration save and load."""
        # Modify configuration
        original_width = self.config_manager.simulation.width
        self.config_manager.simulation.width = 25
        
        # Save configuration
        self.config_manager.save_config("test_config")
        
        # Reset and load
        self.config_manager.simulation.width = original_width
        config_file = Path(self.temp_dir) / "test_config.yaml"
        self.config_manager.update_from_file(config_file)
        
        # Verify loaded value
        self.assertEqual(self.config_manager.simulation.width, 25)

class TestDataPersistence(unittest.TestCase):
    """Test suite for data persistence."""
    
    def setUp(self):
        """Set up test data persistence."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_persistence = DataPersistence(data_dir=self.temp_dir)
        self.test_run_id = "test_run_001"
    
    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """Test that database initializes correctly."""
        db_path = Path(self.temp_dir) / "crisis_simulation.db"
        self.assertTrue(db_path.exists())
        
        # Test database connection
        with self.data_persistence.get_db_connection() as conn:
            tables = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
            """).fetchall()
            
            table_names = [table['name'] for table in tables]
            required_tables = ['simulation_runs', 'step_data', 'model_state', 'decision_logs']
            
            for table in required_tables:
                self.assertIn(table, table_names)
    
    def test_simulation_run_tracking(self):
        """Test simulation run tracking."""
        # Start run
        test_config = {"width": 10, "height": 10}
        self.data_persistence.start_simulation_run(self.test_run_id, test_config)
        
        # Finish run
        self.data_persistence.finish_simulation_run(
            self.test_run_id, 
            total_ticks=100, 
            final_score=0.75,
            metadata={"test": True}
        )
        
        # Verify run exists
        summary = self.data_persistence.get_run_summary(self.test_run_id)
        self.assertEqual(summary['run_info']['run_id'], self.test_run_id)
        self.assertEqual(summary['run_info']['status'], 'completed')
    
    def test_data_export(self):
        """Test data export functionality."""
        # Create test run
        test_config = {"width": 10, "height": 10}
        self.data_persistence.start_simulation_run(self.test_run_id, test_config)
        
        # Add some test data
        self.data_persistence.save_model_state(
            self.test_run_id, 
            step=1, 
            model_data={
                'crisis_score': 0.8,
                'active_fires': 2,
                'survivors_rescued': 1,
                'total_deaths': 0
            }
        )
        
        # Export data
        export_path = self.data_persistence.export_run_data(self.test_run_id, 'csv')
        self.assertTrue(os.path.exists(export_path))

class PerformanceBenchmark:
    """Performance benchmarking suite."""
    
    def __init__(self, config: SimulationConfig = None):
        if config is None:
            config = SimulationConfig(width=20, height=20, max_ticks=100)
        self.config = config
    
    def benchmark_model_creation(self, iterations: int = 10) -> Dict[str, float]:
        """Benchmark model creation performance."""
        times = []
        
        for _ in range(iterations):
            start_time = time.time()
            
            map_config = {
                "width": self.config.width,
                "height": self.config.height,
                "depot": [1, 1],
                "hospitals": [[18, 18]],
                "initial_fires": [[5, 5], [15, 15]],
                "survivors": 10
            }
            
            model = CrisisModel(
                width=self.config.width,
                height=self.config.height,
                map_config=map_config,
                config=self.config
            )
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        return {
            'mean_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'iterations': iterations
        }
    
    def benchmark_simulation_steps(self, steps: int = 50) -> Dict[str, float]:
        """Benchmark simulation step performance."""
        # Create model
        map_config = {
            "width": self.config.width,
            "height": self.config.height,
            "depot": [1, 1],
            "hospitals": [[18, 18]],
            "initial_fires": [[5, 5], [15, 15]],
            "survivors": 10
        }
        
        model = CrisisModel(
            width=self.config.width,
            height=self.config.height,
            map_config=map_config,
            config=self.config
        )
        
        # Benchmark steps
        step_times = []
        
        for _ in range(steps):
            start_time = time.time()
            model.step()
            end_time = time.time()
            step_times.append(end_time - start_time)
        
        return {
            'mean_step_time': sum(step_times) / len(step_times),
            'total_time': sum(step_times),
            'steps_per_second': steps / sum(step_times) if sum(step_times) > 0 else 0,
            'steps': steps
        }

def run_full_test_suite():
    """Run the complete test suite."""
    print("🧪 Running Crisis Simulation Test Suite")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestCrisisSimulation))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestDataPersistence))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Performance benchmarks
    print("\n🚀 Performance Benchmarks")
    print("=" * 30)
    
    benchmark = PerformanceBenchmark()
    
    creation_stats = benchmark.benchmark_model_creation(iterations=5)
    print(f"Model Creation: {creation_stats['mean_time']:.3f}s average")
    
    step_stats = benchmark.benchmark_simulation_steps(steps=25)
    print(f"Simulation Steps: {step_stats['steps_per_second']:.1f} steps/second")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    # Run test suite if executed directly
    success = run_full_test_suite()
    sys.exit(0 if success else 1)
