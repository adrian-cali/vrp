# 🚀 VRP Application - Running and Ready!

## ✅ Status: ALL SERVICES RUNNING

Your VRP application is successfully deployed and running!

---

## 📍 Application URLs

### **FastAPI Documentation (Interactive)**
🔗 **Swagger UI**: http://localhost:8001/docs
- Interactive API documentation
- Try out all endpoints
- See request/response schemas

🔗 **ReDoc**: http://localhost:8001/redoc
- Alternative documentation view
- Clean, readable format

### **API Base URL**
🔗 http://localhost:8001/

### **Health Check**
🔗 http://localhost:8001/health

---

## 🔑 Test Credentials

Use these UUIDs in the `X-User-Id` header for API requests:

```
Admin User ID:     53011549-b9be-47f6-adf4-fddb17cc31a8
Requestor User ID: 24e7d141-6d7c-4e9b-992e-89c944f92ad6
First FM User ID:  3372aaa5-3c76-4443-8d94-0dc70ef98f0b
```

---

## 🧪 Quick API Tests

### 1. Test Health Endpoint
```bash
curl http://localhost:8001/health
```

### 2. Update FM Location (as Field Man)
```bash
curl -X POST http://localhost:8001/api/v1/fm/location \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 3372aaa5-3c76-4443-8d94-0dc70ef98f0b" \
  -d '{
    "current_lat": 14.5995,
    "current_long": 120.9842
  }'
```

### 3. Create VRP Job (as Requestor)
```bash
curl -X POST http://localhost:8001/api/v1/vrp/jobs \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6" \
  -d '{
    "strategy": "manual_area",
    "max_tasks": 100,
    "priority_min": 1,
    "priority_max": 50
  }'
```

### 4. List VRP Jobs
```bash
curl http://localhost:8001/api/v1/vrp/jobs \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6"
```

---

## 📊 Database Status

✅ **1,000 Field Men** with home locations in Metro Manila
✅ **10,000 Tasks** with priorities 1-100 and random NCR coordinates
✅ **16 Areas** (NCR cities)
✅ All FMs assigned to random areas

---

## 🐳 Running Services

| Service | Status | Port | URL |
|---------|--------|------|-----|
| **FastAPI** | ✅ Running | 8001 → 8000 | http://localhost:8001 |
| **PostgreSQL** | ✅ Running | 5433 → 5432 | localhost:5433 |
| **Redis** | ✅ Running | 6380 → 6379 | localhost:6380 |
| **Celery Worker** | ✅ Running | - | Background |
| **VROOM** | ✅ Running | 3001 → 3000 | http://localhost:3001 |
| **OSRM** | ⚠️ Needs Setup | 5002 → 5000 | - |

---

## ⚠️ Important Note: OSRM Setup Required

The OSRM routing engine needs map data to be processed. To enable VRP solving:

### Option 1: Run Map Update Script
```bash
cd /home/adrian/vrp
chmod +x scripts/update_map.sh
./scripts/update_map.sh
```

This will:
- Download latest Philippines map (~150MB)
- Process it with OSRM (takes 10-20 minutes)
- Generate routing files

### Option 2: Manual OSRM Setup
```bash
# Download Philippines map
cd /home/adrian/vrp/vroom_ors/osrm-philippines
wget https://download.geofabrik.de/asia/philippines-latest.osm.pbf

# Process with OSRM
docker run --rm -v "$PWD:/data" osrm/osrm-backend:latest \
  osrm-extract -p /opt/car.lua /data/philippines-latest.osm.pbf

docker run --rm -v "$PWD:/data" osrm/osrm-backend:latest \
  osrm-partition /data/philippines-latest.osrm

docker run --rm -v "$PWD:/data" osrm/osrm-backend:latest \
  osrm-customize /data/philippines-latest.osrm

# Restart services
cd /home/adrian/vrp
docker-compose restart osrm vroom
```

**Until OSRM is set up, VRP job solving will fail (but all other API endpoints work!)**

---

## 🎮 Using the API

### Via Swagger UI (Recommended)

1. Open http://localhost:8001/docs
2. Click the **"Authorize"** button (if available) or add headers manually
3. For each request, add Header: `X-User-Id: <uuid from above>`
4. Try the endpoints interactively!

### Via curl

All endpoints require the `X-User-Id` header. Examples:

**List Jobs:**
```bash
curl http://localhost:8001/api/v1/vrp/jobs?page=1&page_size=10 \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6"
```

**Get Job Details:**
```bash
curl http://localhost:8001/api/v1/vrp/jobs/{job_id} \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6"
```

**Preview Job (HTML):**
Open in browser:
```
http://localhost:8001/api/v1/vrp/jobs/{job_id}/preview
```
(Add `?user_id=24e7d141-6d7c-4e9b-992e-89c944f92ad6` if using browser)

**Finalize Job:**
```bash
curl -X POST http://localhost:8001/api/v1/vrp/jobs/{job_id}/finalize \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6"
```

---

## 🔍 View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f celery_worker
docker-compose logs -f db
```

---

## 🛑 Stop/Restart Services

```bash
# Stop all
docker-compose down

# Restart all
docker-compose restart

# Start all
docker-compose up -d
```

---

## 📚 Available Endpoints

### VRP Endpoints
- `POST /api/v1/vrp/jobs` - Create VRP job
- `POST /api/v1/vrp/plan-ahead` - Same as above (convenience)
- `GET /api/v1/vrp/jobs` - List jobs with pagination
- `GET /api/v1/vrp/jobs/{job_id}` - Get job details
- `GET /api/v1/vrp/jobs/{job_id}/preview` - HTML preview
- `POST /api/v1/vrp/jobs/{job_id}/finalize` - Finalize assignments

### Field Men Endpoints
- `POST /api/v1/fm/location` - Update current location

### WebSocket
- `WS /api/v1/ws/vrp-jobs/{job_id}` - Real-time job status updates

### System
- `GET /` - API info
- `GET /health` - Health check

---

## 🎯 Next Steps

1. ✅ **Explore the API documentation**: http://localhost:8001/docs
2. ⚠️ **Set up OSRM** (if you want to test VRP solving)
3. ✅ **Test the endpoints** using the credentials above
4. ✅ **Check out the preview page** after creating a job
5. ✅ **Try the WebSocket** for real-time updates

---

## 💡 Tips

- Use **Swagger UI** for easiest testing: http://localhost:8001/docs
- All data is **pre-seeded** and ready to use
- The **preview page** shows beautiful HTML with grouped tasks
- **WebSocket** notifications work in real-time
- Check **logs** if something doesn't work: `docker-compose logs -f api`

---

**Enjoy exploring your VRP application!** 🚀
