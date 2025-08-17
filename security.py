# security.py - Security middleware and utilities for abuse prevention
import time
import logging
import hashlib
import json
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, session, abort, g
import re

# Configure security logging
security_logger = logging.getLogger('security')
handler = logging.FileHandler('security.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
security_logger.addHandler(handler)
security_logger.setLevel(logging.INFO)

class SecurityManager:
    def __init__(self):
        self.rate_limits = defaultdict(list)
        self.blocked_ips = set()
        self.failed_attempts = defaultdict(int)
        self.suspicious_activity = defaultdict(list)
        self.session_tokens = {}
        
    def get_client_ip(self):
        """Get real client IP accounting for proxies"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr
    
    def is_blocked_ip(self, ip):
        """Check if IP is blocked (development-friendly)"""
        import os
        is_development = os.getenv("FLASK_ENV") != "production"
        
        if is_development:
            # In development, don't block localhost/127.0.0.1
            if ip in ['127.0.0.1', 'localhost', '::1']:
                return False
        
        return ip in self.blocked_ips
    
    def block_ip(self, ip, reason="Suspicious activity"):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        security_logger.warning(f"IP {ip} blocked: {reason}")
    
    def check_rate_limit(self, ip, endpoint, max_requests=10, time_window=60):
        """Check if request exceeds rate limit"""
        now = time.time()
        key = f"{ip}:{endpoint}"
        
        # Clean old entries
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key] 
            if now - timestamp < time_window
        ]
        
        # Check if over limit
        if len(self.rate_limits[key]) >= max_requests:
            return False
            
        # Add current request
        self.rate_limits[key].append(now)
        return True
    
    def log_security_event(self, event_type, details):
        """Log security events for analysis"""
        ip = self.get_client_ip()
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'ip': ip,
            'event_type': event_type,
            'details': details,
            'user_agent': user_agent,
            'endpoint': request.endpoint,
            'method': request.method
        }
        
        security_logger.info(json.dumps(log_entry))
        
        # Track suspicious patterns
        self.track_suspicious_activity(ip, event_type)
    
    def track_suspicious_activity(self, ip, event_type):
        """Track patterns that might indicate abuse (development-friendly)"""
        import os
        is_development = os.getenv("FLASK_ENV") != "production"
        
        # In development, don't block localhost
        if is_development and ip in ['127.0.0.1', 'localhost', '::1']:
            return
        
        now = time.time()
        
        # Clean old entries (last hour)
        self.suspicious_activity[ip] = [
            (timestamp, event) for timestamp, event in self.suspicious_activity[ip]
            if now - timestamp < 3600
        ]
        
        # Add current event
        self.suspicious_activity[ip].append((now, event_type))
        
        # Check for abuse patterns (more lenient in development)
        recent_events = [event for _, event in self.suspicious_activity[ip][-20:]]
        
        # Higher thresholds in development
        validation_threshold = 10 if is_development else 5
        volume_threshold = 100 if is_development else 50
        
        # Multiple failed validations
        if recent_events.count('validation_failed') >= validation_threshold:
            self.block_ip(ip, "Multiple validation failures")
            return
        
        # Rapid requests
        if len(self.suspicious_activity[ip]) >= volume_threshold:
            self.block_ip(ip, "Excessive request volume")
            return
        
        # Bot-like behavior patterns
        if (recent_events.count('form_submission') >= 20 and 
            recent_events.count('page_view') == 0):
            self.block_ip(ip, "Bot-like submission pattern")
    
    def validate_session_token(self):
        """Validate session authenticity (lenient for development)"""
        if 'session_token' not in session:
            # Generate new session token
            token = hashlib.sha256(f"{time.time()}{self.get_client_ip()}".encode()).hexdigest()
            session['session_token'] = token
            session['token_created'] = time.time()
            self.session_tokens[token] = {
                'ip': self.get_client_ip(),
                'created': time.time(),
                'last_used': time.time()
            }
        else:
            token = session['session_token']
            if token not in self.session_tokens:
                # Invalid token - regenerate instead of blocking (development mode)
                self.log_security_event('invalid_session_token_regenerated', {'token': token[:8]})
                new_token = hashlib.sha256(f"{time.time()}{self.get_client_ip()}".encode()).hexdigest()
                session['session_token'] = new_token
                session['token_created'] = time.time()
                self.session_tokens[new_token] = {
                    'ip': self.get_client_ip(),
                    'created': time.time(),
                    'last_used': time.time()
                }
                return
            
            # Update last used
            self.session_tokens[token]['last_used'] = time.time()
            
            # Check if token is too old (24 hours) - regenerate instead of blocking
            if time.time() - self.session_tokens[token]['created'] > 86400:
                self.log_security_event('expired_session_token_regenerated', {'token': token[:8]})
                del self.session_tokens[token]
                new_token = hashlib.sha256(f"{time.time()}{self.get_client_ip()}".encode()).hexdigest()
                session['session_token'] = new_token
                session['token_created'] = time.time()
                self.session_tokens[new_token] = {
                    'ip': self.get_client_ip(),
                    'created': time.time(),
                    'last_used': time.time()
                }
    
    def validate_user_agent(self):
        """Check for suspicious user agents (lenient for development)"""
        user_agent = request.headers.get('User-Agent', '')
        
        # Block empty user agents (but more lenient)
        if not user_agent:
            self.log_security_event('empty_user_agent', {})
            # Don't block for development - just log
            return True
        
        # Block known malicious bot patterns (reduced list for development)
        malicious_patterns = [
            r'wget', r'curl', r'scanner', r'exploit'
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                self.log_security_event('malicious_user_agent', {'user_agent': user_agent})
                return False
        
        # Log but don't block other bots in development
        bot_patterns = [
            r'bot', r'crawler', r'spider', r'scraper',
            r'python-requests', r'automation', r'test'
        ]
        
        for pattern in bot_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                self.log_security_event('bot_user_agent_allowed', {'user_agent': user_agent})
                break
        
        return True
    
    def check_request_anomalies(self):
        """Check for request anomalies (lenient for development)"""
        # Check for missing referrer on form submissions (lenient - just log)
        if request.method == 'POST' and not request.referrer:
            self.log_security_event('missing_referrer', {})
            # Don't block - just log for development
        
        # Check for suspicious headers
        suspicious_headers = ['X-Forwarded-Host', 'X-Original-URL', 'X-Rewrite-URL']
        for header in suspicious_headers:
            if header in request.headers:
                self.log_security_event('suspicious_header', {'header': header})
        
        # Check request size
        if request.content_length and request.content_length > 10485760:  # 10MB
            self.log_security_event('large_request', {'size': request.content_length})
            return False
        
        return True

# Global security manager instance
security_manager = SecurityManager()

def rate_limit(max_requests=10, time_window=60, per_endpoint=True):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = security_manager.get_client_ip()
            
            # Check if IP is blocked
            if security_manager.is_blocked_ip(ip):
                security_manager.log_security_event('blocked_ip_attempt', {})
                abort(429)
            
            # Check rate limit
            endpoint = request.endpoint if per_endpoint else 'global'
            if not security_manager.check_rate_limit(ip, endpoint, max_requests, time_window):
                security_manager.log_security_event('rate_limit_exceeded', {
                    'endpoint': endpoint,
                    'limit': max_requests,
                    'window': time_window
                })
                abort(429)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def security_checks():
    """Comprehensive security middleware (development-friendly)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if in development mode
            import os
            is_development = os.getenv("FLASK_ENV") != "production"
            
            ip = security_manager.get_client_ip()
            
            # Basic security checks (more lenient in development)
            if security_manager.is_blocked_ip(ip):
                if is_development:
                    security_manager.log_security_event('blocked_ip_bypassed_dev', {})
                else:
                    abort(403)
            
            if not security_manager.validate_user_agent():
                if is_development:
                    security_manager.log_security_event('user_agent_bypassed_dev', {})
                else:
                    abort(403)
            
            # Check request anomalies (completely bypass in development)
            if is_development:
                # In development, just log but never block
                anomaly_result = security_manager.check_request_anomalies()
                if not anomaly_result:
                    security_manager.log_security_event('anomaly_bypassed_dev', {'would_block': True})
            else:
                # In production, actually check and block
                if not security_manager.check_request_anomalies():
                    abort(400)
            
            # Validate session (always run but handle errors gracefully in dev)
            try:
                security_manager.validate_session_token()
            except Exception as e:
                if is_development:
                    security_manager.log_security_event('session_error_bypassed_dev', {'error': str(e)})
                else:
                    raise
            
            # Log legitimate request
            security_manager.log_security_event('legitimate_request', {
                'endpoint': request.endpoint,
                'development_mode': is_development
            })
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_form_input(data, field_name, max_length=100):
    """Enhanced form input validation"""
    if not data:
        security_manager.log_security_event('validation_failed', {
            'field': field_name, 'reason': 'empty'
        })
        return False, "Field cannot be empty"
    
    # Length check
    if len(data) > max_length:
        security_manager.log_security_event('validation_failed', {
            'field': field_name, 'reason': 'too_long', 'length': len(data)
        })
        return False, f"Field too long (max {max_length} characters)"
    
    # Check for injection attempts
    injection_patterns = [
        r'<script', r'javascript:', r'onload=', r'onerror=',
        r'eval\(', r'document\.', r'window\.', r'alert\(',
        r'DROP\s+TABLE', r'INSERT\s+INTO', r'SELECT\s+\*',
        r'UNION\s+SELECT', r'--', r'/\*', r'\*/',
        r'@import', r'expression\('
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, data, re.IGNORECASE):
            security_manager.log_security_event('injection_attempt', {
                'field': field_name, 'pattern': pattern, 'data': data[:100]
            })
            return False, "Invalid characters detected"
    
    # Check for excessive special characters
    special_char_count = len(re.findall(r'[^a-zA-Z0-9\s\-\.\']', data))
    if special_char_count > len(data) * 0.3:  # More than 30% special chars
        security_manager.log_security_event('validation_failed', {
            'field': field_name, 'reason': 'too_many_special_chars'
        })
        return False, "Too many special characters"
    
    return True, ""

def log_user_action(action, details=None):
    """Log user actions for audit trail"""
    security_manager.log_security_event('user_action', {
        'action': action,
        'details': details or {}
    })

def check_csrf_token():
    """Manual CSRF token validation for when flask-wtf is not available"""
    if request.method == 'POST':
        token = request.form.get('csrf_token')
        session_token = session.get('csrf_token')
        
        if not token or not session_token or token != session_token:
            security_manager.log_security_event('csrf_violation', {})
            return False
    return True

def generate_csrf_token():
    """Generate CSRF token when flask-wtf is not available"""
    if 'csrf_token' not in session:
        session['csrf_token'] = hashlib.sha256(
            f"{time.time()}{security_manager.get_client_ip()}".encode()
        ).hexdigest()
    return session['csrf_token']

# Honeypot fields for bot detection
def check_honeypot(form_data):
    """Check honeypot fields that should remain empty"""
    honeypot_fields = ['email', 'website', 'phone', 'address']
    
    for field in honeypot_fields:
        if form_data.get(field):
            security_manager.log_security_event('honeypot_triggered', {
                'field': field, 'value': form_data[field][:50]
            })
            return False
    return True

# Request timing analysis
def analyze_request_timing():
    """Analyze request timing patterns"""
    if not hasattr(g, 'request_start_time'):
        g.request_start_time = time.time()
    
    processing_time = time.time() - g.request_start_time
    
    # Log unusually fast requests (possible automation)
    if processing_time < 0.1 and request.method == 'POST':
        security_manager.log_security_event('suspicious_timing', {
            'processing_time': processing_time,
            'method': request.method
        })

def cleanup_security_data():
    """Periodic cleanup of security data structures"""
    now = time.time()
    
    # Clean old session tokens
    expired_tokens = [
        token for token, data in security_manager.session_tokens.items()
        if now - data['last_used'] > 86400  # 24 hours
    ]
    
    for token in expired_tokens:
        del security_manager.session_tokens[token]
    
    # Clean old rate limit data
    for key in list(security_manager.rate_limits.keys()):
        security_manager.rate_limits[key] = [
            timestamp for timestamp in security_manager.rate_limits[key]
            if now - timestamp < 3600  # 1 hour
        ]
        if not security_manager.rate_limits[key]:
            del security_manager.rate_limits[key]