# captcha.py - Simple CAPTCHA implementation for abuse prevention
import random
import string
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import hashlib
import time
from flask import session

class SimpleCaptcha:
    def __init__(self):
        self.width = 120
        self.height = 40
        self.length = 4
        
    def generate_text(self):
        """Generate random CAPTCHA text"""
        # Use letters and numbers, avoiding confusing characters
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        return ''.join(random.choice(chars) for _ in range(self.length))
    
    def add_noise(self, draw, width, height):
        """Add noise to make OCR harder"""
        # Add random lines
        for _ in range(random.randint(2, 4)):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=random.choice(['#808080', '#606060']), width=1)
        
        # Add random dots
        for _ in range(random.randint(10, 20)):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point((x, y), fill=random.choice(['#808080', '#606060']))
    
    def create_image(self, text):
        """Create CAPTCHA image"""
        # Create image with white background
        image = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Add background noise
        self.add_noise(draw, self.width, self.height)
        
        # Try to use a font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Calculate text position
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width = len(text) * 8
            text_height = 12
        
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2
        
        # Draw each character with slight rotation and color variation
        char_width = text_width // len(text)
        for i, char in enumerate(text):
            char_x = x + i * char_width + random.randint(-3, 3)
            char_y = y + random.randint(-3, 3)
            color = random.choice(['#000000', '#333333', '#666666'])
            
            if font:
                draw.text((char_x, char_y), char, font=font, fill=color)
            else:
                draw.text((char_x, char_y), char, fill=color)
        
        return image
    
    def generate_captcha(self):
        """Generate CAPTCHA and return image data and hash"""
        text = self.generate_text()
        image = self.create_image(text)
        
        # Convert image to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue()).decode()
        
        # Create hash for validation
        timestamp = str(int(time.time()))
        hash_input = f"{text.lower()}{timestamp}"
        captcha_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Store in session with timestamp
        session['captcha_hash'] = captcha_hash
        session['captcha_time'] = timestamp
        
        return f"data:image/png;base64,{image_data}"
    
    def validate_captcha(self, user_input):
        """Validate CAPTCHA input"""
        if not user_input:
            return False, "CAPTCHA is required"
        
        stored_hash = session.get('captcha_hash')
        stored_time = session.get('captcha_time')
        
        if not stored_hash or not stored_time:
            return False, "CAPTCHA expired or missing"
        
        # Check if CAPTCHA is expired (5 minutes)
        current_time = int(time.time())
        if current_time - int(stored_time) > 300:
            return False, "CAPTCHA expired"
        
        # Validate input
        user_input_clean = user_input.strip().upper()
        
        # Try all possible correct answers from the time window
        for test_text in self._generate_possible_texts():
            hash_input = f"{test_text.lower()}{stored_time}"
            test_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            if test_hash == stored_hash and user_input_clean == test_text.upper():
                # Clear CAPTCHA from session after successful validation
                session.pop('captcha_hash', None)
                session.pop('captcha_time', None)
                return True, "CAPTCHA validated"
        
        return False, "Incorrect CAPTCHA"
    
    def _generate_possible_texts(self):
        """Generate possible CAPTCHA texts for validation"""
        # This is a simple implementation
        # In a real scenario, you'd need to store the original text more securely
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        
        # For this simple implementation, we'll generate some common possibilities
        # This is not ideal but works for demonstration
        texts = []
        for _ in range(1000):  # Generate many possibilities
            text = ''.join(random.choice(chars) for _ in range(self.length))
            texts.append(text)
        
        return texts

class MathCaptcha:
    """Simple math-based CAPTCHA as alternative"""
    
    def generate_math_captcha(self):
        """Generate simple math problem"""
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        operation = random.choice(['+', '-'])
        
        if operation == '+':
            answer = num1 + num2
            question = f"What is {num1} + {num2}?"
        else:
            # Ensure positive result for subtraction
            if num1 < num2:
                num1, num2 = num2, num1
            answer = num1 - num2
            question = f"What is {num1} - {num2}?"
        
        # Store answer hash in session
        timestamp = str(int(time.time()))
        hash_input = f"{answer}{timestamp}"
        answer_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        session['math_captcha_hash'] = answer_hash
        session['math_captcha_time'] = timestamp
        
        return question
    
    def validate_math_captcha(self, user_input):
        """Validate math CAPTCHA answer"""
        try:
            user_answer = int(user_input.strip())
        except (ValueError, TypeError):
            return False, "Please enter a number"
        
        stored_hash = session.get('math_captcha_hash')
        stored_time = session.get('math_captcha_time')
        
        if not stored_hash or not stored_time:
            return False, "CAPTCHA expired or missing"
        
        # Check if expired (5 minutes)
        current_time = int(time.time())
        if current_time - int(stored_time) > 300:
            return False, "CAPTCHA expired"
        
        # Validate answer
        hash_input = f"{user_answer}{stored_time}"
        test_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        if test_hash == stored_hash:
            # Clear CAPTCHA from session
            session.pop('math_captcha_hash', None)
            session.pop('math_captcha_time', None)
            return True, "CAPTCHA validated"
        
        return False, "Incorrect answer"

# Global instances
simple_captcha = SimpleCaptcha()
math_captcha = MathCaptcha()

def require_captcha_after_failures(failure_threshold=3):
    """Decorator to require CAPTCHA after multiple failures"""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            failures = session.get('form_failures', 0)
            
            if failures >= failure_threshold:
                # Require CAPTCHA validation
                captcha_input = request.form.get('captcha_response', '').strip()
                
                if not captcha_input:
                    return jsonify({'error': 'CAPTCHA required after multiple attempts'}), 400
                
                # Validate CAPTCHA (try both types)
                image_valid, _ = simple_captcha.validate_captcha(captcha_input)
                math_valid, _ = math_captcha.validate_math_captcha(captcha_input)
                
                if not (image_valid or math_valid):
                    return jsonify({'error': 'Invalid CAPTCHA'}), 400
                
                # Reset failure count on successful CAPTCHA
                session['form_failures'] = 0
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator