# Priority System in VRP: Complete Explanation

## Overview

**Priority** determines which tasks get processed first during assignment. Higher-priority tasks (lower numbers) get assigned before FMs run out of capacity.

**Priority Scale**: `1.0` (highest/urgent) to `100.0` (lowest/routine)

---

## How Priority Works: Step-by-Step

### 1. Tasks Have Priority Values (Database)

**Task Model** (`app/models.py`):
```python
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    title = Column(String(255))
    priority = Column(Float, nullable=False)  # 1.0 to 100.0
    latitude = Column(Float)
    longitude = Column(Float)
    status = Column(String(50), default="pending")
```

**Example Tasks in Database**:
```sql
SELECT id, title, priority FROM tasks LIMIT 10;

┌──────────────────────────┬─────────────────────────┬──────────┐
│ id                       │ title                   │ priority │
├──────────────────────────┼─────────────────────────┼──────────┤
│ 0032fb32-1c11-485a-...   │ Emergency Medicine      │ 1.0      │  ← Urgent
│ 8c6075b5-f0e6-40c6-...   │ Critical Package        │ 2.5      │  ← Very High
│ 61798e75-1439-4d2f-...   │ Same-Day Delivery       │ 15.0     │  ← High
│ 7ddb00bc-ef58-4fc1-...   │ Standard Delivery       │ 50.0     │  ← Medium
│ 0128ac7f-ec38-4294-...   │ Bulk Order Item 1       │ 75.0     │  ← Low
│ 34377861-2206-4ae2-...   │ Bulk Order Item 2       │ 75.0     │  ← Low
│ a501b10c-6a30-4883-...   │ Non-Urgent Survey       │ 90.0     │  ← Very Low
└──────────────────────────┴─────────────────────────┴──────────┘
```

---

### 2. Job Parameters Filter by Priority Range

**When creating a VRP job**, you specify:
- `priority_min` (default: 1.0) - Only include tasks >= this priority
- `priority_max` (default: 100.0) - Only include tasks <= this priority

**Example Job Request**:
```json
POST /api/v1/vrp/jobs

{
  "max_tasks": 200,
  "priority_min": 1.0,    ← Only tasks with priority 1-50
  "priority_max": 50.0,   ← (high and medium priority)
  "strategy": "manual_area"
}
```

**What happens**: System fetches only tasks with `priority BETWEEN 1.0 AND 50.0`

**Use Cases**:
```
Scenario 1: Urgent orders only
priority_min: 1, priority_max: 20
→ Process only critical deliveries

Scenario 2: Routine deliveries
priority_min: 50, priority_max: 100
→ Process bulk/non-urgent tasks

Scenario 3: Everything
priority_min: 1, priority_max: 100
→ Process all pending tasks
```

---

### 3. Database Query Filters by Priority

**Code** (`app/celery_worker.py`, line 50-60):
```python
def solve_vrp(job_id_str: str):
    # Get job parameters
    job = db_service.get_vrp_job(db, job_id)
    params = job.params
    
    max_tasks = params.get("max_tasks", 10000)
    priority_min = params.get("priority_min", 1.0)
    priority_max = params.get("priority_max", 100.0)
    
    # Query tasks from database
    tasks = db.query(Task).filter(
        Task.status == "pending",
        Task.priority >= priority_min,      # ← Filter by min priority
        Task.priority <= priority_max,      # ← Filter by max priority
        Task.latitude.isnot(None),
        Task.longitude.isnot(None)
    ).order_by(Task.priority.asc()).limit(max_tasks).all()
    #            ↑
    #            Sort by priority (ascending = high priority first)
```

**SQL Generated**:
```sql
SELECT * FROM tasks
WHERE status = 'pending'
  AND priority >= 1.0          -- priority_min
  AND priority <= 50.0         -- priority_max
  AND latitude IS NOT NULL
  AND longitude IS NOT NULL
ORDER BY priority ASC          -- 1.0 first, 50.0 last
LIMIT 200;                     -- max_tasks
```

**Result**: Tasks ordered from **most urgent to least urgent**

---

### 4. Greedy Algorithm Processes in Priority Order

**Code** (`app/services/greedy_assignment_service.py`):
```python
def assign_tasks_greedy(self, tasks: List[dict], fm_locations: dict, max_tasks_per_fm: int = 100):
    """
    Assign tasks to nearest FM with capacity
    
    CRITICAL: Tasks MUST be pre-sorted by priority
    """
    
    # Tracks how many tasks each FM has
    fm_task_counts = {str(fm_id): 0 for fm_id in fm_locations.keys()}
    assignments = []
    
    # Tasks already sorted by priority (from database query)
    # Process in order: priority 1.0, 1.5, 2.0, ..., 50.0
    for task in tasks:
        best_fm_id = None
        best_distance = float('inf')
        
        # Find nearest FM with capacity
        for fm_id, (fm_lat, fm_lng) in fm_locations.items():
            fm_id_str = str(fm_id)
            
            # Check if FM at capacity
            if fm_task_counts[fm_id_str] >= max_tasks_per_fm:
                continue  # Skip this FM (full)
            
            # Calculate distance
            distance = self.haversine_distance(
                task["latitude"], task["longitude"],
                fm_lat, fm_lng
            )
            
            # Update best FM if closer
            if distance < best_distance:
                best_distance = distance
                best_fm_id = fm_id_str
        
        # Assign task to best FM (if found)
        if best_fm_id:
            assignments.append({
                "task_id": str(task["id"]),
                "fm_user_id": str(best_fm_id),
                "sequence_no": fm_task_counts[best_fm_id] + 1,
                "distance_meters": int(best_distance),
                "eta_seconds": int(best_distance / 10),
            })
            
            fm_task_counts[best_fm_id] += 1  # Increment count
```

**Why priority order matters**:

```
Example with 2 FMs, capacity = 2 tasks each:

Tasks:
- Task A: priority 1.0, location (14.5, 120.9)
- Task B: priority 2.0, location (14.5, 120.9)  ← Near Task A
- Task C: priority 50.0, location (14.5, 120.9) ← Near Task A
- Task D: priority 75.0, location (15.0, 122.0) ← Far away

FMs:
- FM1: location (14.5, 120.9) ← Near Task A/B/C
- FM2: location (15.0, 122.0) ← Near Task D


WITHOUT priority sorting (random order):
----------------------------------------------
Process Task C (priority 50) first → Assign to FM1 (nearest)
Process Task D (priority 75) next  → Assign to FM2 (nearest)
Process Task A (priority 1) next   → Assign to FM1 (nearest)
Process Task B (priority 2) last   → FM1 FULL! Assign to FM2 (far!)
                                      ↑ BAD: High-priority task gets bad assignment


WITH priority sorting (1, 2, 50, 75):
----------------------------------------------
Process Task A (priority 1) first  → Assign to FM1 (nearest) ✅
Process Task B (priority 2) next   → Assign to FM1 (nearest) ✅
Process Task C (priority 50) next  → FM1 FULL! Assign to FM2 (far) ← OK, low priority
Process Task D (priority 75) last  → Assign to FM2 (nearest) ✅
                                      ↑ GOOD: High-priority tasks get best assignments
```

**Result**: Urgent tasks get first pick of nearest FMs!

---

### 5. How Priority is Set (Task Creation)

**Option 1: Manual Assignment** (seed script):
```python
# app/seed_data.py
for i in range(10000):
    task = Task(
        title=f"Task {i+1}",
        priority=random.uniform(1.0, 100.0),  # Random 1-100
        latitude=random.uniform(7.0, 18.5),   # Philippines lat
        longitude=random.uniform(116.0, 127.0),  # Philippines lng
        status="pending"
    )
    db.add(task)
```

**Option 2: Business Logic** (API endpoint):
```python
# Determine priority based on order type
def calculate_priority(order_type: str) -> float:
    priority_map = {
        "emergency": 1.0,      # Ambulance, urgent medical
        "express": 5.0,        # Same-day delivery
        "standard": 50.0,      # Next-day delivery
        "bulk": 75.0,          # 3-5 days
        "routine": 90.0        # No rush
    }
    return priority_map.get(order_type, 50.0)

# When customer places order
task = Task(
    title=order.title,
    priority=calculate_priority(order.type),  # ← Business rule
    latitude=order.delivery_lat,
    longitude=order.delivery_lng
)
```

**Option 3: Time-Based** (urgency decay):
```python
from datetime import datetime, timedelta

def calculate_time_based_priority(delivery_deadline: datetime) -> float:
    """
    Earlier deadline = higher priority (lower number)
    """
    now = datetime.now()
    hours_until_deadline = (delivery_deadline - now).total_seconds() / 3600
    
    if hours_until_deadline < 2:
        return 1.0   # < 2 hours: Critical
    elif hours_until_deadline < 6:
        return 5.0   # < 6 hours: Urgent
    elif hours_until_deadline < 24:
        return 25.0  # < 24 hours: High
    elif hours_until_deadline < 72:
        return 50.0  # < 3 days: Medium
    else:
        return 75.0  # > 3 days: Low

# Example:
task = Task(
    title="Deliver to Customer A",
    priority=calculate_time_based_priority(order.deadline),
    ...
)
```

---

## Priority in Action: Real Example

### Scenario: 10,000 Tasks, 1,000 FMs, Capacity = 100 per FM

**Task Distribution**:
```
Priority 1-10:     500 tasks (5%)   ← Emergency/urgent
Priority 11-30:  1,500 tasks (15%)  ← High priority
Priority 31-60:  3,000 tasks (30%)  ← Medium priority
Priority 61-90:  4,000 tasks (40%)  ← Low priority
Priority 91-100: 1,000 tasks (10%)  ← Routine/bulk
```

**Job Created**: 
```json
{
  "max_tasks": 10000,
  "priority_min": 1,
  "priority_max": 100
}
```

**Processing Order**:
1. **First 500 tasks** (priority 1-10):
   - Get assigned to nearest FMs
   - Best possible routes
   - All 500 assigned successfully ✅

2. **Next 1,500 tasks** (priority 11-30):
   - Assigned to nearest available FMs
   - Some FMs starting to fill up
   - All 1,500 assigned ✅

3. **Next 3,000 tasks** (priority 31-60):
   - Many FMs at 50-80% capacity
   - May not get nearest FM (2nd or 3rd nearest)
   - All 3,000 assigned ✅

4. **Next 4,000 tasks** (priority 61-90):
   - Most FMs 80-95% capacity
   - Getting assigned to FMs 10-20km away
   - All 4,000 assigned ✅

5. **Last 1,000 tasks** (priority 91-100):
   - All FMs at capacity!
   - **0 assigned, 1,000 unassigned** ❌

**Result Summary**:
```json
{
  "summary": {
    "total_tasks_assigned": 9000,
    "unassigned_tasks": 1000,
    "total_distance_km": 8500,
    "fm_utilization": {
      "fm-1": 100,  ← Full
      "fm-2": 100,  ← Full
      "fm-3": 100,  ← Full
      ...
      "fm-900": 100,  ← Full (900 FMs used)
      "fm-901": 0,    ← Unused
      ...
    }
  }
}
```

**Key Insight**: Low-priority tasks (91-100) didn't get assigned because FMs were full. This is **intentional and good** - urgent tasks are prioritized over routine ones.

---

## Priority Strategies for Different Businesses

### Food Delivery (Time-Sensitive)
```python
def food_delivery_priority(order_time: datetime, restaurant_prep_time: int) -> float:
    """
    Food gets cold fast!
    Priority based on: order time + prep time
    """
    ready_time = order_time + timedelta(minutes=restaurant_prep_time)
    minutes_since_ready = (datetime.now() - ready_time).total_seconds() / 60
    
    if minutes_since_ready > 30:
        return 1.0   # Food cold! Critical
    elif minutes_since_ready > 15:
        return 5.0   # Getting cold
    elif minutes_since_ready > 5:
        return 10.0  # Freshly ready
    else:
        return 20.0  # Still cooking
```

### Healthcare (Severity-Based)
```python
def healthcare_priority(severity: str) -> float:
    """
    Medical appointments by urgency
    """
    severity_map = {
        "life_threatening": 1.0,   # Emergency
        "severe_pain": 5.0,        # Urgent
        "moderate": 25.0,          # Soon
        "routine_checkup": 50.0,   # Scheduled
        "wellness_visit": 75.0     # Flexible
    }
    return severity_map.get(severity, 50.0)
```

### E-Commerce (Customer Tier + Time)
```python
def ecommerce_priority(customer_tier: str, order_age_hours: float) -> float:
    """
    VIP customers + older orders = higher priority
    """
    base_priority = {
        "vip": 10.0,
        "premium": 30.0,
        "standard": 50.0,
        "free": 70.0
    }.get(customer_tier, 50.0)
    
    # Increase priority over time (0.5 per hour)
    time_boost = order_age_hours * 0.5
    final_priority = max(1.0, base_priority - time_boost)
    
    return final_priority

# Example:
# VIP customer, order placed 5 hours ago:
# priority = 10.0 - (5 * 0.5) = 7.5
# 
# Standard customer, order placed 50 hours ago:
# priority = 50.0 - (50 * 0.5) = 25.0  ← Now high priority!
```

---

## Visualizing Priority in Frontend

### Map View (Color-Coded)

**Code** (`app/static/index.html`):
```javascript
function getPriorityColor(priority) {
    if (priority <= 33) {
        return '#ff0000';  // Red: High priority (1-33)
    } else if (priority <= 66) {
        return '#ffaa00';  // Orange: Medium priority (34-66)
    } else {
        return '#00ff00';  // Green: Low priority (67-100)
    }
}

// Render task markers
tasks.forEach(task => {
    const color = getPriorityColor(task.priority);
    
    L.circleMarker([task.latitude, task.longitude], {
        radius: 6,
        fillColor: color,
        color: '#000',
        weight: 1,
        fillOpacity: 0.8
    }).bindPopup(`
        <b>${task.title}</b><br>
        Priority: ${task.priority}<br>
        Color: ${color === '#ff0000' ? 'Red (High)' : 
                color === '#ffaa00' ? 'Orange (Medium)' : 'Green (Low)'}
    `).addTo(map);
});
```

**Visual Result**:
```
Map View:

    🔴 🔴 🔴 🔴          ← High priority (red dots)
      🔴 🔴 🔴
        🟠 🟠 🟠        ← Medium priority (orange dots)
      🟠 🟠 🟠 🟠
    🟢 🟢 🟢 🟢 🟢      ← Low priority (green dots)
  🟢 🟢 🟢 🟢 🟢 🟢

Legend:
🔴 Priority 1-33: Urgent (red)
🟠 Priority 34-66: Standard (orange)
🟢 Priority 67-100: Routine (green)
```

---

## Testing Priority System

### Test 1: Create High-Priority-Only Job
```bash
curl -X POST http://localhost:8001/api/v1/vrp/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "max_tasks": 200,
    "priority_min": 1,
    "priority_max": 20
  }'

# Expected: Only urgent tasks assigned
# Check result: All assignments should have tasks with priority 1-20
```

### Test 2: Check Database Task Priorities
```sql
-- Connect to database
docker exec -it vrp-db-1 psql -U vrp_user -d vrp_db

-- Check priority distribution
SELECT 
    CASE 
        WHEN priority <= 33 THEN 'High (1-33)'
        WHEN priority <= 66 THEN 'Medium (34-66)'
        ELSE 'Low (67-100)'
    END as priority_tier,
    COUNT(*) as task_count
FROM tasks
WHERE status = 'pending'
GROUP BY priority_tier;

-- Example output:
--  priority_tier   | task_count
-- -----------------+------------
--  High (1-33)     |    3200
--  Medium (34-66)  |    3400
--  Low (67-100)    |    3400
```

### Test 3: Verify Assignment Order
```bash
# Create job
JOB_ID=$(curl -s -X POST http://localhost:8001/api/v1/vrp/jobs \
  -H "Content-Type: application/json" \
  -d '{"max_tasks": 100}' | jq -r '.job_id')

# Wait 15 seconds
sleep 15

# Fetch job result
curl -s http://localhost:8001/api/v1/vrp/jobs/$JOB_ID | jq '.result.assignments[:5] | .[] | {task_id, sequence_no}'

# Check database for those task IDs
docker exec -it vrp-db-1 psql -U vrp_user -d vrp_db -c "
SELECT id, priority FROM tasks WHERE id IN (
  'task-id-1',
  'task-id-2',
  ...
) ORDER BY priority;
"

# Expected: Priority values should be low (1-20) for first assigns
```

---

## Priority Summary

### How it Works:
1. **Tasks have priority** (1.0 = urgent, 100.0 = routine)
2. **Job parameters filter** by priority range (priority_min to priority_max)
3. **Database query sorts** tasks by priority ASC (urgent first)
4. **Greedy algorithm processes** in order (urgent tasks get first pick)
5. **Result**: High-priority tasks assigned to nearest FMs; low-priority tasks may be unassigned if capacity exhausted

### Why it Matters:
- ✅ **Fairness**: Urgent tasks don't wait behind routine ones
- ✅ **Customer satisfaction**: Emergency orders get fastest delivery
- ✅ **Business logic**: Prioritize revenue (VIP customers, express orders)
- ✅ **Resource optimization**: Don't waste FM capacity on low-value tasks

### Key Configuration:
```bash
# Job creation
{
  "priority_min": 1,    ← Only tasks >= this value
  "priority_max": 100   ← Only tasks <= this value
}
```

### Business Use Cases:
```
Emergency services:     priority_min=1,  priority_max=10
Express delivery:       priority_min=1,  priority_max=30
Standard delivery:      priority_min=30, priority_max=70
Bulk/routine:           priority_min=70, priority_max=100
Everything:             priority_min=1,  priority_max=100
```

**The Big Picture**: Priority ensures the **right tasks get assigned first**, maximizing customer satisfaction and business value. It's the difference between "random assignment" and "smart assignment"! 🎯
