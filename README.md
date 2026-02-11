# VRP Application - Vehicle Route Planning with VROOM + OSRM

A production-ready FastAPI application for Vehicle Route Planning (VRP) that optimizes task assignments for up to 10,000 tasks across ~1,000 field men using VROOM routing engine with OSRM backend.

## Features

- 🚀 **FastAPI** REST API with WebSocket support
- 🗄️ **PostgreSQL** database with SQLAlchemy 2.0 + Alembic migrations
- 🔄 **Celery** for asynchronous VRP solving
- 📦 **Redis** for caching FM locations and pub/sub notifications
- 🗺️ **OSRM** routing engine with Philippines map data
- 🚗 **VROOM** VRP solver integration
- 🏗️ **Docker Compose** for easy deployment
- 🧪 Optional **H3** clustering for task optimization (R&D)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  PostgreSQL │     │    Redis    │
│     API     │◀────│   Database  │     │   Cache +   │
└─────┬───────┘     └─────────────┘     │   PubSub    │
      │                                  └──────┬──────┘
      │                                         │
      ▼                                         ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Celery    │────▶│    VROOM    │────▶│    OSRM     │
│   Worker    │◀────│  VRP Solver │◀────│   Router    │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Tech Stack

- **API Framework**: FastAPI 0.109+
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0 + Alembic
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery 5.3
- **Routing Engine**: OSRM (Open Source Routing Machine)
- **VRP Solver**: VROOM
- **Containerization**: Docker + Docker Compose
- **Optional**: H3 geospatial indexing

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM recommended
- ~2GB disk space for OSRM map data

### 1. Clone and Setup

```bash
cd /home/adrian/vrp
cp .env.example .env
```

### 2. Update OSRM Map (First Time Setup)

Download and build the latest Philippines map from Geofabrik:

```bash
chmod +x scripts/update_map.sh
./scripts/update_map.sh
```

This will:
- Download latest Philippines OSM data (~150MB)
- Build OSRM routing files (extract, partition, customize)
- Takes approximately 10-20 minutes depending on your system

### 3. Start Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- OSRM routing engine (port 5000)
- VROOM solver (port 3000)
- FastAPI application (port 8000)
- Celery worker (background)

### 4. Run Database Migrations

```bash
docker-compose exec api alembic upgrade head
```

### 5. Seed Test Data

Generate 1,000 FMs + 10,000 tasks:

```bash
docker-compose exec api python scripts/seed_data.py
```

This creates:
- 1 admin user
- 1 requestor user
- 1,000 field men with home locations in NCR
- 10,000 tasks with priorities 1-100
- Sample areas with FM assignments

**Save the User IDs** displayed at the end - you'll need them for API requests.

### 6. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Access API docs
open http://localhost:8000/docs
```

## API Usage

### Authentication

All requests require `X-User-Id` header with a valid UUID:

```bash
X-User-Id: <requestor-user-id-from-seed>
```

### Endpoints

#### 1. Create VRP Job

```bash
curl -X POST http://localhost:8000/api/v1/vrp/jobs \
  -H "Content-Type: application/json" \
  -H "X-User-Id: <your-requestor-uuid>" \
  -d '{
    "strategy": "manual_area",
    "max_tasks": 1000,
    "priority_min": 1,
    "priority_max": 50,
    "fm_user_ids": null
  }'
```

Response:
```json
{
  "job_id": "uuid",
  "status": "queued",
  "created_at": "2024-01-15T10:00:00"
}
```

#### 2. List Jobs

```bash
curl http://localhost:8000/api/v1/vrp/jobs?status=ready_to_preview \
  -H "X-User-Id: <your-requestor-uuid>"
```

#### 3. Get Job Details

```bash
curl http://localhost:8000/api/v1/vrp/jobs/<job-id> \
  -H "X-User-Id: <your-requestor-uuid>"
```

#### 4. Preview Assignments (HTML)

Open in browser:
```
http://localhost:8000/api/v1/vrp/jobs/<job-id>/preview?user_id=<your-requestor-uuid>
```

Or with curl:
```bash
curl http://localhost:8000/api/v1/vrp/jobs/<job-id>/preview \
  -H "X-User-Id: <your-requestor-uuid>"
```

#### 5. Finalize Job

```bash
curl -X POST http://localhost:8000/api/v1/vrp/jobs/<job-id>/finalize \
  -H "X-User-Id: <your-requestor-uuid>"
```

#### 6. Update FM Location

```bash
curl -X POST http://localhost:8000/api/v1/fm/location \
  -H "Content-Type: application/json" \
  -H "X-User-Id: <fm-user-uuid>" \
  -d '{
    "current_lat": 14.5995,
    "current_long": 120.9842
  }'
```

### WebSocket Example

Connect to job status updates:

```javascript
const ws = new WebSocket(
  'ws://localhost:8000/api/v1/ws/vrp-jobs/<job-id>?user_id=<your-requestor-uuid>'
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Job status:', data.status);
};
```

Or use a WebSocket client tool:
```bash
wscat -c "ws://localhost:8000/api/v1/ws/vrp-jobs/<job-id>?user_id=<uuid>"
```

## Database Schema

### Tables

- **users**: Admin, requestors, and field men
- **tasks**: Tasks to be assigned (with priorities 1-100)
- **fm_home_locations**: Field men home/depot locations
- **areas**: Geographic areas (e.g., cities)
- **fm_assigned_areas**: FM to area assignments
- **vrp_jobs**: VRP computation jobs
- **vrp_assignments**: Task-to-FM assignments

### Job Status Flow

```
queued → running → ready_to_preview → finalized
          ↓
        failed
