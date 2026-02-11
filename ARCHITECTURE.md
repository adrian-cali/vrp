# VRP System Architecture

## Overview
This is a **Vehicle Route Planning (VRP)** system that assigns tasks to field managers (FMs) using geospatial optimization. It processes thousands of tasks across the Philippines and assigns them to the nearest available FMs.

---

## System Components

### 1. **FastAPI Server** (`app/main.py`)
- **Port**: 8001
- **Purpose**: REST API for creating jobs, viewing assignments, and serving the web UI
- **Key Routes**:
  - `/api/v1/vrp/*` - VRP job management
  - `/api/v1/data/*` - Public data (tasks, FM locations, H3 clusters)
  - `/api/v1/vrp/jobs/{job_id}/preview` - HTML preview of assignments
  - `/` - Static web UI (Leaflet map, job dashboard)

### 2. **PostgreSQL Database** (`models.py`)
- **Port**: 5433
- **Tables**:
  - `users` - Field managers and requestors
  - `tasks` - Delivery/service tasks with lat/lng
  - `fm_home_locations` - FM home coordinates
  - `vrp_jobs` - Job requests & results (JSONB)
  - `vrp_assignments` - Individual task→FM assignments

### 3. **Redis** (`services/redis_service.py`)
- **Port**: 6380
- **Uses**:
  - Cache FM locations (600s TTL)
  - Pub/sub for job status updates
  - Session/temporary data

### 4. **Celery Worker** (`celery_worker.py`)
- **Purpose**: Background job processing
- **Tasks**:
  - `solve_vrp(job_id)` - Main task that processes VRP jobs
- **Process**:
  1. Fetch tasks & FM locations
  2. Apply H3 geospatial clustering (optional)
  3. Run greedy assignment algorithm
  4. Save assignments to database
  5. Update job status to "ready_to_preview"

### 5. **VROOM Service** (Currently unused)
- **Port**: 3001
- **Status**: Container running but not used
- **Reason**: System uses greedy algorithm instead (OSRM routing failed due to memory issues)

---

## Data Flow

### Creating a VRP Job

```
User Request (Web UI or API)
    ↓
POST /api/v1/vrp/jobs
    ↓
Create VRPJob in database (status: "queued")
    ↓
Enqueue Celery task: solve_vrp.delay(job_id)
    ↓
Return job_id to user immediately
```

### Processing a VRP Job (Celery Worker)

```
solve_vrp(job_id) receives job
    ↓
1. Update job status → "running"
    ↓
2. Fetch tasks from DB
   - Filter by priority range (params.priority_min to priority_max)
   - Limit to max_tasks (default: 10,000)
   - Only tasks with valid lat/lng
    ↓
3. Fetch FM locations from Redis/DB
   - Read from fm_home_locations table
   - Cache in Redis for 600 seconds
    ↓
4. [OPTIONAL] H3 Clustering (if H3_ENABLED=true)
   - Group tasks into hexagonal grid cells (resolution 8)
   - Each cell ≈ 0.46 km² area
   - Log top 10 clusters by task count
    ↓
5. Greedy Assignment Algorithm
   - Sort tasks by priority (1 = highest)
   - For each task:
     * Calculate Haversine distance to all FMs
     * Assign to nearest FM with capacity < 100 tasks
     * Track: task_id, fm_user_id, sequence_no, distance, ETA
    ↓
6. Convert UUIDs to strings (JSON serialization)
    ↓
7. Bulk insert assignments into vrp_assignments table
   - Convert strings back to UUID objects for database
    ↓
8. Store result summary in vrp_jobs.result (JSONB)
   - assignments: [{task_id, fm_user_id, sequence_no, distance_meters, eta_seconds}]
   - summary: {total_tasks_assigned, unassigned_tasks, total_distance, fm_utilization}
    ↓
9. Update job status → "ready_to_preview"
    ↓
10. Publish Redis notification
```

---

## Key Algorithms

### Greedy Assignment (`services/greedy_assignment_service.py`)

**Purpose**: Assign tasks to nearest FM with available capacity

**Algorithm**:
1. Initialize empty assignment list
2. Track task count per FM (max 100)
3. Sort tasks by priority (1 = highest priority)
4. For each task:
   - Calculate Haversine distance to all FMs
   - Find nearest FM with space
   - Assign task with sequence number
   - Increment FM's task count
5. Return assignments + summary stats

