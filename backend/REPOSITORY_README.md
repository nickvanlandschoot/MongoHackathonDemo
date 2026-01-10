# IntraceSentinel Repository Layer

This document describes the repository layer implementation for IntraceSentinel, a supply chain security monitoring system for npm packages.

## Architecture Overview

The repository layer follows a **layered architecture** pattern with:

1. **Models Layer** (`models/`) - Pydantic models for data validation and serialization
2. **Database Layer** (`database.py`) - Connection management and lifecycle
3. **Repository Layer** (`repositories/`) - Data access patterns and business queries
4. **API Layer** (`main.py`) - FastAPI endpoints with dependency injection

## Data Models

All entities share a common `Analysis` block for consistent AI-powered insights:

```python
class Analysis(BaseModel):
    summary: str                           # Human-readable summary
    reasons: list[str]                     # Supporting facts
    confidence: float                      # 0-1 confidence score
    updated_at: datetime                   # Last analysis time
    source: Literal["ai", "rule", "hybrid"]  # Analysis source
```

### Core Entities

#### 1. Package (`models/package.py`)
Top-level npm packages being monitored.

**Key Fields:**
- `name`: Package name
- `registry`: Package registry (default: "npm")
- `repo_url`: GitHub repository URL
- `owner`: Package owner
- `risk_score`: Risk score 0-100
- `scan_state`: Crawl progress tracking
- `analysis`: AI analysis block

**Repository:** `PackageRepository`

#### 2. Dependency (`models/dependency.py`)
Package graph edges representing dependencies.

**Key Fields:**
- `package_id`: Dependent package reference
- `depends_on_id`: Dependency package reference
- `spec`: Version specification (e.g., "^4.0.0")
- `dep_type`: Type (prod, dev, optional, peer)
- `depth`: Dependency depth in graph
- `analysis`: AI analysis with `usage_likelihood` and `runtime_relevance`

**Repository:** `DependencyRepository`

#### 3. Identity (`models/identity.py`)
Contributors and maintainers (npm-first).

**Key Fields:**
- `kind`: Identity type (npm, github, email_domain)
- `handle`: Username/handle
- `email_domain`: Email domain
- `affiliation_tag`: Affiliation (corporate, academic, anonymous)
- `country`: Country code
- `risk_score`: Risk score 0-100
- `analysis`: AI analysis block

**Repository:** `IdentityRepository`

#### 4. PackageIdentity (`models/package_identity.py`)
Links identities to packages with permissions (who can ship what).

**Key Fields:**
- `package_id`: Package reference
- `identity_id`: Identity reference
- `role`: Role (owner, maintainer, contributor)
- `permission_level`: Permission (publish, triage, unknown)
- `trust_score`: Trust score 0-100
- `analysis`: AI analysis block

**Repository:** `PackageIdentityRepository`

#### 5. PackageRelease (`models/package_release.py`)
Primary event stream for npm releases (core watcher feed).

**Key Fields:**
- `package_id`: Package reference
- `version`: Release version
- `previous_version`: Previous version for comparison
- `published_by`: Identity who published
- `publish_timestamp`: Publication time
- `tarball_integrity`: npm integrity/shasum
- `dist_tags`: Distribution tags (latest, next, etc.)
- `risk_score`: Risk score 0-100
- `analysis`: AI analysis block

**Repository:** `PackageReleaseRepository`

#### 6. PackageDelta (`models/package_delta.py`)
Version-to-version diffs (replaces PRs for MVP).

**Key Fields:**
- `package_id`: Package reference
- `from_version`: Source version
- `to_version`: Target version
- `signals`: Detected changes (files, scripts, network calls, obfuscation)
- `risk_score`: Risk score 0-100
- `analysis`: AI analysis block

**Signals:**
- `added_files`, `removed_files`, `changed_files`
- `has_install_scripts`, `touched_install_scripts`
- `has_native_code`
- `added_network_calls`
- `minified_or_obfuscated_delta`

**Repository:** `PackageDeltaRepository`

#### 7. RiskAlert (`models/risk_alert.py`)
Security alerts and decisions.

