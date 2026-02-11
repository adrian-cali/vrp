# VRP Application - Complete Project Structure

## 📁 Directory Structure

```
vrp/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Pydantic settings
│   ├── database.py                # SQLAlchemy setup
│   ├── models.py                  # Database models
│   ├── schemas.py                 # Pydantic schemas
│   ├── dependencies.py            # FastAPI dependencies
│   ├── celery_worker.py           # Celery tasks
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── vrp.py                 # VRP job endpoints
│   │   ├── preview.py             # HTML preview endpoint
│   │   ├── fm.py                  # Field men endpoints
│   │   └── websocket.py           # WebSocket endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── db_service.py          # Database operations
│   │   ├── redis_service.py       # Redis operations
│   │   ├── vroom_service.py       # VROOM integration
│   │   └── h3_service.py          # H3 clustering (optional)
│   └── templates/
│       ├── preview.html           # Job preview page
│       └── not_ready.html         # Not ready page
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_init.py            # Initial schema migration
├── scripts/
│   ├── seed_data.py               # Database seeding script
│   └── update_map.sh              # OSRM map update script
├── vroom_ors/                     # Existing VROOM/OSRM setup
│   ├── docker-compose.yml
│   └── osrm-philippines/          # OSRM data directory
├── .env                           # Environment variables
├── .env.example                   # Example environment config
├── .gitignore
├── alembic.ini                    # Alembic configuration
├── docker-compose.yml             # Docker services
├── Dockerfile                     # API container
├── Makefile                       # Convenience commands
├── README.md                      # Complete documentation
└── requirements.txt               # Python dependencies
```

## 🎯 Key Components

### 1. Database Models (app/models.py)
- ✅ Users (admin, requestor, fm roles)
- ✅ Tasks (with priority, coordinates, status)
- ✅ FM Home Locations
- ✅ Areas
- ✅ FM Assigned Areas
- ✅ VRP Jobs
- ✅ VRP Assignments

### 2. API Endpoints (app/routers/)
- ✅ POST `/api/v1/vrp/plan-ahead` - Convenience endpoint
- ✅ POST `/api/v1/vrp/jobs` - Create VRP job
- ✅ GET `/api/v1/vrp/jobs` - List jobs with pagination
- ✅ GET `/api/v1/vrp/jobs/{job_id}` - Get job details
- ✅ GET `/api/v1/vrp/jobs/{job_id}/preview` - HTML preview
- ✅ POST `/api/v1/vrp/jobs/{job_id}/finalize` - Finalize (idempotent)
- ✅ POST `/api/v1/fm/location` - Update FM location
- ✅ WS `/api/v1/ws/vrp-jobs/{job_id}` - WebSocket notifications

### 3. Services (app/services/)
- ✅ **Redis Service**: FM location caching + pub/sub
- ✅ **DB Service**: All database operations
- ✅ **VROOM Service**: VRP solving integration
- ✅ **H3 Service**: Optional clustering (R&D)

### 4. Celery Worker (app/celery_worker.py)
- ✅ Task: `solve_vrp(job_id)`
- ✅ Load tasks + FMs
- ✅ Determine start locations (Redis current or DB home)
- ✅ Build VROOM payload
- ✅ Call VROOM API
- ✅ Normalize and save assignments
- ✅ Publish status notifications

### 5. Docker Services (docker-compose.yml)
- ✅ PostgreSQL 15
- ✅ Redis 7
- ✅ OSRM routing engine
- ✅ VROOM VRP solver
- ✅ FastAPI API service
- ✅ Celery worker

### 6. Scripts
- ✅ **seed_data.py**: Generate 1000 FMs + 10,000 tasks
- ✅ **update_map.sh**: Download and build OSRM Philippines map

### 7. HTML Templates
- ✅ **preview.html**: Beautiful job preview with FM grouping
- ✅ **not_ready.html**: Job not ready page

## 🚀 Quick Start Commands

```bash
# Setup
make update-map    # First time: update OSRM map
make up            # Start all services
make seed          # Seed test data

# Development
make logs          # View logs
make restart       # Restart services

# Cleanup
make down          # Stop services
make clean         # Remove everything
```

## ✅ Acceptance Criteria Status

All requirements met:

- ✅ `docker-compose up` starts all services without manual intervention
- ✅ Seed script generates 1000 FMs + 10,000 tasks successfully
- ✅ Creating VRP job returns job_id and transitions to `ready_to_preview`
- ✅ Preview endpoint returns grouped HTML with ordered tasks
- ✅ Finalize endpoint is idempotent
- ✅ WebSocket receives notifications on status changes
- ✅ OSRM map update instructions documented and working

## 📊 Data Flow

```
1. Create Job (API) → queued
   ↓
2. Celery picks up → running
   ↓
3. Load tasks + FMs from DB
   ↓
4. Check Redis for FM current locations
   ↓
5. Build VROOM request
   ↓
6. Call VROOM with OSRM routing
   ↓
7. Normalize results
   ↓
8. Save assignments to DB
   ↓
9. Update job status → ready_to_preview
   ↓
10. Publish Redis notification
   ↓
11. WebSocket clients notified
   ↓
12. Preview in browser
   ↓
13. Finalize → tasks marked finalized
```

## 🎨 Features

### Priority Handling
- Tasks: 1 (highest) to 100 (lowest)
- Converted for VROOM: inverted mapping
- Preview shows color-coded priorities

### FM Location Strategy
1. Check Redis cache (TTL 10 min)
2. Fall back to home location from DB
3. Skip FMs without any location

### WebSocket Notifications
- Real-time job status updates
- Connects per job
- Auto-closes on finalize/failed

### HTML Preview
- Grouped by FM
- Ordered by sequence
- Shows stats: distance, time, task count
- Color-coded priorities
- Responsive design

### Optional H3 Clustering
- Enable via `H3_ENABLED=true`
- Configurable resolution
- Pre-groups tasks by geography
- Simple FM-to-cluster assignment
- Documented for future enhancement

## 🔧 Configuration

All configuration via `.env` file:
- Database credentials
- Redis settings
- Service URLs (VROOM, OSRM)
- FM location cache TTL
- H3 settings

## 📝 API Documentation

Interactive docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testing

Test with provided user IDs from seed script:

```bash
# Save these from seed output
REQUESTOR_ID=<uuid-from-seed>
FM_ID=<uuid-from-seed>

# Test FM location update
curl -X POST http://localhost:8000/api/v1/fm/location \
  -H "X-User-Id: $FM_ID" \
  -H "Content-Type: application/json" \
  -d '{"current_lat": 14.5995, "current_long": 120.9842}'

# Create VRP job
JOB_ID=$(curl -X POST http://localhost:8000/api/v1/vrp/jobs \
  -H "X-User-Id: $REQUESTOR_ID" \
  -H "Content-Type: application/json" \
  -d '{"max_tasks": 100}' | jq -r '.job_id')

# Wait for completion (or use WebSocket)
sleep 30

# Preview
open "http://localhost:8000/api/v1/vrp/jobs/$JOB_ID/preview?user_id=$REQUESTOR_ID"

# Finalize
curl -X POST "http://localhost:8000/api/v1/vrp/jobs/$JOB_ID/finalize" \
  -H "X-User-Id: $REQUESTOR_ID"
```

## 📦 Dependencies

See `requirements.txt` for complete list:
- fastapi
- uvicorn
- sqlalchemy
- alembic
- psycopg2-binary
- redis
- celery
- httpx
- h3
- jinja2
- websockets

## 🎓 Architecture Decisions

1. **UUID Primary Keys**: Better for distributed systems
2. **JSONB for params/result**: Flexible job configuration
3. **Redis for current locations**: Fast, TTL-based cache
4. **Celery for async**: Decouples API from long-running tasks
5. **Pub/Sub for notifications**: Real-time updates to WebSocket
6. **Priority inversion**: Maps our 1=high to VROOM's higher=better
7. **Idempotent finalize**: Safe to call multiple times
8. **H3 as optional**: Experimental, not required for core functionality

## 🏆 Production Ready Features

- Health check endpoint
- Proper error handling
- Database migrations
- Connection pooling
- Docker healthchecks
- Service dependencies
- Comprehensive logging
- Configurable via environment
- Idempotent operations
- WebSocket with auth check

## 📚 Further Enhancements (Future)

- JWT authentication
- Role-based access control
- Task time windows
- Vehicle capacity constraints
- Multi-depot support
- Real-time route tracking
- Mobile app integration
- Analytics dashboard
- Job scheduling
- Cost optimization
- Driver breaks
- Traffic-aware routing (OSRM supports this)

---

**Built and ready to deploy!** 🚀
