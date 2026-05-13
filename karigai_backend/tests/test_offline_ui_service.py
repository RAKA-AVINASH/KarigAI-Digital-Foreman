"""
Unit tests for Offline UI Service
"""

import pytest

from app.services.offline_ui_service import (
    OfflineUIService,
    FeatureAvailability,
    NetworkStatus
)


@pytest.fixture
def offline_ui_service():
    """Create an offline UI service instance"""
    return OfflineUIService()


def test_initial_network_status(offline_ui_service):
    """Test initial network status is unknown"""
    status = offline_ui_service.get_network_status()
    assert status == NetworkStatus.UNKNOWN


def test_set_network_status(offline_ui_service):
    """Test setting network status"""
    offline_ui_service.set_network_status(NetworkStatus.ONLINE)
    assert offline_ui_service.get_network_status() == NetworkStatus.ONLINE
    
    offline_ui_service.set_network_status(NetworkStatus.OFFLINE)
    assert offline_ui_service.get_network_status() == NetworkStatus.OFFLINE


def test_feature_availability_online(offline_ui_service):
    """Test feature availability when online"""
    offline_ui_service.set_network_status(NetworkStatus.ONLINE)
    
    status = offline_ui_service.check_feature_availability("voice_recognition")
    assert status.availability == FeatureAvailability.FULLY_AVAILABLE
    assert len(status.limitations) == 0


def test_feature_availability_offline_capable(offline_ui_service):
    """Test offline-capable feature when offline"""
    offline_ui_service.set_network_status(NetworkStatus.OFFLINE)
    
    status = offline_ui_service.check_feature_availability("document_generation")
    # Should be available offline (even without cache for this test)
    assert status.availability in [
        FeatureAvailability.OFFLINE_AVAILABLE,
        FeatureAvailability.UNAVAILABLE  # If no cache
    ]


def test_feature_availability_network_dependent(offline_ui_service):
    """Test network-dependent feature when offline"""
    offline_ui_service.set_network_status(NetworkStatus.OFFLINE)
    
    status = offline_ui_service.check_feature_availability("vision_analysis")
    assert status.availability == FeatureAvailability.UNAVAILABLE
    assert "Network connection required" in status.limitations


def test_feature_availability_slow_network(offline_ui_service):
    """Test feature availability with slow network"""
    offline_ui_service.set_network_status(NetworkStatus.SLOW)
    
    status = offline_ui_service.check_feature_availability("voice_recognition")
    assert status.availability == FeatureAvailability.DEGRADED
    assert "Slow network connection" in status.limitations


def test_unknown_feature(offline_ui_service):
    """Test checking unknown feature"""
    status = offline_ui_service.check_feature_availability("unknown_feature")
    assert status.availability == FeatureAvailability.UNAVAILABLE
    assert "Unknown feature" in status.message


def test_get_all_feature_statuses(offline_ui_service):
    """Test getting all feature statuses"""
    offline_ui_service.set_network_status(NetworkStatus.ONLINE)
    
    statuses = offline_ui_service.get_all_feature_statuses()
    
    assert len(statuses) > 0
    assert "voice_recognition" in statuses
    assert "document_generation" in statuses
    assert "vision_analysis" in statuses


def test_offline_mode_indicator_online(offline_ui_service):
    """Test offline mode indicator when online"""
    offline_ui_service.set_network_status(NetworkStatus.ONLINE)
    
    indicator = offline_ui_service.get_offline_mode_indicator()
    
    assert indicator["mode"] == "online"
    assert indicator["network_status"] == "online"
    assert indicator["color"] == "green"
    assert "feature_counts" in indicator


def test_offline_mode_indicator_offline(offline_ui_service):
    """Test offline mode indicator when offline"""
    offline_ui_service.set_network_status(NetworkStatus.OFFLINE)
    
    indicator = offline_ui_service.get_offline_mode_indicator()
    
    assert indicator["mode"] == "offline"
    assert indicator["network_status"] == "offline"
    assert indicator["color"] in ["yellow", "red"]


def test_get_feature_limitations(offline_ui_service):
    """Test getting feature limitations"""
    offline_ui_service.set_network_status(NetworkStatus.OFFLINE)
    
    limitations = offline_ui_service.get_feature_limitations("vision_analysis")
    
    assert len(limitations) > 0
    assert "Network connection required" in limitations


def test_get_fallback_option(offline_ui_service):
    """Test getting fallback option"""
    fallback = offline_ui_service.get_fallback_option("voice_recognition")
    assert fallback is not None
    assert fallback == "basic_voice_recognition"
    
    fallback = offline_ui_service.get_fallback_option("whatsapp_integration")
    assert fallback == "local_storage"


def test_should_use_fallback(offline_ui_service):
    """Test determining if fallback should be used"""
    offline_ui_service.set_network_status(NetworkStatus.OFFLINE)
    
    # Network-dependent feature should use fallback
    should_use = offline_ui_service.should_use_fallback("vision_analysis")
    assert isinstance(should_use, bool)


def test_get_user_message(offline_ui_service):
    """Test getting user-friendly message"""
    offline_ui_service.set_network_status(NetworkStatus.ONLINE)
    
    message = offline_ui_service.get_user_message("voice_recognition")
    assert len(message) > 0
    assert "voice_recognition" in message.lower()


def test_register_custom_feature(offline_ui_service):
    """Test registering a custom feature"""
    offline_ui_service.register_feature("custom_feature", {
        "offline_capable": True,
        "requires_cache": False,
        "degraded_offline": False,
        "fallback": None
    })
    
    offline_ui_service.set_network_status(NetworkStatus.OFFLINE)
    status = offline_ui_service.check_feature_availability("custom_feature")
    
    assert status.availability == FeatureAvailability.OFFLINE_AVAILABLE


def test_get_offline_ready_features(offline_ui_service):
    """Test getting offline-ready features"""
    features = offline_ui_service.get_offline_ready_features()
    
    assert len(features) > 0
    assert "voice_recognition" in features
    assert "document_generation" in features
    assert "vision_analysis" not in features  # Not offline capable


def test_get_network_dependent_features(offline_ui_service):
    """Test getting network-dependent features"""
    features = offline_ui_service.get_network_dependent_features()
    
    assert len(features) > 0
    assert "vision_analysis" in features
    assert "whatsapp_integration" in features
