"""H3 clustering service for VRP optimization (R&D feature)"""
import h3
from typing import List, Dict, Tuple, Optional
from app.config import settings


class H3Service:
    def __init__(self, resolution: int = None):
        self.resolution = resolution or settings.h3_resolution
        self.enabled = settings.h3_enabled
    
    def get_h3_cell(self, lat: float, lng: float) -> str:
        """Convert lat/lng to H3 cell"""
        # h3 v3 API
        return h3.geo_to_h3(lat, lng, self.resolution)
    
    def cluster_tasks_by_h3(self, tasks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Cluster tasks by H3 cell
        
        Args:
            tasks: List of task dicts with 'latitude' and 'longitude'
        
        Returns:
            Dict mapping H3 cell -> list of tasks
        """
        if not self.enabled:
            return {"default": tasks}
        
        clusters = {}
        for task in tasks:
            if task.get("latitude") and task.get("longitude"):
                cell = self.get_h3_cell(task["latitude"], task["longitude"])
                if cell not in clusters:
                    clusters[cell] = []
                clusters[cell].append(task)
        
        return clusters
    
    def get_cluster_center(self, cell: str) -> Tuple[float, float]:
        """Get center point of H3 cell"""
        # h3 v3 API
        lat, lng = h3.h3_to_geo(cell)
        return lat, lng
    
    def assign_fms_to_clusters(
        self,
        clusters: Dict[str, List[Dict]],
        fm_locations: Dict[str, Tuple[float, float]]
    ) -> Dict[str, List[str]]:
        """
        Simple heuristic: assign FMs to nearest clusters
        
        Args:
            clusters: H3 cell -> tasks mapping
            fm_locations: FM user_id -> (lat, lng) mapping
        
        Returns:
            H3 cell -> list of FM user_ids
        """
        cluster_assignments = {cell: [] for cell in clusters.keys()}
        
        # Get cluster centers
        cluster_centers = {
            cell: self.get_cluster_center(cell)
            for cell in clusters.keys()
        }
        
        # Simple assignment: each FM to nearest cluster
        # In production, use more sophisticated algorithm
        for fm_id, fm_loc in fm_locations.items():
            nearest_cell = min(
                cluster_centers.keys(),
                key=lambda c: self._haversine_distance(fm_loc, cluster_centers[c])
            )
            cluster_assignments[nearest_cell].append(fm_id)
        
        return cluster_assignments
    
    def _haversine_distance(self, loc1: Tuple[float, float], loc2: Tuple[float, float]) -> float:
        """Calculate approximate distance between two lat/lng points"""
        from math import radians, sin, cos, sqrt, atan2
        
        lat1, lng1 = map(radians, loc1)
        lat2, lng2 = map(radians, loc2)
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        # Earth radius in km
        return 6371 * c


h3_service = H3Service()
