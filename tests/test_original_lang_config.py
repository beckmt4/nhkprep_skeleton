"""Tests for original language detection configuration system."""

import os
import tempfile
from pathlib import Path

import pytest
from unittest.mock import patch

from src.nhkprep.config import RuntimeConfig
from src.nhkprep.original_lang.config import OriginalLanguageConfig, create_detector_from_runtime_config


class TestOriginalLanguageConfig:
    """Test configuration for original language detection."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = OriginalLanguageConfig()
        
        assert config.enabled is True
        assert config.tmdb_api_key is None
        assert config.backend_priorities == ["tmdb", "imdb"]
        assert config.confidence_threshold == 0.7
        assert config.max_backends == 2
        
        assert config.tmdb_rate_limit == 40
        assert config.tmdb_rate_window == 10
        assert config.imdb_rate_limit == 10
        assert config.imdb_rate_window == 60
        
        assert config.cache_enabled is True
        assert config.cache_ttl == 86400
        assert config.cache_max_size == 1000
        
        assert config.search_max_results == 10
        assert config.year_tolerance == 1
        assert config.title_similarity_threshold == 0.8
        
        assert config.request_timeout == 30.0
        assert config.total_timeout == 120.0

    def test_custom_configuration(self):
        """Test configuration with custom values."""
        config = OriginalLanguageConfig(
            enabled=False,
            tmdb_api_key="test-key",
            backend_priorities=["imdb", "tmdb"],
            confidence_threshold=0.8,
            max_backends=1,
            cache_enabled=False
        )
        
        assert config.enabled is False
        assert config.tmdb_api_key == "test-key"
        assert config.backend_priorities == ["imdb", "tmdb"]
        assert config.confidence_threshold == 0.8
        assert config.max_backends == 1
        assert config.cache_enabled is False

    def test_cache_directory_creation(self):
        """Test that cache directory is created when enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "test_cache"
            config = OriginalLanguageConfig(
                cache_enabled=True,
                cache_dir=cache_dir
            )
            
            # Cache directory should be created in post_init
            assert cache_dir.exists()

    def test_from_runtime_config(self):
        """Test creating OriginalLanguageConfig from RuntimeConfig."""
        runtime_config = RuntimeConfig(
            orig_lang_enabled=False,
            orig_lang_tmdb_api_key="runtime-key",
            orig_lang_backend_priorities=["imdb"],
            orig_lang_confidence_threshold=0.9,
            orig_lang_max_backends=1,
            orig_lang_cache_enabled=False,
            orig_lang_total_timeout=60.0
        )
        
        orig_config = OriginalLanguageConfig.from_runtime_config(runtime_config)
        
        assert orig_config.enabled is False
        assert orig_config.tmdb_api_key == "runtime-key"
        assert orig_config.backend_priorities == ["imdb"]
        assert orig_config.confidence_threshold == 0.9
        assert orig_config.max_backends == 1
        assert orig_config.cache_enabled is False
        assert orig_config.total_timeout == 60.0

    @patch.dict(os.environ, {"TMDB_API_KEY": "env-key"})
    def test_environment_variable_api_key(self):
        """Test that API key is read from environment variable."""
        runtime_config = RuntimeConfig(orig_lang_tmdb_api_key=None)
        orig_config = OriginalLanguageConfig.from_runtime_config(runtime_config)
        
        assert orig_config.tmdb_api_key == "env-key"

    def test_get_backend_config_tmdb(self):
        """Test getting TMDb backend configuration."""
        config = OriginalLanguageConfig(
            tmdb_api_key="test-key",
            tmdb_rate_limit=30,
            tmdb_rate_window=15,
            search_max_results=5,
            year_tolerance=2,
            request_timeout=45.0
        )
        
        backend_config = config.get_backend_config("tmdb")
        
        assert backend_config["api_key"] == "test-key"
        assert backend_config["rate_limit"] == 30
        assert backend_config["rate_window"] == 15
        assert backend_config["max_results"] == 5
        assert backend_config["year_tolerance"] == 2
        assert backend_config["request_timeout"] == 45.0

    def test_get_backend_config_imdb(self):
        """Test getting IMDb backend configuration."""
        config = OriginalLanguageConfig(
            imdb_rate_limit=20,
            imdb_rate_window=30,
            search_max_results=8,
            year_tolerance=3,
            request_timeout=25.0
        )
        
        backend_config = config.get_backend_config("imdb")
        
        assert backend_config["rate_limit"] == 20
        assert backend_config["rate_window"] == 30
        assert backend_config["max_results"] == 8
        assert backend_config["year_tolerance"] == 3
        assert backend_config["request_timeout"] == 25.0

    def test_get_backend_config_invalid(self):
        """Test getting configuration for invalid backend."""
        config = OriginalLanguageConfig()
        
        with pytest.raises(ValueError, match="Unknown backend: invalid"):
            config.get_backend_config("invalid")

    def test_is_backend_available(self):
        """Test backend availability checking."""
        config = OriginalLanguageConfig(enabled=True, tmdb_api_key="test-key")
        
        assert config.is_backend_available("tmdb") is True
        assert config.is_backend_available("imdb") is True
        assert config.is_backend_available("invalid") is False
        
        # Test with disabled config
        config_disabled = OriginalLanguageConfig(enabled=False, tmdb_api_key="test-key")
        assert config_disabled.is_backend_available("tmdb") is False
        assert config_disabled.is_backend_available("imdb") is False
        
        # Test without API key
        config_no_key = OriginalLanguageConfig(enabled=True, tmdb_api_key=None)
        assert config_no_key.is_backend_available("tmdb") is False
        assert config_no_key.is_backend_available("imdb") is True

    def test_get_available_backends(self):
        """Test getting available backends in priority order."""
        config = OriginalLanguageConfig(
            enabled=True,
            tmdb_api_key="test-key",
            backend_priorities=["tmdb", "imdb"],
            max_backends=2
        )
        
        available = config.get_available_backends()
        assert available == ["tmdb", "imdb"]
        
        # Test with max_backends limit
        config.max_backends = 1
        available = config.get_available_backends()
        assert available == ["tmdb"]
        
        # Test with disabled
        config.enabled = False
        available = config.get_available_backends()
        assert available == []
        
        # Test without TMDb API key
        config = OriginalLanguageConfig(
            enabled=True,
            tmdb_api_key=None,
            backend_priorities=["tmdb", "imdb"],
            max_backends=2
        )
        available = config.get_available_backends()
        assert available == ["imdb"]

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = OriginalLanguageConfig(
            confidence_threshold=0.8,
            max_backends=2,
            title_similarity_threshold=0.7,
            year_tolerance=1,
            cache_ttl=3600,
            request_timeout=30.0,
            total_timeout=120.0,
            backend_priorities=["tmdb", "imdb"],
            tmdb_api_key="test-key"
        )
        
        issues = config.validate()
        assert issues == []

    def test_validate_invalid_config(self):
        """Test validation of invalid configuration."""
        config = OriginalLanguageConfig(
            confidence_threshold=1.5,  # Invalid: > 1
            max_backends=0,  # Invalid: < 1
            title_similarity_threshold=-0.1,  # Invalid: < 0
            year_tolerance=-1,  # Invalid: < 0
            cache_ttl=-100,  # Invalid: < 0
            request_timeout=-10.0,  # Invalid: <= 0
            total_timeout=50.0,  # Valid but we'll test separately
            backend_priorities=["invalid_backend"],  # Invalid backend
            enabled=True,
            tmdb_api_key=None  # No available backends
        )
        
        issues = config.validate()
        
        expected_keywords = [
            "confidence_threshold must be between 0 and 1",
            "max_backends must be at least 1", 
            "title_similarity_threshold must be between 0 and 1",
            "year_tolerance must be non-negative",
            "cache_ttl must be non-negative",
            "request_timeout must be positive",
            "Invalid backends",
            "No available backends"
        ]
        
        for keyword in expected_keywords:
            assert any(keyword in issue for issue in issues), f"Expected keyword not found: {keyword}"
    
    def test_validate_timeout_comparison(self):
        """Test timeout comparison validation separately."""
        config = OriginalLanguageConfig(
            request_timeout=60.0,
            total_timeout=30.0  # Invalid: smaller than request_timeout
        )
        
        issues = config.validate()
        assert any("total_timeout should be greater than request_timeout" in issue for issue in issues)


class TestDetectorFactory:
    """Test detector factory functions."""

    def test_create_detector_from_runtime_config_valid(self):
        """Test creating detector from valid runtime config."""
        runtime_config = RuntimeConfig(
            orig_lang_enabled=True,
            orig_lang_tmdb_api_key="test-key",
            orig_lang_confidence_threshold=0.8
        )
        
        detector = create_detector_from_runtime_config(runtime_config)
        
        assert detector is not None
        assert detector.config.enabled is True
        assert detector.config.tmdb_api_key == "test-key"
        assert detector.config.confidence_threshold == 0.8

    def test_create_detector_from_runtime_config_invalid(self):
        """Test creating detector from invalid runtime config."""
        runtime_config = RuntimeConfig(
            orig_lang_enabled=True,
            orig_lang_tmdb_api_key=None,
            orig_lang_confidence_threshold=2.0,  # Invalid: > 1
            orig_lang_backend_priorities=["invalid"]  # Invalid backend
        )
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            create_detector_from_runtime_config(runtime_config)


if __name__ == "__main__":
    pytest.main([__file__])