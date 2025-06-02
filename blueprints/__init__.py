# blueprints/__init__.py - Essential blueprints only
from .match import match_bp    # Match organizer (core feature)

# Only the essential blueprints for match organizer functionality
all_blueprints = [
    match_bp,     # Match organization
]