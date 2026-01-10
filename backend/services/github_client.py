"""
GitHub API client for user enrichment.
"""

from datetime import datetime, timezone
from typing import Optional, List
from dataclasses import dataclass
import re

import requests

import env


@dataclass
class GitHubUserInfo:
    """GitHub user profile information."""

    username: str
    created_at: datetime
    email: Optional[str]
    company: Optional[str]
    location: Optional[str]
    public_repos: int
    followers: int
    organizations: List[str]
    is_new_account: bool  # Created within last 90 days


class GitHubApiClient:
    """Client for GitHub API interactions."""

    BASE_URL = "https://api.github.com"
    TIMEOUT = 30
    NEW_ACCOUNT_THRESHOLD_DAYS = 90

    def __init__(self, token: Optional[str] = None):
        self._token = token or env.GITHUB_PAT
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "IntraceSentinel/1.0",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if self._token:
            self._session.headers["Authorization"] = f"Bearer {self._token}"

    def get_user(self, username: str) -> Optional[GitHubUserInfo]:
        """
        Fetch GitHub user profile.

        Args:
            username: GitHub username

        Returns:
            GitHubUserInfo or None if not found
        """
        url = f"{self.BASE_URL}/users/{username}"

        try:
            response = self._session.get(url, timeout=self.TIMEOUT)
            if response.status_code == 404:
                print(f"[github_client] User not found: {username}")
                return None
            response.raise_for_status()
            data = response.json()

            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

            # Fetch organizations
            orgs = self._get_user_orgs(username)

            # Calculate if new account
            now = datetime.now(timezone.utc)
            account_age = now - created_at
            is_new = account_age.days < self.NEW_ACCOUNT_THRESHOLD_DAYS

            return GitHubUserInfo(
                username=data["login"],
                created_at=created_at,
                email=data.get("email"),
                company=data.get("company"),
                location=data.get("location"),
                public_repos=data.get("public_repos", 0),
                followers=data.get("followers", 0),
                organizations=orgs,
                is_new_account=is_new,
            )
        except requests.RequestException as e:
            print(f"[github_client] ERROR: Failed to fetch GitHub user {username}: {e}")
            return None

    def _get_user_orgs(self, username: str) -> List[str]:
        """Fetch user's public organizations."""
        url = f"{self.BASE_URL}/users/{username}/orgs"

        try:
            response = self._session.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            return [org["login"] for org in response.json()]
        except requests.RequestException as e:
            print(f"[github_client] WARNING: Failed to fetch orgs for {username}: {e}")
            return []

    @staticmethod
    def parse_github_username_from_repo_url(repo_url: Optional[str]) -> Optional[str]:
        """
        Extract GitHub username/org from repository URL.

        Handles formats:
        - https://github.com/user/repo
        - git+https://github.com/user/repo.git
        - git://github.com/user/repo.git
        - git@github.com:user/repo.git
        - github:user/repo

        Args:
            repo_url: Repository URL string

        Returns:
            GitHub username/org or None
        """
        if not repo_url:
            return None

        patterns = [
            r"github\.com[/:]([^/]+)/",  # Standard HTTPS/SSH
            r"^github:([^/]+)/",  # github: shorthand
        ]

        for pattern in patterns:
            match = re.search(pattern, repo_url)
            if match:
                return match.group(1)

        return None