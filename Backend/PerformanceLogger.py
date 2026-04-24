import json
import time
from datetime import datetime
from pathlib import Path
import statistics
from collections import defaultdict

class PerformanceLogger:
    """
    Logs performance metrics for research evaluation.
    Tracks: latency, accuracy, API usage, costs, errors, and comparisons
    """
    
    def __init__(self):
        self.log_file = Path("Data/performance_log.json")
        self.comparison_file = Path("Data/comparison_log.json")
        self.ensure_log_files()
    
    def ensure_log_files(self):
        """Create log files if they don't exist"""
        if not self.log_file.exists():
            with open(self.log_file, 'w') as f:
                json.dump([], f)
        
        if not self.comparison_file.exists():
            with open(self.comparison_file, 'w') as f:
                json.dump([], f)
    
    def log_interaction(self, 
                       query: str,
                       decision: list,
                       execution_time: float,
                       apis_used: list,
                       success: bool,
                       error_message: str = None,
                       decision_time: float = 0,
                       response_generation_time: float = 0,
                       tts_time: float = 0):
        """
        Log a single user interaction with detailed metrics
        
        Args:
            query: User's voice input
            decision: Decision model output (list of actions)
            execution_time: Total time from query to completion (seconds)
            apis_used: List of APIs called (e.g., ['groq', 'serper'])
            success: Whether the task completed successfully
            error_message: Error details if any
            decision_time: Time spent on intent classification
            response_generation_time: Time for LLM response
            tts_time: Time for text-to-speech
        """
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "decision": decision,
            "metrics": {
                "total_time_seconds": round(execution_time, 3),
                "decision_time_seconds": round(decision_time, 3),
                "response_time_seconds": round(response_generation_time, 3),
                "tts_time_seconds": round(tts_time, 3),
            },
            "apis_used": apis_used,
            "success": success,
            "error": error_message,
            "query_type": self._classify_query_type(decision),
            "estimated_cost": self._estimate_cost(apis_used, query)
        }
        
        # Append to log file
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
            
            logs.append(entry)
            
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        
        except Exception as e:
            print(f"Error logging performance: {e}")
    
    def _classify_query_type(self, decision: list) -> str:
        """Classify the query type based on decision"""
        if not decision:
            return "unknown"
        
        decision_str = ' '.join(decision).lower()
        
        if 'realtime' in decision_str:
            return "realtime"
        elif 'general' in decision_str:
            return "general"
        elif any(word in decision_str for word in ['open', 'close', 'play', 'system']):
            return "automation"
        elif 'generate' in decision_str:
            return "image_generation"
        else:
            return "mixed"
    
    def _estimate_cost(self, apis_used: list, query: str) -> float:
        """
        Estimate cost based on APIs used
        Rough estimates (update with actual pricing)
        """
        cost = 0.0
        
        # Cohere for decision making
        cost += 0.0001  # ~$0.0001 per decision
        
        for api in apis_used:
            if 'groq' in api.lower():
                # Groq: ~$0.0001 per 1K tokens, estimate 200 tokens per query
                cost += 0.00002
            elif 'serper' in api.lower():
                # Serper: ~$0.001 per search
                cost += 0.001
            elif 'huggingface' in api.lower():
                # HuggingFace image gen: free for now, but count as $0.01
                cost += 0.01
        
        return round(cost, 5)
    
    def log_comparison(self,
                       query: str,
                       cohere_decision: list,
                       pattern_decision: list,
                       cohere_time: float,
                       pattern_time: float,
                       actual_execution: str,
                       match_accuracy: bool):
        """
        Log comparison between Cohere and Pattern Matcher
        
        Args:
            query: User's query
            cohere_decision: Decision from Cohere model
            pattern_decision: Decision from pattern matcher
            cohere_time: Time taken by Cohere
            pattern_time: Time taken by pattern matcher
            actual_execution: What was actually executed ('cohere' or 'pattern')
            match_accuracy: Did both produce same result?
        """
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "cohere_decision": cohere_decision,
            "pattern_decision": pattern_decision,
            "cohere_time_seconds": round(cohere_time, 3),
            "pattern_time_seconds": round(pattern_time, 3),
            "speedup": round(cohere_time / pattern_time if pattern_time > 0 else 0, 2),
            "decisions_match": match_accuracy,
            "actual_execution": actual_execution
        }
        
        try:
            with open(self.comparison_file, 'r') as f:
                logs = json.load(f)
            
            logs.append(entry)
            
            with open(self.comparison_file, 'w') as f:
                json.dump(logs, f, indent=2)
        
        except Exception as e:
            print(f"Error logging comparison: {e}")
    
    def generate_statistics(self):
        """
        Generate comprehensive statistics from logs
        Returns dict with various metrics
        """
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
            
            if not logs:
                return {"error": "No logs found"}
            
            # Calculate statistics
            stats = {
                "total_interactions": len(logs),
                "success_rate": sum(1 for log in logs if log['success']) / len(logs) * 100,
                "query_types": defaultdict(int),
                "latency": {
                    "avg_total_time": 0,
                    "avg_decision_time": 0,
                    "avg_response_time": 0,
                    "avg_tts_time": 0,
                    "min_time": float('inf'),
                    "max_time": 0
                },
                "api_usage": defaultdict(int),
                "total_estimated_cost": 0,
                "errors": []
            }
            
            total_times = []
            decision_times = []
            response_times = []
            tts_times = []
            
            for log in logs:
                # Query types
                stats["query_types"][log['query_type']] += 1
                
                # Latency
                total_time = log['metrics']['total_time_seconds']
                total_times.append(total_time)
                decision_times.append(log['metrics']['decision_time_seconds'])
                response_times.append(log['metrics']['response_time_seconds'])
                tts_times.append(log['metrics']['tts_time_seconds'])
                
                stats["latency"]["min_time"] = min(stats["latency"]["min_time"], total_time)
                stats["latency"]["max_time"] = max(stats["latency"]["max_time"], total_time)
                
                # API usage
                for api in log['apis_used']:
                    stats["api_usage"][api] += 1
                
                # Cost
                stats["total_estimated_cost"] += log['estimated_cost']
                
                # Errors
                if not log['success'] and log['error']:
                    stats["errors"].append({
                        "query": log['query'],
                        "error": log['error']
                    })
            
            # Calculate averages
            stats["latency"]["avg_total_time"] = round(statistics.mean(total_times), 3)
            stats["latency"]["avg_decision_time"] = round(statistics.mean(decision_times), 3)
            stats["latency"]["avg_response_time"] = round(statistics.mean(response_times), 3)
            stats["latency"]["avg_tts_time"] = round(statistics.mean(tts_times), 3)
            
            # Percentiles
            stats["latency"]["p50"] = round(statistics.median(total_times), 3)
            stats["latency"]["p95"] = round(statistics.quantiles(total_times, n=20)[18], 3) if len(total_times) > 1 else 0
            
            # Convert defaultdicts to regular dicts
            stats["query_types"] = dict(stats["query_types"])
            stats["api_usage"] = dict(stats["api_usage"])
            
            # Cost per query
            stats["avg_cost_per_query"] = round(stats["total_estimated_cost"] / len(logs), 5)
            
            return stats
        
        except Exception as e:
            return {"error": str(e)}
    
    def generate_comparison_stats(self):
        """Generate statistics comparing Cohere vs Pattern Matcher"""
        
        try:
            with open(self.comparison_file, 'r') as f:
                logs = json.load(f)
            
            if not logs:
                return {"error": "No comparison logs found"}
            
            total = len(logs)
            matches = sum(1 for log in logs if log['decisions_match'])
            
            avg_cohere_time = sum(log['cohere_time_seconds'] for log in logs) / total
            avg_pattern_time = sum(log['pattern_time_seconds'] for log in logs) / total
            avg_speedup = avg_cohere_time / avg_pattern_time if avg_pattern_time > 0 else 0
            
            stats = {
                "total_comparisons": total,
                "accuracy": {
                    "matches": matches,
                    "match_rate": round((matches / total) * 100, 2),
                    "mismatches": total - matches
                },
                "performance": {
                    "avg_cohere_time": round(avg_cohere_time, 3),
                    "avg_pattern_time": round(avg_pattern_time, 3),
                    "speedup_factor": round(avg_speedup, 2),
                    "time_saved_per_query": round(avg_cohere_time - avg_pattern_time, 3)
                },
                "mismatches": []
            }
            
            # Collect mismatches for analysis
            for log in logs:
                if not log['decisions_match']:
                    stats["mismatches"].append({
                        "query": log['query'],
                        "cohere": log['cohere_decision'],
                        "pattern": log['pattern_decision']
                    })
            
            return stats
        
        except Exception as e:
            return {"error": str(e)}
    
    def print_statistics(self):
        """Print formatted statistics to console"""
        stats = self.generate_statistics()
        
        if "error" in stats:
            print(f"Error: {stats['error']}")
            return
        
        print("\n" + "="*60)
        print("📊 PERFORMANCE STATISTICS")
        print("="*60)
        
        print(f"\n📈 Overall Metrics:")
        print(f"   Total Interactions: {stats['total_interactions']}")
        print(f"   Success Rate: {stats['success_rate']:.1f}%")
        print(f"   Total Estimated Cost: ${stats['total_estimated_cost']:.4f}")
        print(f"   Avg Cost per Query: ${stats['avg_cost_per_query']:.5f}")
        
        print(f"\n⏱️  Latency Metrics (seconds):")
        print(f"   Average Total Time: {stats['latency']['avg_total_time']}")
        print(f"   Average Decision Time: {stats['latency']['avg_decision_time']}")
        print(f"   Average Response Time: {stats['latency']['avg_response_time']}")
        print(f"   Average TTS Time: {stats['latency']['avg_tts_time']}")
        print(f"   Min Time: {stats['latency']['min_time']}")
        print(f"   Max Time: {stats['latency']['max_time']}")
        print(f"   P50 (Median): {stats['latency']['p50']}")
        print(f"   P95: {stats['latency']['p95']}")
        
        print(f"\n📊 Query Type Distribution:")
        for query_type, count in stats['query_types'].items():
            percentage = (count / stats['total_interactions']) * 100
            print(f"   {query_type}: {count} ({percentage:.1f}%)")
        
        print(f"\n🔌 API Usage:")
        for api, count in stats['api_usage'].items():
            print(f"   {api}: {count} calls")
        
        if stats['errors']:
            print(f"\n❌ Errors ({len(stats['errors'])}):")
            for i, error in enumerate(stats['errors'][:5], 1):
                print(f"   {i}. Query: '{error['query']}'")
                print(f"      Error: {error['error']}")
        
        print("\n" + "="*60 + "\n")
    
    def print_comparison_stats(self):
        """Print formatted comparison statistics"""
        stats = self.generate_comparison_stats()
        
        if "error" in stats:
            print(f"Error: {stats['error']}")
            return
        
        print("\n" + "="*60)
        print("🔬 COHERE vs PATTERN MATCHER COMPARISON")
        print("="*60)
        
        print(f"\n📊 Accuracy Metrics:")
        print(f"   Total Comparisons: {stats['total_comparisons']}")
        print(f"   Decisions Match: {stats['accuracy']['matches']} ({stats['accuracy']['match_rate']}%)")
        print(f"   Decisions Differ: {stats['accuracy']['mismatches']}")
        
        print(f"\n⚡ Performance Metrics:")
        print(f"   Avg Cohere Time: {stats['performance']['avg_cohere_time']}s")
        print(f"   Avg Pattern Time: {stats['performance']['avg_pattern_time']}s")
        print(f"   Speedup Factor: {stats['performance']['speedup_factor']}x faster with Pattern Matcher")
        print(f"   Time Difference: {stats['performance']['time_saved_per_query']}s per query")
        
        if stats['mismatches']:
            print(f"\n❌ Mismatches ({len(stats['mismatches'])}):")
            for i, mismatch in enumerate(stats['mismatches'][:10], 1):
                print(f"\n   {i}. Query: '{mismatch['query']}'")
                print(f"      Cohere: {mismatch['cohere']}")
                print(f"      Pattern: {mismatch['pattern']}")
        
        print("\n" + "="*60 + "\n")
    
    def export_for_paper(self, output_file="Data/statistics_for_paper.txt"):
        """Export statistics in paper-ready format"""
        stats = self.generate_statistics()
        
        with open(output_file, 'w') as f:
            f.write("PERFORMANCE METRICS FOR RESEARCH PAPER\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Total Interactions: {stats['total_interactions']}\n")
            f.write(f"Success Rate: {stats['success_rate']:.2f}%\n")
            f.write(f"Average Latency: {stats['latency']['avg_total_time']}s\n")
            f.write(f"P95 Latency: {stats['latency']['p95']}s\n")
            f.write(f"Average Cost: ${stats['avg_cost_per_query']:.5f}\n\n")
            
            f.write("Query Type Distribution:\n")
            for query_type, count in stats['query_types'].items():
                percentage = (count / stats['total_interactions']) * 100
                f.write(f"  - {query_type}: {percentage:.1f}%\n")
        
        print(f"✅ Statistics exported to {output_file}")
    
    def export_comparison_for_paper(self, output_file="Data/comparison_for_paper.txt"):
        """Export comparison statistics in paper-ready format"""
        stats = self.generate_comparison_stats()
        
        if "error" in stats:
            print(f"Error: {stats['error']}")
            return
        
        with open(output_file, 'w') as f:
            f.write("COMPARISON METRICS FOR RESEARCH PAPER\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Total Comparisons: {stats['total_comparisons']}\n")
            f.write(f"Match Rate: {stats['accuracy']['match_rate']}%\n")
            f.write(f"Cohere Avg Time: {stats['performance']['avg_cohere_time']}s\n")
            f.write(f"Pattern Avg Time: {stats['performance']['avg_pattern_time']}s\n")
            f.write(f"Speedup Factor: {stats['performance']['speedup_factor']}x\n\n")
            
            f.write("Analysis:\n")
            f.write(f"  - Pattern Matcher is {stats['performance']['speedup_factor']}x faster\n")
            f.write(f"  - But only matches {stats['accuracy']['match_rate']}% of the time\n")
            f.write(f"  - Trade-off: Speed vs Accuracy\n\n")
            
            if stats['mismatches']:
                f.write(f"Example Mismatches ({len(stats['mismatches'])}):\n")
                for i, mismatch in enumerate(stats['mismatches'][:5], 1):
                    f.write(f"\n{i}. '{mismatch['query']}'\n")
                    f.write(f"   Cohere: {mismatch['cohere']}\n")
                    f.write(f"   Pattern: {mismatch['pattern']}\n")
        
        print(f"✅ Comparison exported to {output_file}")

# Create singleton instance
logger = PerformanceLogger()