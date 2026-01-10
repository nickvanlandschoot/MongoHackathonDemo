from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import env
from database import DatabaseManager, get_database, get_database_manager
from models import Analysis, Package
from repositories import PackageRepository

app = FastAPI(
    title="IntraceSentinel API",
    description="Supply chain security monitoring API",
    version="1.0.0",
)

# Initialize database manager
db_manager = get_database_manager()


def get_package_repository(db=Depends(get_database)) -> PackageRepository:
    """Dependency injection for PackageRepository."""
    return PackageRepository(db)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    try:
        db_manager.connect()
        db_manager.client.admin.command("ping")
        print("MongoDB connection successful")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    db_manager.disconnect()
    print("MongoDB connection closed")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to IntraceSentinel API",
        "version": "1.0.0",
        "description": "Supply chain security monitoring for npm packages",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db_manager.client.admin.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {"status": "healthy", "database": db_status, "timestamp": datetime.utcnow()}


# Example: Repository usage endpoints
@app.post("/packages", response_model=Package)
async def create_package(
    name: str,
    registry: str = "npm",
    repo: PackageRepository = Depends(get_package_repository),
):
    """
    Create a new package.

    Example usage demonstrating the repository layer.
    """
    # Check if package already exists
    existing = repo.find_by_name(name)
    if existing:
        raise HTTPException(status_code=400, detail="Package already exists")

    # Create package with analysis
    package = Package(
        name=name,
        registry=registry,
        analysis=Analysis(
            summary=f"Package {name} registered for monitoring",
            reasons=["Newly registered package"],
            confidence=1.0,
            source="rule",
        ),
    )

    created = repo.create(package)
    return created


@app.get("/packages/{name}", response_model=Package)
async def get_package(name: str, repo: PackageRepository = Depends(get_package_repository)):
    """
    Get package by name.

    Example usage demonstrating the repository layer.
    """
    package = repo.find_by_name(name)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    return package


@app.get("/packages", response_model=list[Package])
async def list_packages(
    skip: int = 0, limit: int = 100, repo: PackageRepository = Depends(get_package_repository)
):
    """
    List all packages.

    Example usage demonstrating the repository layer.
    """
    packages = repo.find_all(skip=skip, limit=limit)
    return packages


@app.get("/packages/high-risk", response_model=list[Package])
async def list_high_risk_packages(
    threshold: float = 70.0,
    skip: int = 0,
    limit: int = 100,
    repo: PackageRepository = Depends(get_package_repository),
):
    """
    List high-risk packages.

    Example usage demonstrating repository custom queries.
    """
    packages = repo.find_high_risk(threshold=threshold, skip=skip, limit=limit)
    return packages