**Distance Calculation**: Haversine formula
- Accounts for Earth's curvature
- Returns meters between two lat/lng points

**Time Estimate**: Simple assumption
- `eta_seconds = distance_meters / 10` (10 m/s ≈ 36 km/h)

### H3 Clustering (`services/h3_service.py`)

**Purpose**: Group nearby tasks into hexagonal cells for visualization

**Library**: Uber H3 (v3.7.6)
- **Resolution 8**: Cell area ≈ 0.46 km² (462,000 m²)
- **Resolution 9**: Cell area ≈ 0.10 km² (105,000 m²)

**Process**:
1. Convert task (lat, lng) → H3 cell ID
2. Group tasks by cell ID
3. Count tasks per cell
4. Find FMs within each cell
5. Return cluster centers + counts

**Use Cases**:
- Heat map visualization
- Performance analysis (cluster density)
- Future: Per-cluster VRP solving

---

## Database Schema

### VRPJob Table
```sql
CREATE TABLE vrp_jobs (
    id UUID PRIMARY KEY,
    requestor_user_id UUID REFERENCES users(id),
    status VARCHAR(50),  -- queued, running, ready_to_preview, failed, finalized
    params JSONB,         -- {max_tasks, priority_min, priority_max, strategy}
    result JSONB,         -- {assignments: [...], summary: {...}}
    error TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### VRPAssignment Table
```sql
CREATE TABLE vrp_assignments (
    id UUID PRIMARY KEY,
    vrp_job_id UUID REFERENCES vrp_jobs(id),
    task_id UUID REFERENCES tasks(id),
    fm_user_id UUID REFERENCES users(id),
    sequence_no INTEGER,      -- Order for this FM (1st task, 2nd task, etc.)
    distance_meters INTEGER,
    eta_seconds INTEGER,
    UNIQUE(vrp_job_id, task_id)  -- Each task assigned once per job
);
```

### Task Table
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    priority FLOAT,           -- 1 (highest) to 100 (lowest)
    latitude FLOAT,
    longitude FLOAT,
    status VARCHAR(50),       -- pending, assigned, finalized
    created_at TIMESTAMP
);
```

---

## Configuration (.env)

### H3 Clustering
- `H3_ENABLED=true` - Enable H3 clustering in jobs
- `H3_RESOLUTION=8` - Hexagon size (8 = ~0.46 km²)
- `H3_MIN_TASKS=100` - Minimum tasks to enable clustering

### Database
- `POSTGRES_HOST=db`
- `POSTGRES_PORT=5432`
- `POSTGRES_USER=vrp_user`
- `POSTGRES_PASSWORD=vrp_pass`
- `POSTGRES_DB=vrp_db`

### Redis
- `REDIS_HOST=redis`
- `REDIS_PORT=6379`

### Services
- `VROOM_URL=http://vroom:3000` (unused)

---

## API Endpoints

### Create Job
```bash
POST /api/v1/vrp/jobs
Content-Type: application/json

{
  "max_tasks": 200,
  "priority_min": 1,
  "priority_max": 50,
  "strategy": "manual_area"
}

Response:
{
  "job_id": "uuid",
  "status": "queued",
  "created_at": "2026-02-10T01:15:00Z"
}
```

### List Jobs
```bash
GET /api/v1/vrp/jobs?page=1&page_size=10

Response:
{
  "jobs": [
    {
      "id": "uuid",
      "status": "ready_to_preview",
      "params": {...},
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 10
}
```

### Get Job Detail
```bash
GET /api/v1/vrp/jobs/{job_id}

Response:
{
  "id": "uuid",
  "status": "ready_to_preview",
  "params": {...},
  "result": {
    "assignments": [
      {
        "task_id": "uuid",
        "fm_user_id": "uuid",
        "sequence_no": 1,
        "distance_meters": 450,
        "eta_seconds": 45
      }
    ],
    "summary": {
      "total_tasks_assigned": 200,
      "unassigned_tasks": 0,
      "total_distance_km": 125.5,
      "fm_utilization": {
        "fm-uuid-1": 10,
        "fm-uuid-2": 15
      }
    }
  }
}
```

### Preview Assignments (HTML)
```bash
GET /api/v1/vrp/jobs/{job_id}/preview

Returns: HTML page with Leaflet map showing:
- Task locations (color-coded by priority)
- FM home locations
- Assignment routes
```

---

## Web UI (`app/static/index.html`)

### Tabs

