"""Tests for the Security module."""

import pytest
from paws.security import (
    verify_entitlements,
    extract_paths_from_inputs,
    _matches_capability,
    _matches_scope
)
from paws.core.models import AOLEntitlement


class TestExtractPathsFromInputs:
    """Tests for the extract_paths_from_inputs function."""
    
    def test_skips_command_key(self):
        """Command inputs should not be treated as paths."""
        inputs = {
            "command": "rm -f ~/Downloads/file.txt && echo hello > /tmp/output.txt"
        }
        paths = extract_paths_from_inputs(inputs)
        assert paths == []
    
    def test_skips_script_key(self):
        """Script inputs should not be treated as paths."""
        inputs = {
            "script": "#!/bin/bash\ncd /home/user && ls -la"
        }
        paths = extract_paths_from_inputs(inputs)
        assert paths == []
    
    def test_extracts_file_path(self):
        """Actual file paths should be extracted."""
        inputs = {
            "input_file": "/home/user/data.csv",
            "output_dir": "./output/"
        }
        paths = extract_paths_from_inputs(inputs)
        assert "/home/user/data.csv" in paths
        assert "./output/" in paths
    
    def test_extracts_home_path(self):
        """Paths starting with ~ should be extracted."""
        inputs = {
            "file": "~/Documents/report.pdf"
        }
        paths = extract_paths_from_inputs(inputs)
        assert "~/Documents/report.pdf" in paths
    
    def test_skips_urls(self):
        """URLs should not be treated as paths."""
        inputs = {
            "url": "https://example.com/api/data",
            "ftp": "ftp://files.example.com/data.zip"
        }
        paths = extract_paths_from_inputs(inputs)
        assert paths == []
    
    def test_skips_shell_commands_in_values(self):
        """Values containing shell operators should be skipped."""
        inputs = {
            "some_value": "cat file.txt | grep pattern",
            "other": "echo hello && echo world"
        }
        paths = extract_paths_from_inputs(inputs)
        assert paths == []
    
    def test_nested_dict(self):
        """Should extract paths from nested dicts."""
        inputs = {
            "config": {
                "input_path": "/data/input.json",
                "command": "echo /this/should/be/skipped"
            }
        }
        paths = extract_paths_from_inputs(inputs)
        assert "/data/input.json" in paths
        assert len(paths) == 1
    
    def test_list_values(self):
        """Should extract paths from lists."""
        inputs = {
            "files": ["/path/to/file1.txt", "/path/to/file2.txt"]
        }
        paths = extract_paths_from_inputs(inputs)
        assert "/path/to/file1.txt" in paths
        assert "/path/to/file2.txt" in paths


class TestMatchesCapability:
    """Tests for capability matching."""
    
    def test_exact_extension_match(self):
        assert _matches_capability("Bash", "Bash", "execute_command") == True
        assert _matches_capability("bash", "Bash", "execute_command") == True
    
    def test_wildcard(self):
        assert _matches_capability("*", "AnyExtension", "any_tool") == True
    
    def test_pattern_match(self):
        assert _matches_capability("Execute Bash Commands", "Bash", "execute_command") == True
    
    def test_no_match(self):
        assert _matches_capability("Python Scripts", "Bash", "execute_command") == False


class TestMatchesScope:
    """Tests for scope matching."""
    
    def test_wildcard(self):
        assert _matches_scope("*", "/any/path") == True
    
    def test_execute_scope(self):
        assert _matches_scope("Execute", "/any/path") == True
        assert _matches_scope("execute commands", "/any/path") == True


class TestVerifyEntitlements:
    """Tests for the main verify_entitlements function."""
    
    def test_no_entitlements_permissive(self):
        """No entitlements = permissive mode."""
        allowed, reason = verify_entitlements([], "Bash", "execute_command")
        assert allowed == True
        assert "permissive" in reason.lower()
    
    def test_matching_capability_no_path(self):
        """Should allow when capability matches and no path to check."""
        entitlements = [
            AOLEntitlement(scope="Execute", capability="Execute Bash Commands")
        ]
        allowed, reason = verify_entitlements(entitlements, "Bash", "execute_command")
        assert allowed == True
    
    def test_denied_no_matching_capability(self):
        """Should deny when no capability matches."""
        entitlements = [
            AOLEntitlement(scope="Read ./data/", capability="File Access")
        ]
        allowed, reason = verify_entitlements(entitlements, "Bash", "execute_command", "/tmp/file.txt")
        assert allowed == False