**Key Fields:**
- `package_id`: Package reference
- `identity_id`: Related identity (optional)
- `release_id`: Triggering release (optional)
- `delta_id`: Triggering delta (optional)
- `reason`: Human-readable reason
- `severity`: Severity score 0-100
- `status`: Status (open, investigated, resolved)
- `analysis`: AI analysis block

**Repository:** `RiskAlertRepository`

#### 8. GitHubEvent (`models/github_event.py`)
Optional GitHub enrichment data.

**Key Fields:**
- `package_id`: Package reference
- `type`: Event type (pr, commit, release, security_advisory)
- `url`: GitHub URL
- `actor`: GitHub actor/user
- `analysis`: AI analysis block

**Repository:** `GitHubEventRepository`

## Repository Pattern

### Base Repository

The `BaseRepository[T]` class provides common CRUD operations:

```python
# Create
entity = repo.create(entity)

# Read
entity = repo.find_by_id(entity_id)
entity = repo.find_one({"name": "express"})
entities = repo.find_many({"risk_score": {"$gte": 70}}, skip=0, limit=100)
entities = repo.find_all(skip=0, limit=100)

# Update
entity = repo.update(entity_id, {"risk_score": 85.0})
entity = repo.update_one({"name": "express"}, {"risk_score": 85.0})

# Delete
success = repo.delete(entity_id)
success = repo.delete_one({"name": "express"})
count = repo.delete_many({"risk_score": {"$lt": 10}})

# Count & Existence
count = repo.count({"status": "open"})
exists = repo.exists({"name": "express"})
```

### Custom Repository Methods

Each repository extends `BaseRepository` with domain-specific queries:

**PackageRepository:**
- `find_by_name(name)` - Find package by name
- `find_by_registry(registry)` - Find packages by registry
- `find_by_owner(owner)` - Find packages by owner
- `find_high_risk(threshold)` - Find high-risk packages
- `find_needs_scan()` - Find packages needing scan

**DependencyRepository:**
- `find_by_package(package_id)` - Find package dependencies
- `find_dependents(package_id)` - Find packages depending on this one
- `find_by_type(package_id, dep_type)` - Find dependencies by type
- `find_production_deps(package_id)` - Find production dependencies

**IdentityRepository:**
- `find_by_handle(handle, kind)` - Find identity by handle
- `find_by_kind(kind)` - Find identities by kind
- `find_by_affiliation(affiliation_tag)` - Find by affiliation
- `find_high_risk(threshold)` - Find high-risk identities

**PackageIdentityRepository:**
- `find_by_package(package_id)` - Find identities for package
- `find_by_identity(identity_id)` - Find packages for identity
- `find_publishers(package_id)` - Find identities with publish rights
- `find_by_role(package_id, role)` - Find by role

**PackageReleaseRepository:**
- `find_by_package(package_id)` - Find releases for package
- `find_by_version(package_id, version)` - Find specific version
- `find_by_publisher(identity_id)` - Find by publisher
- `find_recent(hours)` - Find recent releases
- `find_high_risk(threshold)` - Find high-risk releases

**PackageDeltaRepository:**
- `find_by_package(package_id)` - Find deltas for package
- `find_delta(package_id, from_version, to_version)` - Find specific delta
- `find_with_install_scripts()` - Find deltas touching install scripts
- `find_with_network_calls()` - Find deltas adding network calls
- `find_obfuscated()` - Find deltas with obfuscated code
- `find_high_risk(threshold)` - Find high-risk deltas

**RiskAlertRepository:**
- `find_by_package(package_id)` - Find alerts for package
- `find_by_status(status)` - Find by status
- `find_open_alerts()` - Find open alerts
- `find_by_release(release_id)` - Find alerts by release
- `find_by_delta(delta_id)` - Find alerts by delta
- `find_high_severity(threshold)` - Find high-severity alerts

**GitHubEventRepository:**
- `find_by_package(package_id)` - Find events for package
- `find_by_type(event_type)` - Find by event type
- `find_security_advisories(package_id)` - Find security advisories
- `find_by_actor(actor)` - Find by GitHub actor

