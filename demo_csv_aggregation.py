#!/usr/bin/env python3
"""
Demo script for the complete CSV aggregation system.
Shows how to run experiments and aggregate results.
"""

import os
import sys
import subprocess

def demo_csv_aggregation():
    """Demonstrate the complete CSV aggregation workflow."""
    print("🎯 CSV Aggregation System Demo")
    print("=" * 50)
    
    print("\n1️⃣ System Overview:")
    print("   • Per-run JSON saving to results/raw/")
    print("   • CSV aggregation to results/agg/summary.csv")
    print("   • Assignment-compliant column structure")
    print("   • Command-line aggregation support")
    
    print("\n2️⃣ Directory Structure:")
    print("   📁 results/")
    print("   ├── 📁 raw/           # Individual JSON files per run")
    print("   └── 📁 agg/           # Aggregated CSV files")
    print("       └── 📄 summary.csv  # Main aggregation file")
    
    print("\n3️⃣ Usage Examples:")
    print("   # Run experiments with automatic JSON saving:")
    print("   python -m eval.harness --n_seeds 5 --maps configs/map_small.yaml")
    print("   ")
    print("   # Aggregate existing JSON files to CSV:")
    print("   python -m eval.harness --aggregate_only")
    print("   ")
    print("   # GUI test with JSON saving:")
    print("   python -m eval.harness --gui --strategy react")
    
    print("\n4️⃣ Assignment Compliance:")
    print("   ✅ Required CSV columns:")
    required_columns = [
        "run_id", "map", "strategy", "seed", "ticks",
        "rescued", "deaths", "avg_rescue_time", "fires_extinguished", "roads_cleared",
        "energy_used", "tool_calls", "invalid_json", "replans", "hospital_overflow_events"
    ]
    for i, col in enumerate(required_columns, 1):
        print(f"      {i:2d}. {col}")
    
    print("\n5️⃣ Current Status:")
    # Check if directories exist
    raw_dir = "results/raw"
    agg_dir = "results/agg"
    summary_csv = "results/agg/summary.csv"
    
    raw_exists = os.path.exists(raw_dir)
    agg_exists = os.path.exists(agg_dir)
    csv_exists = os.path.exists(summary_csv)
    
    print(f"   📁 results/raw/: {'✅' if raw_exists else '❌'}")
    print(f"   📁 results/agg/: {'✅' if agg_exists else '❌'}")
    print(f"   📄 summary.csv: {'✅' if csv_exists else '❌'}")
    
    if raw_exists:
        json_files = [f for f in os.listdir(raw_dir) if f.endswith('.json')]
        print(f"   📊 JSON files: {len(json_files)}")
    
    if csv_exists:
        import csv
        with open(summary_csv, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"   📊 CSV rows: {len(rows)}")
        
        if rows:
            print(f"   📊 Sample data:")
            sample_row = rows[0]
            print(f"      run_id: {sample_row['run_id']}")
            print(f"      strategy: {sample_row['strategy']}")
            print(f"      rescued: {sample_row['rescued']}")
            print(f"      deaths: {sample_row['deaths']}")
    
    print("\n6️⃣ Implementation Details:")
    print("   🔧 save_run_json() - Saves individual run metrics to JSON")
    print("   🔧 aggregate_to_csv() - Aggregates all JSONs to summary CSV")
    print("   🔧 Enhanced eval/harness.py with automatic JSON saving")
    print("   🔧 Command-line --aggregate_only mode for post-processing")
    
    print("\n7️⃣ Integration with Assignment Phases:")
    print("   ✅ Phase 2A: Enhanced metrics collection (completed)")
    print("   ✅ Phase 2B: CSV aggregation system (completed)")
    print("   ⏳ Phase 3A: 45-run experiment suite (ready)")
    print("   ⏳ Phase 3B: Plot generation system (ready)")
    
    print("\n🎉 CSV Aggregation System is ready for full assignment experiments!")
    print("=" * 50)

def show_sample_data():
    """Show sample of current data if available."""
    csv_path = "results/agg/summary.csv"
    if os.path.exists(csv_path):
        print("\n📊 Sample Data from summary.csv:")
        print("-" * 40)
        
        import csv
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if rows:
            # Show first few rows
            for i, row in enumerate(rows[:3]):
                print(f"Run {i+1}: {row['run_id']}")
                print(f"  Map: {row['map']}, Strategy: {row['strategy']}")
                print(f"  Rescued: {row['rescued']}, Deaths: {row['deaths']}")
                print(f"  Energy used: {row['energy_used']}, Tool calls: {row['tool_calls']}")
                print()
        else:
            print("No data rows found in CSV")
    else:
        print("\n📊 No summary.csv found - run some experiments first!")

if __name__ == "__main__":
    demo_csv_aggregation()
    show_sample_data()
