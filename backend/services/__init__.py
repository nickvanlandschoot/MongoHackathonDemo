"""
Services layer for IntraceSentinel.
"""

from .npm_client import NpmRegistryClient, NpmVersionInfo, NpmPackageMetadata
from .github_client import GitHubApiClient, GitHubUserInfo
from .tarball_extractor import TarballExtractor, TarballContent
from .risk_scorer import RiskScorer, RiskAssessment
from .watcher import WatcherService
from .scheduler import WatcherScheduler
from .delta_service import DeltaService
from .package_service import get_or_create_package_with_enrichment, enrich_github_data
from .background_jobs import BackgroundJobManager, get_job_manager, Job, JobStatus

__all__ = [
    "NpmRegistryClient",
    "NpmVersionInfo",
    "NpmPackageMetadata",
    "GitHubApiClient",
    "GitHubUserInfo",
    "TarballExtractor",
    "TarballContent",
    "RiskScorer",
    "RiskAssessment",
    "WatcherService",
    "WatcherScheduler",
    "DeltaService",
    "get_or_create_package_with_enrichment",
    "enrich_github_data",
    "BackgroundJobManager",
    "get_job_manager",
    "Job",
    "JobStatus",
]