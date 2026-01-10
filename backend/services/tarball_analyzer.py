"""
Tarball content analyzer for suspicious patterns.
"""

import tarfile
import io
import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class TarballAnalysisResult:
    """Results from analyzing a package tarball."""

    files: List[str]
    suspicious_files: List[str]  # Files matching risky patterns
    suspicious_content_matches: Dict[str, List[str]]  # file -> matched patterns
    package_json: Optional[dict]
    scripts: Dict[str, str]  # npm scripts
    new_dependencies: List[str] = field(default_factory=list)  # deps added (if comparing)
    has_install_scripts: bool = False
    has_postinstall: bool = False
    has_preinstall: bool = False
    risk_indicators: List[str] = field(default_factory=list)  # Human-readable risk reasons


class TarballAnalyzer:
    """Analyzer for npm package tarballs."""

    # Suspicious filename patterns
    SUSPICIOUS_FILENAME_PATTERNS = [
        r"crypto",
        r"wallet",
        r"exfiltrat",
        r"steal",
        r"keylog",
        r"backdoor",
        r"reverse.?shell",
        r"\.min\.js$",  # Minified files in non-minified package (flag for review)
        r"eval\.js",
    ]

    # Suspicious content patterns (regexes)
    SUSPICIOUS_CONTENT_PATTERNS = [
        (r"eval\s*\(", "eval() usage"),
        (r"Function\s*\(", "Function() constructor"),
        (r"Buffer\.from\s*\([^)]*,\s*['\"]base64['\"]", "Base64 decoding"),
        (r"child_process", "child_process module"),
        (r"\.exec\s*\(", "exec() call"),
        (r"\.spawn\s*\(", "spawn() call"),
        (r"require\s*\(['\"]https?['\"]", "HTTP module"),
        (r"require\s*\(['\"]net['\"]", "Net module"),
        (r"require\s*\(['\"]dgram['\"]", "UDP module"),
        (r"process\.env", "Environment variable access"),
        (r"fs\.(read|write)", "Filesystem access"),
        (r"(0x[a-fA-F0-9]{40})", "Ethereum address pattern"),
        (r"(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}", "Bitcoin address pattern"),
        (r"webhook", "Webhook reference"),
        (r"discord\.com/api/webhooks", "Discord webhook"),
        (r"api\.telegram\.org", "Telegram API"),
    ]

    # Install script names that are auto-executed
    INSTALL_SCRIPTS = ["preinstall", "install", "postinstall", "prepare"]

    # Maximum tarball size to analyze (50MB)
    MAX_TARBALL_SIZE = 50_000_000

    # Maximum file size to analyze content (1MB)
    MAX_FILE_SIZE = 1_000_000

    def analyze(self, tarball_bytes: bytes) -> TarballAnalysisResult:
        """
        Analyze a tarball for suspicious patterns.

        Args:
            tarball_bytes: Raw .tgz content

        Returns:
            TarballAnalysisResult with findings
        """
        if len(tarball_bytes) > self.MAX_TARBALL_SIZE:
            return TarballAnalysisResult(
                files=[],
                suspicious_files=[],
                suspicious_content_matches={},
                package_json=None,
                scripts={},
                risk_indicators=["Tarball exceeds size limit, skipped analysis"],
            )

        files: List[str] = []
        suspicious_files: List[str] = []
        suspicious_content: Dict[str, List[str]] = {}
        package_json: Optional[dict] = None
        risk_indicators: List[str] = []

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

                    # Check filename patterns
                    for pattern in self.SUSPICIOUS_FILENAME_PATTERNS:
                        if re.search(pattern, name, re.IGNORECASE):
                            suspicious_files.append(name)
                            break

                    # Check file contents for text files
                    if self._is_text_file(name) and member.size < self.MAX_FILE_SIZE:
                        try:
                            f = tar.extractfile(member)
                            if f:
                                content = f.read().decode("utf-8", errors="ignore")
                                matches = self._check_content(content)
                                if matches:
                                    suspicious_content[name] = matches

                                # Parse package.json
                                if name == "package.json":
                                    try:
                                        package_json = json.loads(content)
                                    except json.JSONDecodeError:
                                        risk_indicators.append("Malformed package.json")
                        except Exception as e:
                            print(f"[tarball_analyzer] DEBUG: Failed to read {name}: {e}")

        except tarfile.TarError as e:
            print(f"[tarball_analyzer] ERROR: Failed to parse tarball: {e}")
            return TarballAnalysisResult(
                files=[],
                suspicious_files=[],
                suspicious_content_matches={},
                package_json=None,
                scripts={},
                risk_indicators=["Failed to parse tarball (corrupted or malformed)"],
            )

        # Analyze package.json
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

        # Generate risk indicators
        if suspicious_files:
            risk_indicators.append(
                f"Suspicious filenames: {', '.join(suspicious_files[:5])}"
            )

        if suspicious_content:
            patterns_found = set()
            for file_matches in suspicious_content.values():
                patterns_found.update(file_matches)
            risk_indicators.append(
                f"Suspicious patterns in code: {', '.join(list(patterns_found)[:5])}"
            )

        if has_postinstall:
            risk_indicators.append("Has postinstall script (executes on npm install)")

        if has_preinstall:
            risk_indicators.append("Has preinstall script (executes on npm install)")

        return TarballAnalysisResult(
            files=files,
            suspicious_files=suspicious_files,
            suspicious_content_matches=suspicious_content,
            package_json=package_json,
            scripts=scripts,
            has_install_scripts=has_install_scripts,
            has_postinstall=has_postinstall,
            has_preinstall=has_preinstall,
            risk_indicators=risk_indicators,
        )

    def compare_package_json(
        self, old_pkg: Optional[dict], new_pkg: Optional[dict]
    ) -> List[str]:
        """
        Compare package.json files and identify changes.

        Returns list of risk indicators from the diff.
        """
        if not old_pkg or not new_pkg:
            return []

        indicators = []

        # Check for new scripts
        old_scripts = set(old_pkg.get("scripts", {}).keys())
        new_scripts = set(new_pkg.get("scripts", {}).keys())
        added_scripts = new_scripts - old_scripts

        for script in self.INSTALL_SCRIPTS:
            if script in added_scripts:
                indicators.append(f"Added {script} script")

        # Check for new dependencies
        old_deps = set(old_pkg.get("dependencies", {}).keys())
        new_deps = set(new_pkg.get("dependencies", {}).keys())
        added_deps = new_deps - old_deps

        if added_deps:
            indicators.append(f"Added dependencies: {', '.join(list(added_deps)[:5])}")

        return indicators

    def _is_text_file(self, filename: str) -> bool:
        """Check if file is likely a text file based on extension."""
        text_extensions = {
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".json",
            ".md",
            ".txt",
            ".yml",
            ".yaml",
            ".toml",
            ".sh",
            ".bash",
            ".mjs",
            ".cjs",
        }
        return any(filename.endswith(ext) for ext in text_extensions)

    def _check_content(self, content: str) -> List[str]:
        """Check content for suspicious patterns."""
        matches = []
        for pattern, description in self.SUSPICIOUS_CONTENT_PATTERNS:
            if re.search(pattern, content):
                matches.append(description)
        return matches