```

## VRP Solving Process

1. **Job Created**: Status = `queued`, Celery task enqueued
2. **Worker Picks Up**: Status = `running`
3. **Load Data**:
   - Tasks filtered by params (priority, max count)
   - FMs filtered by area or explicit list
4. **Determine Start Locations**:
   - Check Redis for current FM location
   - Fall back to home location from DB
5. **Build VROOM Request**:
   - Convert tasks to VROOM jobs
   - Convert FMs to VROOM vehicles
   - Priority mapping: Task priority 1 (high) → VROOM priority 100
6. **Call VROOM API**: Solve VRP with OSRM routing
7. **Normalize Results**: Convert VROOM output to DB format
8. **Save Assignments**: Create `vrp_assignments` records
9. **Update Status**: `ready_to_preview`
10. **Notify**: Publish to Redis pub/sub, WebSocket clients receive update

## Priority Handling

Tasks have priority 1-100:
- **1 = Highest priority**
- **100 = Lowest priority**

During VRP solving, priorities are inverted for VROOM:
- Task priority 1 → VROOM priority 100
- Task priority 100 → VROOM priority 1

This ensures high-priority tasks are served first in the routes.

## H3 R&D Feature

Optional hierarchical spatial indexing for task clustering.

### Enable H3

In `.env`:
```bash
H3_ENABLED=true
H3_RESOLUTION=8
```

### How It Works

1. Tasks are grouped by H3 hexagonal cells
2. FMs can be pre-assigned to clusters based on proximity
3. Reduces VROOM problem size for better performance
4. Resolution 7-10 recommended (cell size ~5km to ~60m)

### Implementation

See `app/services/h3_service.py` for:
- `cluster_tasks_by_h3()`: Group tasks by H3 cell
- `assign_fms_to_clusters()`: Simple FM-to-cluster heuristic
- `get_cluster_center()`: Get cell centroid

**Note**: This is an R&D feature. For production, implement more sophisticated clustering algorithms based on capacity, time windows, and load balancing.

## Configuration

### Environment Variables

See `.env.example` for all options:

```bash
# Database
DATABASE_URL=postgresql://vrp_user:vrp_password@db:5432/vrp_db

# Redis
REDIS_URL=redis://redis:6379/0
FM_LOCATION_TTL=600  # Cache TTL in seconds

# Services
VROOM_URL=http://vroom:3000
OSRM_URL=http://osrm:5000

# H3 Clustering
H3_ENABLED=false
H3_RESOLUTION=8
```

## Development

### Run Locally (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start services
docker-compose up db redis osrm vroom -d

# Update .env for localhost
DATABASE_URL=postgresql://vrp_user:vrp_password@localhost:5432/vrp_db
REDIS_URL=redis://localhost:6379/0
OSRM_URL=http://localhost:5000
VROOM_URL=http://localhost:3000

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.celery_worker worker --loglevel=info
```

### Create New Migration

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f celery_worker
docker-compose logs -f osrm
```

## Troubleshooting

### OSRM Not Ready

**Issue**: API returns routing errors

**Solution**:
```bash
# Check OSRM health
curl http://localhost:5000/health

# Restart OSRM
docker-compose restart osrm

# Rebuild map data
./scripts/update_map.sh
```

### VROOM Connection Refused

**Issue**: Celery worker can't reach VROOM

**Solution**:
```bash
# VROOM needs OSRM to be ready first
docker-compose restart vroom

# Check VROOM logs
docker-compose logs vroom
```

### No Tasks Assigned

**Issue**: VRP job completes but no assignments

**Possible causes**:
1. Tasks missing coordinates (check `tasks.latitude/longitude`)
2. No FMs with valid locations
3. VROOM couldn't find valid routes

**Debug**:
```bash
# Check job error field
curl http://localhost:8000/api/v1/vrp/jobs/<job-id>

# Check Celery logs
docker-compose logs celery_worker
```

### Database Connection Failed

**Solution**:
```bash
docker-compose restart db
docker-compose exec api alembic upgrade head
```

## Performance Considerations

### Task Limits

- Recommended: 1,000-5,000 tasks per job
- Maximum tested: 10,000 tasks
- For larger problems, consider:
  - H3 clustering to split into sub-problems
  - Area-based job splitting
  - Incremental optimization

### FM Limits

- Recommended: 50-200 FMs per job
- Maximum tested: 1,000 FMs
- VROOM performance degrades with 500+ vehicles

### Optimization Tips

1. **Use H3 Clustering**: Pre-group tasks by geography
2. **Filter by Area**: Assign specific areas to jobs
3. **Priority Filtering**: Split high/low priority into separate jobs
4. **Time Windows**: Implement time constraints (future feature)
5. **Incremental Updates**: Finalize and create new jobs for remaining tasks

## Production Checklist

- [ ] Update `.env` with production credentials
- [ ] Set `DEBUG=false`
- [ ] Configure proper CORS origins
- [ ] Set up SSL/TLS (reverse proxy)
- [ ] Implement proper authentication (JWT, OAuth)
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure log aggregation
- [ ] Set up database backups
- [ ] Scale Celery workers horizontally
- [ ] Use managed PostgreSQL/Redis
- [ ] Implement rate limiting
- [ ] Add job prioritization
- [ ] Set up alerting

## License

MIT

## Support

For issues, questions, or contributions, please contact the development team.

---

**Built with ❤️ using FastAPI, VROOM, and OSRM**
