import redis
import json
from datetime import datetime
from typing import Optional, Dict
from app.config import settings


class RedisService:
    def __init__(self):
        self.client = redis.from_url(settings.redis_url, decode_responses=True)
        self.pubsub = self.client.pubsub()
    
    def set_fm_location(self, user_id: str, lat: float, long: float) -> None:
        """Set field man current location with TTL"""
        key = f"fm:loc:{user_id}"
        value = json.dumps({
            "lat": lat,
            "long": long,
            "updated_at": datetime.utcnow().isoformat()
        })
        self.client.setex(key, settings.fm_location_ttl, value)
    
    def get_fm_location(self, user_id: str) -> Optional[Dict[str, float]]:
        """Get field man current location"""
        key = f"fm:loc:{user_id}"
        value = self.client.get(key)
        if value:
            data = json.loads(value)
            return {"lat": data["lat"], "long": data["long"]}
        return None
    
    def publish_job_status(self, job_id: str, status: str) -> None:
        """Publish VRP job status update"""
        channel = f"vrp:job:{job_id}:status"
        payload = json.dumps({
            "job_id": job_id,
            "status": status
        })
        self.client.publish(channel, payload)
    
    def subscribe_job_status(self, job_id: str):
        """Subscribe to VRP job status updates"""
        channel = f"vrp:job:{job_id}:status"
        self.pubsub.subscribe(channel)
        return self.pubsub
    
    def close(self):
        """Close connections"""
        self.pubsub.close()
        self.client.close()


# Singleton instance
redis_service = RedisService()