## Database Connection Management

The `DatabaseManager` singleton manages MongoDB connections:

```python
from database import get_database_manager, get_database

# Get manager instance
db_manager = get_database_manager()

# Connect (done automatically at startup)
db_manager.connect()

# Get database for repositories
db = db_manager.database

# Disconnect (done automatically at shutdown)
db_manager.disconnect()
```

## Dependency Injection

FastAPI dependency injection is used for repositories:

```python
from fastapi import Depends
from database import get_database
from repositories import PackageRepository

def get_package_repository(db=Depends(get_database)) -> PackageRepository:
    return PackageRepository(db)

@app.get("/packages/{name}")
async def get_package(
    name: str,
    repo: PackageRepository = Depends(get_package_repository)
):
    package = repo.find_by_name(name)
    return package
```

## API Examples

The `main.py` file includes example endpoints:

### Create Package
```bash
POST /packages?name=express&registry=npm
```

### Get Package
```bash
GET /packages/express
```

### List Packages
```bash
GET /packages?skip=0&limit=100
```

### List High-Risk Packages
```bash
GET /packages/high-risk?threshold=70.0&skip=0&limit=100
```

## Usage Examples

### Creating a Package

```python
from models import Analysis, Package
from repositories import PackageRepository

# Create package
package = Package(
    name="express",
    registry="npm",
    repo_url="https://github.com/expressjs/express",
    analysis=Analysis(
        summary="Popular web framework",
        reasons=["30M+ weekly downloads", "Verified maintainers"],
        confidence=0.95,
        source="hybrid"
    )
)

# Save to database
repo = PackageRepository(db)
created = repo.create(package)
```

### Finding High-Risk Releases

```python
from repositories import PackageReleaseRepository

repo = PackageReleaseRepository(db)

# Find recent high-risk releases
risky_releases = repo.find_high_risk(threshold=80.0, limit=10)

for release in risky_releases:
    print(f"{release.version}: {release.analysis.summary}")
    print(f"Risk: {release.risk_score}, Confidence: {release.analysis.confidence}")
```

### Creating Risk Alerts

```python
from models import Analysis, RiskAlert
from repositories import RiskAlertRepository

alert = RiskAlert(
    package_id=package_id,
    release_id=release_id,
    delta_id=delta_id,
    reason="Obfuscated code added in patch release",
    severity=85.0,
    status="open",
    analysis=Analysis(
        summary="High-risk obfuscated code introduced",
        reasons=[
            "Minified code in non-minified package",
            "No changelog entry",
            "Published outside normal schedule"
        ],
        confidence=0.91,
        source="hybrid"
    )
)

repo = RiskAlertRepository(db)
repo.create(alert)
```

## Database Collections

The following MongoDB collections are used:

- `packages` - Top-level packages
- `dependencies` - Package dependencies
- `identities` - Maintainers/contributors
- `package_identities` - Package-identity relationships
- `package_releases` - Release events
- `package_deltas` - Version diffs
- `risk_alerts` - Security alerts
- `github_events` - GitHub events (optional)

## Best Practices

1. **Always use repositories** - Never access MongoDB collections directly
2. **Use dependency injection** - Inject repositories via FastAPI dependencies
3. **Include analysis blocks** - Every entity must have an analysis
4. **Handle ObjectIds properly** - Repositories accept both string and ObjectId
5. **Use pagination** - Always use skip/limit for list queries
6. **Validate with Pydantic** - Models provide automatic validation
7. **Follow the analysis pattern** - Maintain consistent analysis structure

## Testing

To test the repository layer:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the backend
cd backend
uvicorn main:app --reload

# Test endpoints
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/packages?name=express"
curl http://localhost:8000/packages/express
```

## Next Steps

1. **Add indexes** - Create MongoDB indexes for query optimization
2. **Add validation** - Implement pre-save validation hooks
3. **Add caching** - Implement caching layer for frequent queries
4. **Add transactions** - Use MongoDB transactions for multi-document operations
5. **Add audit logging** - Track all database modifications
6. **Add bulk operations** - Implement bulk insert/update for efficiency
