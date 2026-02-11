# VRP System - Quick Test Guide

## 🚀 Starting the System

```bash
cd /home/adrian/vrp
docker-compose up -d
```

Wait ~10 seconds for all services to be healthy.

### Check Service Status:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Should see:
- vrp-api-1 (Up, port 8001)
- vrp-celery_worker-1 (Up)
- vrp-db-1 (Up, healthy)
- vrp-redis-1 (Up, healthy)
- vrp-vroom-1 (Up, healthy)

---

## 🧪 Testing the VRP System

### Test 1: Create a VRP Job (200 tasks)

```bash
curl -X POST http://localhost:8001/api/v1/vrp/jobs \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6" \
  -d '{
    "requestor_id": "24e7d141-6d7c-4e9b-992e-89c944f92ad6",
    "optimization_params": {
      "max_tasks": 200
    }
  }'
```

**Expected Response**:
```json
{
  "job_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "queued",
  "created_at": "2026-02-10T..."
}
```

**Save the job_id for next steps!**

---

### Test 2: Check Job Status

Replace `<JOB_ID>` with your actual job ID:

```bash
curl -s http://localhost:8001/api/v1/vrp/jobs/<JOB_ID> \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6" | jq
```

**Status Flow**:
1. `queued` → Job created, waiting for worker
2. `running` → Worker processing (10-15 seconds)
3. `ready_to_preview` → ✅ Success! Assignments created
4. `failed` → ❌ Error (check error_message field)

**Successful Response Example**:
```json
{
  "id": "...",
  "status": "ready_to_preview",
  "result": {
    "summary": {
      "total_tasks_assigned": 10000,
      "unassigned_tasks": 0,
      "total_distance": 5627000,
      "total_duration": 562700,
      "fm_utilization": {
        "fm_id_1": 12,
        "fm_id_2": 8,
        ...
      }
    },
    "assignments": [...]
  }
}
```

---

### Test 3: Check Job Metrics

Get summary stats only:

```bash
curl -s http://localhost:8001/api/v1/vrp/jobs/<JOB_ID> \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6" | \
  jq '{
    status: .status,
    assigned: .result.summary.total_tasks_assigned,
    unassigned: .result.summary.unassigned_tasks,
    fms_used: (.result.summary.fm_utilization | length),
    distance_km: ((.result.summary.total_distance // 0) / 1000 | round)
  }'
```

**Expected Output**:
```json
{
  "status": "ready_to_preview",
  "assigned": 10000,
  "unassigned": 0,
  "fms_used": 982,
  "distance_km": 5627
}
```

---

### Test 4: View H3 Clustering

See how tasks are grouped into geographic hexagons:

```bash
curl -s 'http://localhost:8001/h3_clusters?limit=100' | jq '.clusters[:5]'
```

**Response**:
```json
[
  {
    "h3_cell": "88694ed8...",
    "center_lat": 14.5413,
    "center_lng": 120.9111,
    "task_count": 16,
    "fm_count": 1
  },
  ...
]
```

---

### Test 5: View All Available Tasks

```bash
curl -s 'http://localhost:8001/tasks?limit=10' | jq '.[:3]'
```

**Response**:
```json
[
  {
    "id": "...",
    "title": "Task #1",
    "priority": 45,
    "latitude": 14.5234,
    "longitude": 121.0123,
    "status": "pending"
  },
  ...
]
```

---

### Test 6: View FM Home Locations

```bash
curl -s 'http://localhost:8001/fm_home_locations' | jq '.[:3]'
```

**Response**:
```json
[
  {
    "fm_user_id": "...",
    "home_lat": 14.5500,
    "home_long": 121.0200
  },
  ...
]
```

---

## 📊 Testing Different Scenarios

### Small Job (50 tasks):
```bash
curl -X POST http://localhost:8001/api/v1/vrp/jobs \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6" \
  -d '{"requestor_id": "24e7d141-6d7c-4e9b-992e-89c944f92ad6", "optimization_params": {"max_tasks": 50}}'
```

### Large Job (1000 tasks):
```bash
curl -X POST http://localhost:8001/api/v1/vrp/jobs \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6" \
  -d '{"requestor_id": "24e7d141-6d7c-4e9b-992e-89c944f92ad6", "optimization_params": {"max_tasks": 1000}}'
```

### Maximum Job (10,000 tasks):
```bash
curl -X POST http://localhost:8001/api/v1/vrp/jobs \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 24e7d141-6d7c-4e9b-992e-89c944f92ad6" \
  -d '{"requestor_id": "24e7d141-6d7c-4e9b-992e-89c944f92ad6", "optimization_params": {"max_tasks": 10000}}'
```

**Processing Times**:
- 50 tasks: ~5 seconds
- 200 tasks: ~8 seconds
- 1,000 tasks: ~10 seconds
- 10,000 tasks: ~12 seconds

---

## 🌐 Web Interface

Open in browser: **http://localhost:8001**

### Available Tabs:
1. **Jobs**: View all VRP jobs and their status
2. **Create**: Create new VRP job (web form)
3. **FM Location**: View field manager locations
4. **Map View**: See all 10,000 tasks on interactive map

### Map Features:
- Color-coded markers by priority:
  - 🔴 Red: High priority (1-33)
  - 🟡 Yellow: Medium priority (34-66)
  - 🟢 Green: Low priority (67-100)
- Zoom/pan with mouse
- Click markers for task details
- Real-time statistics

---

## 🔍 Monitoring & Logs

### Check Celery Worker Logs:
```bash
docker logs vrp-celery_worker-1 --tail 50
```

**Look for**:
- "H3 clustering enabled: grouping X tasks..."
- "Created X H3 clusters (resolution 8)"
- "Using greedy assignment for X tasks, Y FMs"
- "Greedy assignment complete: X assigned, Y unassigned"

### Check API Logs:
```bash
docker logs vrp-api-1 --tail 50
```

### Check Health:
```bash
curl http://localhost:8001/health
```

Expected: `{"status":"healthy"}`

---

## 📈 Performance Benchmarks

Based on tested results:

| Tasks | FMs Used | Distance (km) | Processing Time | Assignment Rate |
|-------|----------|---------------|-----------------|-----------------|
| 50    | ~50      | ~300          | ~5 sec          | 100%            |
| 200   | ~150     | ~1,200        | ~8 sec          | 100%            |
| 1,000 | ~500     | ~3,000        | ~10 sec         | 100%            |
| 10,000| ~982     | ~5,627        | ~12 sec         | 100%            |

**H3 Clustering Performance**:
- 10,000 tasks → 1,657 clusters (~6 tasks/cluster avg)
- Clustering time: ~2 seconds
- Resolution 8: ~0.46 km² hexagons

---

## 🐛 Troubleshooting

### Job stays "running" for long time:
```bash
docker logs vrp-celery_worker-1 --tail 100 | grep ERROR
```

### Check if DB is accessible:
```bash
docker exec vrp-db-1 psql -U vrp_user -d vrp_db -c "SELECT COUNT(*) FROM tasks;"
```

Expected: `10000`

### Check if Redis is working:
```bash
docker exec vrp-redis-1 redis-cli PING
```

Expected: `PONG`

### Restart services:
```bash
cd /home/adrian/vrp
docker-compose restart
```

### Full restart (if needed):
```bash
cd /home/adrian/vrp
docker-compose down
docker-compose up -d
```

---

## ✅ Success Criteria

A successful test should show:
- ✅ Job reaches `ready_to_preview` status
- ✅ 100% task assignment rate (unassigned_tasks = 0)
- ✅ Reasonable number of FMs used (~10% of task count)
- ✅ Distance calculated (> 0)
- ✅ Processing time < 15 seconds for 10K tasks

---

## 🎯 Next Steps After Testing

1. **View Results**: Check the web UI at http://localhost:8001
2. **API Integration**: Use the job_id to fetch assignments
3. **Customize**: Adjust H3_RESOLUTION in `.env` (7-9) for different cluster sizes
4. **Scale**: Test with more tasks by modifying data seeding
5. **Deploy**: Consider production deployment with proper authentication

---

## 📞 Getting Help

If you encounter issues:
1. Check container logs (`docker logs <container_name>`)
2. Verify all services are `Up` and `healthy`
3. Check `.env` file configuration
4. Review `PROGRESS_REPORT.md` for system details
5. Check H3_GUIDE.md for clustering documentation

---

**Pro Tip**: Save your successful job_id values to compare results across different max_tasks settings!
