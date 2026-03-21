"""Service for managing feature toggles and MVP visibility."""

from enum import Enum


class Feature(Enum):
    """Available features that can be toggled."""
    # MVP Features (always enabled)
    HABITS = "habits"
    IDENTITIES = "identities"
    DEEP_WORK = "deep_work"
    BRAIN_DUMP = "brain_dump"
    DASHBOARD = "dashboard"
    
    # Phase 2+ Features (can be toggled)
    JOURNALS = "journals"
    TIME_BUCKETS = "time_buckets"
    ANALYTICS = "analytics"
    NOTIFICATIONS = "notifications"
    WHATSAPP_AGENT = "whatsapp_agent"
    AI_AUTOMATION = "ai_automation"
    EXPORT_IMPORT = "export_import"
    TEAM_COLLABORATION = "team_collaboration"


# MVP Feature Set - Always Enabled
MVP_FEATURES = {
    Feature.HABITS,
    Feature.IDENTITIES,
    Feature.DEEP_WORK,
    Feature.BRAIN_DUMP,
    Feature.DASHBOARD,
}

# Phase 2 Features - Can be hidden by user preference
PHASE_2_FEATURES = {
    Feature.JOURNALS,
    Feature.TIME_BUCKETS,
    Feature.NOTIFICATIONS,
    Feature.ANALYTICS,
}

# Future Features - Not yet implemented
FUTURE_FEATURES = {
    Feature.WHATSAPP_AGENT,
    Feature.AI_AUTOMATION,
    Feature.EXPORT_IMPORT,
    Feature.TEAM_COLLABORATION,
}


def is_mvp_feature(feature: Feature) -> bool:
    """Check if a feature is part of the MVP."""
    return feature in MVP_FEATURES


def is_enabled(feature: Feature, user_preferences: dict = None) -> bool:
    """
    Check if a feature is enabled for a user.
    
    Rules:
    - MVP features are always enabled
    - Phase 2 features can be disabled by user preference
    - Future features are never enabled
    """
    # MVP features are always enabled
    if feature in MVP_FEATURES:
        return True
    
    # Future features are never enabled
    if feature in FUTURE_FEATURES:
        return False
    
    # Phase 2 features can be toggled
    if feature in PHASE_2_FEATURES:
        if user_preferences is None:
            # Default: all Phase 2 features are enabled
            return True
        
        # Check user preference
        return user_preferences.get(f"feature_{feature.value}", True)
    
    return False


def get_enabled_features(user_preferences: dict = None) -> list:
    """Get all enabled features for a user."""
    enabled = []
    
    for feature in Feature:
        if is_enabled(feature, user_preferences):
            enabled.append(feature.value)
    
    return enabled


def get_feature_status(user_preferences: dict = None) -> dict:
    """Get the status of all features."""
    return {
        "mvp": [f.value for f in MVP_FEATURES],
        "phase_2": [f.value for f in PHASE_2_FEATURES],
        "future": [f.value for f in FUTURE_FEATURES],
        "enabled": get_enabled_features(user_preferences),
    }


def toggle_feature(feature: Feature, user_preferences: dict) -> dict:
    """Toggle a Phase 2 feature on/off for a user."""
    if feature in MVP_FEATURES:
        return {"status": "error", "message": "Cannot toggle MVP features"}
    
    if feature in FUTURE_FEATURES:
        return {"status": "error", "message": "Feature not yet available"}
    
    if feature not in PHASE_2_FEATURES:
        return {"status": "error", "message": "Unknown feature"}
    
    key = f"feature_{feature.value}"
    current_state = user_preferences.get(key, True)
    user_preferences[key] = not current_state
    
    return {
        "status": "success",
        "feature": feature.value,
        "enabled": not current_state
    }


def get_feature_description(feature: Feature) -> str:
    """Get a user-friendly description of a feature."""
    descriptions = {
        Feature.HABITS: "Track daily habits and build streaks",
        Feature.IDENTITIES: "Define identities and link them to habits",
        Feature.DEEP_WORK: "Schedule and track deep work sessions",
        Feature.BRAIN_DUMP: "Capture thoughts and ideas quickly",
        Feature.DASHBOARD: "View your daily overview and progress",
        Feature.JOURNALS: "Write and reflect on your journey",
        Feature.TIME_BUCKETS: "Plan your life in decades",
        Feature.NOTIFICATIONS: "Receive reminders and streak warnings",
        Feature.ANALYTICS: "View detailed progress analytics",
        Feature.WHATSAPP_AGENT: "Manage PersonalHQ via WhatsApp",
        Feature.AI_AUTOMATION: "AI-powered habit and session suggestions",
        Feature.EXPORT_IMPORT: "Export and import your data",
        Feature.TEAM_COLLABORATION: "Share goals with friends or coaches",
    }
    return descriptions.get(feature, "Unknown feature")
