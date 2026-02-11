"""VROOM integration service"""
import httpx
from typing import List, Dict, Any, Optional
from app.config import settings


class VROMService:
    def __init__(self):
        self.vroom_url = settings.vroom_url
        self.osrm_url = settings.osrm_url
    
    async def solve_vrp(
        self,
        jobs: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call VROOM API to solve VRP
        
        Args:
            jobs: List of job dicts with id, location (lat, lng), priority, etc.
            vehicles: List of vehicle dicts with id, start location, etc.
        
        Returns:
            VROOM solution dict
        """
        payload = {
            "jobs": jobs,
            "vehicles": vehicles
            # Note: No routing options - VROOM using straight-line distances
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(self.vroom_url, json=payload)
            response.raise_for_status()
            return response.json()
    
    def build_vroom_jobs(self, tasks: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert task objects to VROOM jobs format
        
        Args:
            tasks: List of Task model instances
        
        Returns:
            List of VROOM job dicts
        """
        jobs = []
        for idx, task in enumerate(tasks, start=1):
            if not task.latitude or not task.longitude:
                continue
            
            jobs.append({
                "id": idx,  # Use enumeration index
                "location": [task.longitude, task.latitude],  # VROOM uses [lng, lat]
                "priority": int(101 - task.priority),  # Invert: 1 (high) -> 100, 100 (low) -> 1
                "service": 300,  # 5 minutes service time per task
                "delivery": [1],  # Dummy delivery amount
                "task_id_ref": str(task.id)  # Keep reference to our task ID
            })
        
        return jobs
    
    def build_vroom_vehicles(
        self,
        fm_locations: Dict[str, tuple]
    ) -> List[Dict[str, Any]]:
        """
        Convert FM locations to VROOM vehicles format
        
        Args:
            fm_locations: Dict mapping FM user_id (str) -> (lat, lng) tuple
        
        Returns:
            List of VROOM vehicle dicts
        """
        vehicles = []
        for idx, (fm_id, (lat, lng)) in enumerate(fm_locations.items(), start=1):
            vehicles.append({
                "id": idx,
                "start": [lng, lat],  # VROOM uses [lng, lat]
                "capacity": [10000],  # Large capacity
                "time_window": [0, 28800],  # 8 hour work day (in seconds)
                "fm_user_id_ref": fm_id  # Keep reference to our FM ID
            })
        
        return vehicles
    
    def normalize_vroom_result(
        self,
        vroom_result: Dict[str, Any],
        jobs_map: Dict[int, str],  # vroom job id -> task_id
        vehicles_map: Dict[int, str]  # vroom vehicle id -> fm_user_id
    ) -> Dict[str, Any]:
        """
        Normalize VROOM result into our format for DB storage
        
        Returns:
            Dict with summary stats and assignment list
        """
        routes = vroom_result.get("routes", [])
        
        assignments = []
        summary = {
            "total_distance": 0,
            "total_duration": 0,
            "total_tasks_assigned": 0,
            "unassigned_tasks": len(vroom_result.get("unassigned", []))
        }
        
        for route in routes:
            vehicle_id = route.get("vehicle")
            fm_user_id = vehicles_map.get(vehicle_id)
            
            if not fm_user_id:
                continue
            
            steps = route.get("steps", [])
            sequence_no = 0
            
            route_distance = route.get("distance", 0)
            route_duration = route.get("duration", 0)
            
            summary["total_distance"] += route_distance
            summary["total_duration"] += route_duration
            
            for step in steps:
                if step.get("type") == "job":
                    job_id = step.get("job")
                    task_id = jobs_map.get(job_id)
                    
                    if task_id:
                        sequence_no += 1
                        assignments.append({
                            "fm_user_id": fm_user_id,
                            "task_id": task_id,
                            "sequence_no": sequence_no,
                            "eta_seconds": step.get("arrival", 0),
                            "distance_meters": step.get("distance", 0)
                        })
                        summary["total_tasks_assigned"] += 1
        
        return {
            "summary": summary,
            "assignments": assignments,
            "raw_vroom_output": vroom_result
        }


vroom_service = VROMService()
