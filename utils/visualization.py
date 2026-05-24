# visualization.py - Enhanced visualization and plotting utilities

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
from dataclasses import asdict

from utils.experiment_runner import ExperimentResult

# Set style for professional plots
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("Warning: Matplotlib/Seaborn not available. Plotting functions disabled.")

import pandas as pd

class ResultsVisualizer:
    """Advanced visualization for experiment results and analysis."""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.plots_dir = self.results_dir / "plots"
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        
        # Color schemes
        self.strategy_colors = {
            'react': '#2E86AB',
            'reflexion': '#A23B72', 
            'cot': '#F18F01',
            'mock': '#C73E1D'
        }
        
    def plot_strategy_comparison(self, results: List[ExperimentResult], 
                               save_path: Optional[str] = None) -> plt.Figure:
        """Create comprehensive strategy comparison plots."""
        if not PLOTTING_AVAILABLE:
            print("Plotting not available. Install matplotlib and seaborn.")
            return None
        # Convert to DataFrame
        df = pd.DataFrame([asdict(r) for r in results if r.success])
        
        if df.empty:
            print("No successful results to plot")
            return None
            
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Strategy Performance Comparison', fontsize=16, fontweight='bold')
        
        # 1. Crisis Score Distribution
        ax1 = axes[0, 0]
        strategy_groups = df.groupby('strategy')['crisis_score']
        box_data = [group.values for name, group in strategy_groups]
        box_labels = [name for name, _ in strategy_groups]
        
        bp1 = ax1.boxplot(box_data, labels=box_labels, patch_artist=True)
        for patch, strategy in zip(bp1['boxes'], box_labels):
            patch.set_facecolor(self.strategy_colors.get(strategy, '#cccccc'))
            patch.set_alpha(0.7)
            
        ax1.set_title('Crisis Score Distribution by Strategy')
        ax1.set_ylabel('Crisis Score')
        ax1.grid(True, alpha=0.3)
        
        # 2. Rescue Rate Comparison
        ax2 = axes[0, 1]
        rescue_means = df.groupby('strategy')['rescue_rate'].mean()
        rescue_stds = df.groupby('strategy')['rescue_rate'].std()
        
        bars = ax2.bar(rescue_means.index, rescue_means.values, 
                      yerr=rescue_stds.values, capsize=5, alpha=0.8,
                      color=[self.strategy_colors.get(s, '#cccccc') for s in rescue_means.index])
        
        ax2.set_title('Average Rescue Rate by Strategy')
        ax2.set_ylabel('Rescue Rate')
        ax2.set_ylim(0, 1.0)
        ax2.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar, mean, std in zip(bars, rescue_means.values, rescue_stds.values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + std + 0.01,
                    f'{mean:.2%}', ha='center', va='bottom', fontweight='bold')
        
        # 3. Execution Time vs Performance
        ax3 = axes[1, 0]
        for strategy in df['strategy'].unique():
            strategy_data = df[df['strategy'] == strategy]
            ax3.scatter(strategy_data['execution_time'], strategy_data['crisis_score'], 
                       label=strategy, alpha=0.7, s=50,
                       color=self.strategy_colors.get(strategy, '#cccccc'))
                       
        ax3.set_xlabel('Execution Time (seconds)')
        ax3.set_ylabel('Crisis Score')
        ax3.set_title('Performance vs Execution Time')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Tool Usage Analysis
        ax4 = axes[1, 1]
        if 'total_tool_calls' in df.columns:
            tool_means = df.groupby('strategy')['total_tool_calls'].mean()
            tool_stds = df.groupby('strategy')['total_tool_calls'].std()
            
            bars = ax4.bar(tool_means.index, tool_means.values,
                          yerr=tool_stds.values, capsize=5, alpha=0.8,
                          color=[self.strategy_colors.get(s, '#cccccc') for s in tool_means.index])
                          
            ax4.set_title('Average Tool Calls per Strategy')
            ax4.set_ylabel('Number of Tool Calls')
            ax4.grid(True, alpha=0.3)
            
            # Add value labels
            for bar, mean in zip(bars, tool_means.values):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + tool_stds[bar.get_x()],
                        f'{int(mean)}', ha='center', va='bottom', fontweight='bold')
        else:
            ax4.text(0.5, 0.5, 'Tool call data not available', 
                    transform=ax4.transAxes, ha='center', va='center')
            ax4.set_title('Tool Usage Analysis')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Strategy comparison plot saved to {save_path}")
            
        return fig
        
    def plot_performance_over_time(self, results: List[ExperimentResult], 
                                  save_path: Optional[str] = None) -> plt.Figure:
        """Plot performance metrics over simulation steps."""
        df = pd.DataFrame([asdict(r) for r in results if r.success])
        
        if df.empty:
            print("No successful results to plot")
            return None
            
        fig, axes = plt.subplots(2, 1, figsize=(12, 10))
        fig.suptitle('Performance Over Time', fontsize=16, fontweight='bold')
        
        # Crisis Score vs Steps
        ax1 = axes[0]
        for strategy in df['strategy'].unique():
            strategy_data = df[df['strategy'] == strategy]
            ax1.scatter(strategy_data['steps_completed'], strategy_data['crisis_score'],
                       label=strategy, alpha=0.7, s=50,
                       color=self.strategy_colors.get(strategy, '#cccccc'))
                       
        ax1.set_xlabel('Steps Completed')
        ax1.set_ylabel('Crisis Score')
        ax1.set_title('Crisis Score vs Simulation Length')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Rescue Rate vs Steps
        ax2 = axes[1]
        for strategy in df['strategy'].unique():
            strategy_data = df[df['strategy'] == strategy]
            ax2.scatter(strategy_data['steps_completed'], strategy_data['rescue_rate'],
                       label=strategy, alpha=0.7, s=50,
                       color=self.strategy_colors.get(strategy, '#cccccc'))
                       
        ax2.set_xlabel('Steps Completed')
        ax2.set_ylabel('Rescue Rate')
        ax2.set_title('Rescue Rate vs Simulation Length')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Performance over time plot saved to {save_path}")
            
        return fig
        
    def plot_success_rate_analysis(self, results: List[ExperimentResult],
                                  save_path: Optional[str] = None) -> plt.Figure:
        """Analyze success rates and failure patterns."""
        df = pd.DataFrame([asdict(r) for r in results])
        
        if df.empty:
            print("No results to analyze")
            return None
            
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Success Rate Analysis', fontsize=16, fontweight='bold')
        
        # Success rate by strategy
        ax1 = axes[0]
        success_rates = df.groupby('strategy')['success'].mean()
        bars = ax1.bar(success_rates.index, success_rates.values, alpha=0.8,
                      color=[self.strategy_colors.get(s, '#cccccc') for s in success_rates.index])
                      
        ax1.set_title('Success Rate by Strategy')
        ax1.set_ylabel('Success Rate')
        ax1.set_ylim(0, 1.0)
        ax1.grid(True, alpha=0.3)
        
        # Add percentage labels
        for bar, rate in zip(bars, success_rates.values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{rate:.1%}', ha='center', va='bottom', fontweight='bold')
        
        # Failure analysis
        ax2 = axes[1]
        failed_df = df[~df['success']]
        
        if not failed_df.empty:
            # Count failure types (simplified)
            failure_counts = failed_df['strategy'].value_counts()
            
            wedges, texts, autotexts = ax2.pie(failure_counts.values, labels=failure_counts.index,
                                              autopct='%1.1f%%', startangle=90,
                                              colors=[self.strategy_colors.get(s, '#cccccc') 
                                                    for s in failure_counts.index])
            ax2.set_title('Distribution of Failed Runs')
        else:
            ax2.text(0.5, 0.5, 'No failures to analyze!', 
                    transform=ax2.transAxes, ha='center', va='center', 
                    fontsize=14, fontweight='bold', color='green')
            ax2.set_title('Failure Analysis')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Success rate analysis plot saved to {save_path}")
            
        return fig
        
    def create_comprehensive_report(self, results: List[ExperimentResult],
                                   report_name: str = "experiment_report") -> str:
        """Create a comprehensive visual report with all plots."""
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.plots_dir / f"{report_name}_{timestamp}"
        report_dir.mkdir(exist_ok=True)
        
        # Generate all plots
        plots_generated = []
        
        try:
            # Strategy comparison
            fig1 = self.plot_strategy_comparison(results, 
                                               save_path=report_dir / "strategy_comparison.png")
            if fig1:
                plots_generated.append("strategy_comparison.png")
                plt.close(fig1)
                
            # Performance over time
            fig2 = self.plot_performance_over_time(results,
                                                 save_path=report_dir / "performance_over_time.png")
            if fig2:
                plots_generated.append("performance_over_time.png")
                plt.close(fig2)
                
            # Success rate analysis
            fig3 = self.plot_success_rate_analysis(results,
                                                  save_path=report_dir / "success_rate_analysis.png")
            if fig3:
                plots_generated.append("success_rate_analysis.png")
                plt.close(fig3)
                
        except Exception as e:
            print(f"Error generating plots: {e}")
            
        # Generate summary statistics
        self.generate_summary_table(results, report_dir / "summary_stats.txt")
        
        print(f"Comprehensive report generated in {report_dir}")
        print(f"Plots generated: {len(plots_generated)}")
        
        return str(report_dir)
        
    def generate_summary_table(self, results: List[ExperimentResult], 
                             save_path: str):
        """Generate a text summary of results."""
        df = pd.DataFrame([asdict(r) for r in results])
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write("EXPERIMENT RESULTS SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total Experiments: {len(results)}\n")
            f.write(f"Successful Runs: {sum(r.success for r in results)}\n")
            f.write(f"Overall Success Rate: {sum(r.success for r in results)/len(results):.1%}\n\n")
            
            if not df.empty:
                successful_df = df[df['success']]
                
                if not successful_df.empty:
                    f.write("PERFORMANCE STATISTICS (Successful Runs Only)\n")
                    f.write("-" * 40 + "\n")
                    
                    # Overall stats
                    f.write(f"Average Crisis Score: {successful_df['crisis_score'].mean():.2f} ± {successful_df['crisis_score'].std():.2f}\n")
                    f.write(f"Average Rescue Rate: {successful_df['rescue_rate'].mean():.2%} ± {successful_df['rescue_rate'].std():.2%}\n")
                    f.write(f"Average Execution Time: {successful_df['execution_time'].mean():.2f} seconds\n")
                    f.write(f"Average Steps Completed: {successful_df['steps_completed'].mean():.1f}\n\n")
                    
                    # Per-strategy breakdown
                    f.write("PER-STRATEGY BREAKDOWN\n")
                    f.write("-" * 25 + "\n")
                    
                    for strategy in successful_df['strategy'].unique():
                        strategy_data = successful_df[successful_df['strategy'] == strategy]
                        f.write(f"\n{strategy.upper()}:\n")
                        f.write(f"  Runs: {len(strategy_data)}\n")
                        f.write(f"  Avg Crisis Score: {strategy_data['crisis_score'].mean():.2f}\n")
                        f.write(f"  Avg Rescue Rate: {strategy_data['rescue_rate'].mean():.2%}\n")
                        f.write(f"  Avg Execution Time: {strategy_data['execution_time'].mean():.2f}s\n")
                        
        print(f"Summary statistics saved to {save_path}")

def load_and_visualize_results(results_file: str, report_name: str = "analysis"):
    """Convenience function to load results and create visualizations."""
    results_path = Path("results/experiments") / results_file
    
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        return
        
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    results = [ExperimentResult(**item) for item in data]
    
    visualizer = ResultsVisualizer()
    report_dir = visualizer.create_comprehensive_report(results, report_name)
    
    print(f"Visualization report created: {report_dir}")
    return report_dir

if __name__ == "__main__":
    # Example usage
    print("Visualization utilities loaded. Use load_and_visualize_results() to process experiment results.")
