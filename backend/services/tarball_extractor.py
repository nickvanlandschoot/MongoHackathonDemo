"""
Tarball content extractor for npm packages.
Responsible for extracting file lists and metadata, NOT analysis.
"""

import tarfile
import io
import json
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TarballContent:
    """Extracted content from a package tarball."""

    files: List[str]
    package_json: Optional[dict]
    scripts: Dict[str, str]  # npm scripts from package.json

    # Metadata for future analysis
    has_install_scripts: bool = False
    has_postinstall: bool = False
    has_preinstall: bool = False


class TarballExtractor:
    """Extractor for npm package tarballs - focused on data extraction only."""

    # Install script names that are auto-executed
    INSTALL_SCRIPTS = ["preinstall", "install", "postinstall", "prepare"]

    # Maximum tarball size to process (50MB)
    MAX_TARBALL_SIZE = 50_000_000

    def extract(self, tarball_bytes: bytes) -> TarballContent:
        """
        Extract content from a tarball.

        Args:
            tarball_bytes: Raw .tgz content

        Returns:
            TarballContent with file list and metadata
        """
        if len(tarball_bytes) > self.MAX_TARBALL_SIZE:
            return TarballContent(
                files=[],
                package_json=None,
                scripts={},
            )

        files: List[str] = []
        package_json: Optional[dict] = None

        try:
            with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:gz") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue

                    # Normalize path (remove leading 'package/')
                    name = member.name
                    if name.startswith("package/"):
                        name = name[8:]
                    files.append(name)

                    # Parse package.json
                    if name == "package.json":
                        try:
                            f = tar.extractfile(member)
                            if f:
                                content = f.read().decode("utf-8", errors="ignore")
                                package_json = json.loads(content)
                        except (json.JSONDecodeError, Exception) as e:
                            print(f"[tarball_extractor] DEBUG: Failed to parse package.json: {e}")

        except tarfile.TarError as e:
            print(f"[tarball_extractor] ERROR: Failed to extract tarball: {e}")
            return TarballContent(
                files=[],
                package_json=None,
                scripts={},
            )

        # Extract scripts from package.json
        scripts = {}
        has_install_scripts = False
        has_postinstall = False
        has_preinstall = False

        if package_json:
            scripts = package_json.get("scripts", {})
            for script_name in self.INSTALL_SCRIPTS:
                if script_name in scripts:
                    has_install_scripts = True
                    if script_name == "postinstall":
                        has_postinstall = True
                    if script_name == "preinstall":
                        has_preinstall = True

        return TarballContent(
            files=files,
            package_json=package_json,
            scripts=scripts,
            has_install_scripts=has_install_scripts,
            has_postinstall=has_postinstall,
            has_preinstall=has_preinstall,
        )
