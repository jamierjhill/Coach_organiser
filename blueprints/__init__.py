from .auth import auth_bp
from .main import main_bp
from .match import match_bp
from .calendar import calendar_bp
from .ai_tools import ai_tools_bp
from .settings import settings_bp
from .player import player_bp
from .whats_new import whats_new_bp  # Add this line
from .admin import admin_bp


all_blueprints = [auth_bp, main_bp, match_bp, calendar_bp, ai_tools_bp, settings_bp, player_bp, whats_new_bp, admin_bp]
