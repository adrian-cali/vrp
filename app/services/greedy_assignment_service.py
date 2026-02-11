"""Simple greedy assignment service - assigns tasks to nearest FM"""
from typing import List, Dict, Any, Tuple
import math


class GreedyAssignmentService:
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate Haversine distance between two points in meters
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
        
        Returns:
            Distance in meters
        """
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def assign_tasks_greedy(
        self,
        tasks: List[Any],
        fm_locations: Dict[str, Tuple[float, float]],
        max_tasks_per_fm: int = 100
    ) -> Dict[str, Any]:
        """
        Assign tasks to nearest field manager using greedy algorithm
        
        Args:
            tasks: List of Task objects with id, latitude, longitude, priority
            fm_locations: Dict mapping FM user_id -> (lat, lng) tuple
            max_tasks_per_fm: Maximum number of tasks per FM
        
        Returns:
            Dict with assignments list and summary stats
        """
        assignments = []
        fm_task_counts = {str(fm_id): 0 for fm_id in fm_locations.keys()}  # Ensure string keys
        
        # Sort tasks by priority (1 = highest priority)
        sorted_tasks = sorted(tasks, key=lambda t: t.priority)
        
        total_distance = 0
        assigned_count = 0
        unassigned_count = 0
        
        for task_idx, task in enumerate(sorted_tasks):
            # Find nearest FM with capacity
            best_fm_id = None
            best_distance = float('inf')
            
            for fm_id, (fm_lat, fm_lng) in fm_locations.items():
                fm_id_str = str(fm_id)  # Ensure string
                if fm_task_counts[fm_id_str] >= max_tasks_per_fm:
                    continue  # FM at capacity
                
                distance = self.haversine_distance(
                    task.latitude,
                    task.longitude,
                    fm_lat,
                    fm_lng
                )
                
                if distance < best_distance:
                    best_distance = distance
                    best_fm_id = fm_id_str  # Use string version
            
            if best_fm_id:
                # Assign task to this FM (ensure all IDs are strings for JSON serialization)
                assignments.append({
                    "task_id": str(task.id),
                    "fm_user_id": str(best_fm_id),  # Ensure string
                    "sequence_no": fm_task_counts[best_fm_id] + 1,
                    "distance_meters": int(best_distance),
                    "eta_seconds": int(best_distance / 10),
                })
                
                fm_task_counts[best_fm_id] += 1
                total_distance += best_distance
                assigned_count += 1
            else:
                # No FM available (all at capacity)
                unassigned_count += 1
        
        # Calculate summary
        summary = {
            "total_distance": int(total_distance),
            "total_duration": int(total_distance / 10),  # seconds
            "total_tasks_assigned": assigned_count,
            "unassigned_tasks": unassigned_count,
            "fm_utilization": {
                str(fm_id): count for fm_id, count in fm_task_counts.items() if count > 0
            }
        }
        
        return {
            "assignments": assignments,
            "summary": summary
        }
