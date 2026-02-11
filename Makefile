.PHONY: help build up down restart logs seed update-map clean

help:
	@echo "Available commands:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs (all services)"
	@echo "  make seed        - Seed database with test data"
	@echo "  make update-map  - Update OSRM map data"
	@echo "  make clean       - Remove all containers and volumes"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "API will be available at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

seed:
	docker-compose exec api python scripts/seed_data.py

update-map:
	./scripts/update_map.sh

clean:
	docker-compose down -v
	@echo "All containers and volumes removed"
