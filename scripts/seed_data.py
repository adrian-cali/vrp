#!/usr/bin/env python3
"""
Seed script to generate test data:
- 1000 FM users with home locations
- 10,000 tasks with random priorities and NCR coordinates
- Sample areas and FM assignments
"""
import random
import sys
import os
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, Task, FMHomeLocation, Area, FMAssignedArea

# Set fixed seed for reproducibility
random.seed(42)

# NCR (Metro Manila) approximate bounds
NCR_LAT_MIN = 14.35
NCR_LAT_MAX = 14.75
NCR_LNG_MIN = 120.90
NCR_LNG_MAX = 121.15

# Sample NCR cities/areas
NCR_AREAS = [
    "Manila", "Quezon City", "Makati", "Pasig", "Taguig",
    "Mandaluyong", "San Juan", "Pasay", "Paranaque", "Las Pinas",
    "Muntinlupa", "Marikina", "Caloocan", "Malabon", "Navotas", "Valenzuela"
]

# Sample street names
STREETS = [
    "EDSA", "Quezon Ave", "España Blvd", "Taft Ave", "Roxas Blvd",
    "C5 Road", "Ortigas Ave", "Shaw Blvd", "Aurora Blvd", "Marcos Highway"
]


def random_ncr_coords():
    """Generate random coordinates within NCR bounds"""
    lat = random.uniform(NCR_LAT_MIN, NCR_LAT_MAX)
    lng = random.uniform(NCR_LNG_MIN, NCR_LNG_MAX)
    return lat, lng


def random_address():
    """Generate random address"""
    num = random.randint(1, 999)
    street = random.choice(STREETS)
    area = random.choice(NCR_AREAS)
    return f"{num} {street}, {area}, Metro Manila"


def seed_data():
    """Main seeding function"""
    db = SessionLocal()
    
    try:
        print("Starting data seeding...")
        
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"Database already contains {existing_users} users.")
            response = input("Continue and add more data? (y/n): ")
            if response.lower() != 'y':
                print("Seeding cancelled.")
                return
        
        # 1. Create admin and requestor users
        print("Creating admin and requestor users...")
        admin = User(
            id=uuid4(),
            email="admin@vrp.com",
            name="Admin User",
            role="admin"
        )
        db.add(admin)
        
        requestor = User(
            id=uuid4(),
            email="requestor@vrp.com",
            name="Requestor User",
            role="requestor"
        )
        db.add(requestor)
        db.commit()
        print(f"✓ Created admin and requestor")
        
        # 2. Create areas
        print("Creating areas...")
        areas = []
        for area_name in NCR_AREAS:
            area = Area(id=uuid4(), name=area_name)
            areas.append(area)
            db.add(area)
        db.commit()
        print(f"✓ Created {len(areas)} areas")
        
        # 3. Create 1000 FM users with home locations
        print("Creating 1000 field men with home locations...")
        fm_users = []
        for i in range(1, 1001):
            fm = User(
                id=uuid4(),
                email=f"fm{i}@vrp.com",
                name=f"Field Man {i}",
                role="fm"
            )
            db.add(fm)
            fm_users.append(fm)
            
            # Create home location
            lat, lng = random_ncr_coords()
            home = FMHomeLocation(
                user_id=fm.id,
                address=random_address(),
                home_lat=lat,
                home_long=lng
            )
            db.add(home)
            
            # Assign to random area(s)
            num_areas = random.randint(1, 3)
            assigned_areas = random.sample(areas, num_areas)
            for area in assigned_areas:
                fm_area = FMAssignedArea(user_id=fm.id, area_id=area.id)
                db.add(fm_area)
            
            if (i % 100) == 0:
                db.commit()
                print(f"  ... {i}/1000 FMs created")
        
        db.commit()
        print(f"✓ Created {len(fm_users)} field men")
        
        # 4. Create 10,000 tasks
        print("Creating 10,000 tasks...")
        for i in range(1, 10001):
            lat, lng = random_ncr_coords()
            priority = random.uniform(1, 100)
            
            task = Task(
                id=uuid4(),
                address=random_address(),
                latitude=lat,
                longitude=lng,
                priority=priority,
                user_id=requestor.id,
                status="pending"
            )
            db.add(task)
            
            if (i % 1000) == 0:
                db.commit()
                print(f"  ... {i}/10000 tasks created")
        
        db.commit()
        print(f"✓ Created 10,000 tasks")
        
        print("\n" + "="*60)
        print("SEEDING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\nTest Credentials:")
        print(f"  Admin User ID:     {admin.id}")
        print(f"  Requestor User ID: {requestor.id}")
        print(f"  First FM User ID:  {fm_users[0].id}")
        print(f"\nUse these UUIDs in the X-User-Id header for API requests.")
        print("="*60)
    
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