#### 1. Map View
- Leaflet.js map
- Shows all 10,000 tasks as markers
- Color-coded by priority:
  - 🔴 Red: Priority 1-33 (high)
  - 🟡 Yellow: Priority 34-66 (medium)
  - 🟢 Green: Priority 67-100 (low)

#### 2. VRP Jobs
- List of all jobs
- Columns: Job ID, Status, Created At, Params
- Actions: Preview button (opens assignment map)
- Auto-refresh every 5 seconds

#### 3. Create Job
- Form to create new VRP job
- Fields:
  - Max Tasks (1-10,000)
  - Priority Range (1-100)
  - Strategy (manual_area)
- Submit → Creates job → Shows job ID

#### 4. FM Locations
- Table of all field managers
- Columns: FM ID, Home Lat/Lng
- Shows 1,000 FMs from database

---

## Performance

### Benchmarks (10,000 tasks, 1,000 FMs)

| Operation | Time |
|-----------|------|
| H3 Clustering | 2-4 seconds |
| Greedy Assignment | 10-12 seconds |
| Database Insert (bulk) | 2-3 seconds |
| **Total Job Processing** | **12-15 seconds** |

### Optimization Techniques
- **Redis caching**: FM locations cached 600s
- **Bulk database inserts**: `bulk_save_objects()`
- **Priority sorting**: Process high-priority tasks first
- **Distance shortcuts**: Haversine (no routing API calls)

---

## Common Issues & Solutions

### 1. Jobs Stuck in "running" Status
**Cause**: Celery worker crashed during processing
**Fix**: Restart Celery: `docker-compose restart celery_worker`

### 2. Jobs Failed with "UUID not serializable"
**Cause**: UUID objects in JSONB field
**Fix**: Already implemented - `convert_uuids_to_strings()`

### 3. Swagger UI Hanging
**Cause**: Large result field in list response
**Fix**: Already implemented - Use `VRPJobSummary` (excludes result)

### 4. OSRM Out of Memory
**Cause**: Philippines map too large (563MB)
**Fix**: System uses greedy algorithm instead

---

## Future Improvements

### Short-term
- [ ] Add job retry mechanism
- [ ] Implement real-time progress updates (WebSocket)
- [ ] Add assignment filtering (by FM, by priority)
- [ ] Export assignments to CSV/Excel

### Long-term
- [ ] Per-cluster VRP solving (use H3 cells)
- [ ] Real routing via smaller OSRM maps (city-level)
- [ ] Time windows for tasks (delivery windows)
- [ ] FM skill matching (task types)
- [ ] Dynamic rebalancing (handle new tasks)

---

## Testing

### Quick Test
```bash
# 1. Create a job
curl -X POST http://localhost:8001/api/v1/vrp/jobs \
  -H "Content-Type: application/json" \
  -d '{"max_tasks": 100, "priority_min": 1, "priority_max": 100}'

# 2. Wait 15 seconds

# 3. Check status
curl http://localhost:8001/api/v1/vrp/jobs/{job_id}

# Expected: status = "ready_to_preview"
```

### Run All Tests
```bash
# Unit tests (if available)
docker exec vrp-api-1 pytest

# Load test
ab -n 100 -c 10 http://localhost:8001/api/v1/data/tasks
```

---

## Deployment

### Development
```bash
docker-compose up -d
```

### Production Considerations
- [ ] Enable authentication (X-User-Id currently optional)
- [ ] Add rate limiting (Redis)
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure auto-scaling (Celery workers)
- [ ] Add logging aggregation (ELK stack)
- [ ] Use managed PostgreSQL (RDS/Cloud SQL)
- [ ] Add backup strategy (pg_dump cron)

---

## Tech Stack Summary

| Component | Technology | Version |
|-----------|-----------|---------|
| API Framework | FastAPI | 0.109.0 |
| Database | PostgreSQL | 15 |
| Task Queue | Celery | 5.3.6 |
| Message Broker | Redis | 7 |
| Geospatial | H3 (Python) | 3.7.6 |
| Routing (unused) | VROOM | 1.13.0 |
| ORM | SQLAlchemy | 2.0.25 |
| Frontend | Leaflet.js | 1.9.4 |
| Container | Docker Compose | 2.x |

---

## Contact & Support

For questions about this codebase:
1. Check `TESTING_QUICK_START.md` for usage examples
2. Review `PROGRESS_REPORT.md` for recent changes
3. Read `H3_GUIDE.md` for H3 clustering details
