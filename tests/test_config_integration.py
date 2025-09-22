"""Integration test for configuration system with detector."""

import pytest

from src.nhkprep.config import RuntimeConfig
from src.nhkprep.original_lang.config import create_detector_from_runtime_config


@pytest.mark.asyncio
class TestConfigurationIntegration:
    """Test integration of configuration system with detector."""

    async def test_detector_with_default_config(self):
        """Test detector creation with default configuration."""
        runtime_config = RuntimeConfig()
        
        detector = create_detector_from_runtime_config(runtime_config)
        
        assert detector is not None
        assert detector.config.enabled is True
        assert detector.config.confidence_threshold == 0.7
        assert detector.config.backend_priorities == ["tmdb", "imdb"]
        
        # Should have no backends set up initially
        assert len(detector.backends) == 0
        
        # Get available backends should work
        available = detector.config.get_available_backends()
        # Without API key, only IMDb should be available
        assert available == ["imdb"]

    async def test_detector_with_custom_config(self):
        """Test detector creation with custom configuration."""
        runtime_config = RuntimeConfig(
            orig_lang_enabled=True,
            orig_lang_tmdb_api_key="test-key",
            orig_lang_confidence_threshold=0.8,
            orig_lang_backend_priorities=["tmdb", "imdb"],
            orig_lang_max_backends=1
        )
        
        detector = create_detector_from_runtime_config(runtime_config)
        
        assert detector.config.enabled is True
        assert detector.config.tmdb_api_key == "test-key"
        assert detector.config.confidence_threshold == 0.8
        assert detector.config.backend_priorities == ["tmdb", "imdb"]
        assert detector.config.max_backends == 1
        
        # Should have both backends available
        available = detector.config.get_available_backends()
        assert available == ["tmdb"]  # Limited by max_backends=1

    async def test_detector_with_disabled_config(self):
        """Test detector behavior when disabled."""
        runtime_config = RuntimeConfig(
            orig_lang_enabled=False,
            orig_lang_tmdb_api_key="test-key"
        )
        
        detector = create_detector_from_runtime_config(runtime_config)
        
        assert detector.config.enabled is False
        
        # Should not detect anything when disabled
        result = await detector.detect_from_filename("Spirited Away (2001).mkv")
        assert result is None

    async def test_timeout_configuration(self):
        """Test timeout configuration is respected."""
        runtime_config = RuntimeConfig(
            orig_lang_total_timeout=0.1,  # Very short timeout
            orig_lang_request_timeout=0.05
        )
        
        detector = create_detector_from_runtime_config(runtime_config)
        
        assert detector.config.total_timeout == 0.1
        assert detector.config.request_timeout == 0.05
        
        # Detection should timeout quickly (though we can't test actual timeout easily)
        # Just verify the configuration is applied
        assert detector.config.total_timeout < 1.0

    async def test_backend_configuration_tmdb(self):
        """Test TMDb backend configuration."""
        runtime_config = RuntimeConfig(
            orig_lang_tmdb_api_key="test-key",
            orig_lang_tmdb_rate_limit=20,
            orig_lang_tmdb_rate_window=15,
            orig_lang_search_max_results=5,
            orig_lang_year_tolerance=2,
            orig_lang_request_timeout=45.0
        )
        
        detector = create_detector_from_runtime_config(runtime_config)
        
        tmdb_config = detector.config.get_backend_config("tmdb")
        
        assert tmdb_config["api_key"] == "test-key"
        assert tmdb_config["rate_limit"] == 20
        assert tmdb_config["rate_window"] == 15
        assert tmdb_config["max_results"] == 5
        assert tmdb_config["year_tolerance"] == 2
        assert tmdb_config["request_timeout"] == 45.0

    async def test_backend_configuration_imdb(self):
        """Test IMDb backend configuration."""
        runtime_config = RuntimeConfig(
            orig_lang_imdb_rate_limit=15,
            orig_lang_imdb_rate_window=30,
            orig_lang_search_max_results=8,
            orig_lang_year_tolerance=3,
            orig_lang_request_timeout=35.0
        )
        
        detector = create_detector_from_runtime_config(runtime_config)
        
        imdb_config = detector.config.get_backend_config("imdb")
        
        assert imdb_config["rate_limit"] == 15
        assert imdb_config["rate_window"] == 30
        assert imdb_config["max_results"] == 8
        assert imdb_config["year_tolerance"] == 3
        assert imdb_config["request_timeout"] == 35.0


if __name__ == "__main__":
    pytest.main([__file__])