from .auth import auth_bp
from .main import main_bp
from .match import match_bp
from .calendar import calendar_bp
from .ai_tools import ai_tools_bp

all_blueprints = [auth_bp, main_bp, match_bp, calendar_bp, ai_tools_bp]
