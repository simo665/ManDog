"""
Input validation utilities for the marketplace bot.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class InputValidator:
    """Utility class for validating user inputs."""
    
    # Constants for validation
    MAX_ITEM_NAME_LENGTH = 200
    MAX_NOTES_LENGTH = 500
    MAX_QUANTITY = 999
    MIN_QUANTITY = 1
    MAX_RATING = 5
    MIN_RATING = 1
    MAX_COMMENT_LENGTH = 500
    
    @staticmethod
    def validate_item_name(item_name: str) -> str:
        """Validate and clean item name."""
        try:
            if not item_name or not item_name.strip():
                raise ValidationError("Item name cannot be empty")
            
            # Clean the input
            cleaned_name = item_name.strip()
            
            # Check length
            if len(cleaned_name) > InputValidator.MAX_ITEM_NAME_LENGTH:
                raise ValidationError(f"Item name must be {InputValidator.MAX_ITEM_NAME_LENGTH} characters or less")
            
            # Check for valid characters (allow letters, numbers, spaces, and common symbols)
            if not re.match(r'^[a-zA-Z0-9\s\-_\+\(\)\[\]\'\"\.,:!]+$', cleaned_name):
                raise ValidationError("Item name contains invalid characters")
            
            # Prevent excessive whitespace
            cleaned_name = re.sub(r'\s+', ' ', cleaned_name)
            
            return cleaned_name
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating item name: {e}")
            raise ValidationError("Invalid item name format")
    
    @staticmethod
    def validate_quantity(quantity_str: str) -> int:
        """Validate and parse quantity."""
        try:
            if not quantity_str or not quantity_str.strip():
                return 1  # Default quantity
            
            # Parse quantity
            quantity = int(quantity_str.strip())
            
            # Check range
            if quantity < InputValidator.MIN_QUANTITY:
                raise ValidationError(f"Quantity must be at least {InputValidator.MIN_QUANTITY}")
            
            if quantity > InputValidator.MAX_QUANTITY:
                raise ValidationError(f"Quantity cannot exceed {InputValidator.MAX_QUANTITY}")
            
            return quantity
            
        except ValueError:
            raise ValidationError("Quantity must be a valid number")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating quantity: {e}")
            raise ValidationError("Invalid quantity format")
    
    @staticmethod
    def validate_notes(notes: str) -> str:
        """Validate and clean notes/price field."""
        try:
            if not notes:
                return ""
            
            # Clean the input
            cleaned_notes = notes.strip()
            
            # Check length
            if len(cleaned_notes) > InputValidator.MAX_NOTES_LENGTH:
                raise ValidationError(f"Notes must be {InputValidator.MAX_NOTES_LENGTH} characters or less")
            
            # Remove potentially harmful content (basic sanitization)
            cleaned_notes = re.sub(r'<[^>]*>', '', cleaned_notes)  # Remove HTML tags
            cleaned_notes = re.sub(r'[^\w\s\-_\+\(\)\[\]\'\"\.,:!@#$%&*/?=]', '', cleaned_notes)
            
            # Normalize whitespace
            cleaned_notes = re.sub(r'\s+', ' ', cleaned_notes)
            
            return cleaned_notes
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating notes: {e}")
            raise ValidationError("Invalid notes format")
    
    @staticmethod
    def validate_rating(rating_str: str) -> int:
        """Validate and parse rating."""
        try:
            if not rating_str or not rating_str.strip():
                raise ValidationError("Rating cannot be empty")
            
            # Parse rating
            rating = int(rating_str.strip())
            
            # Check range
            if rating < InputValidator.MIN_RATING or rating > InputValidator.MAX_RATING:
                raise ValidationError(f"Rating must be between {InputValidator.MIN_RATING} and {InputValidator.MAX_RATING}")
            
            return rating
            
        except ValueError:
            raise ValidationError("Rating must be a valid number")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating rating: {e}")
            raise ValidationError("Invalid rating format")
    
    @staticmethod
    def validate_comment(comment: str) -> str:
        """Validate and clean comment."""
        try:
            if not comment:
                return ""
            
            # Clean the input
            cleaned_comment = comment.strip()
            
            # Check length
            if len(cleaned_comment) > InputValidator.MAX_COMMENT_LENGTH:
                raise ValidationError(f"Comment must be {InputValidator.MAX_COMMENT_LENGTH} characters or less")
            
            # Basic sanitization
            cleaned_comment = re.sub(r'<[^>]*>', '', cleaned_comment)
            cleaned_comment = re.sub(r'[^\w\s\-_\+\(\)\[\]\'\"\.,:!@?]', '', cleaned_comment)
            
            # Normalize whitespace
            cleaned_comment = re.sub(r'\s+', ' ', cleaned_comment)
            
            return cleaned_comment
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating comment: {e}")
            raise ValidationError("Invalid comment format")
    
    @staticmethod
    def validate_time_format(time_str: str) -> str:
        """Validate time format (HH:MM)."""
        try:
            if not time_str or not time_str.strip():
                raise ValidationError("Time cannot be empty")
            
            time_str = time_str.strip()
            
            # Check format
            if not re.match(r'^\d{1,2}:\d{2}$', time_str):
                raise ValidationError("Time must be in HH:MM format")
            
            # Parse and validate
            hour_str, minute_str = time_str.split(':')
            hour = int(hour_str)
            minute = int(minute_str)
            
            if hour < 0 or hour > 23:
                raise ValidationError("Hour must be between 0 and 23")
            
            if minute < 0 or minute > 59:
                raise ValidationError("Minute must be between 0 and 59")
            
            # Format consistently
            return f"{hour:02d}:{minute:02d}"
            
        except ValueError:
            raise ValidationError("Invalid time format")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating time: {e}")
            raise ValidationError("Invalid time format")
    
    @staticmethod
    def validate_date_range(date_str: str) -> datetime:
        """Validate date is within acceptable range."""
        try:
            if not date_str or not date_str.strip():
                raise ValidationError("Date cannot be empty")
            
            # Parse date
            date_obj = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            
            # Check range (today to 14 days ahead)
            today = datetime.now().date()
            max_date = today + timedelta(days=14)
            
            if date_obj.date() < today:
                raise ValidationError("Date cannot be in the past")
            
            if date_obj.date() > max_date:
                raise ValidationError("Date cannot be more than 14 days in the future")
            
            return date_obj
            
        except ValueError:
            raise ValidationError("Invalid date format")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating date: {e}")
            raise ValidationError("Invalid date")
    
    @staticmethod
    def validate_listing_data(listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete listing data."""
        try:
            validated_data = {}
            
            # Required fields
            required_fields = ['listing_type', 'zone', 'subcategory', 'item']
            for field in required_fields:
                if field not in listing_data or not listing_data[field]:
                    raise ValidationError(f"Missing required field: {field}")
                validated_data[field] = listing_data[field]
            
            # Validate item name
            validated_data['item'] = InputValidator.validate_item_name(listing_data['item'])
            
            # Validate quantity
            quantity_str = listing_data.get('quantity', '1')
            validated_data['quantity'] = InputValidator.validate_quantity(str(quantity_str))
            
            # Validate notes
            notes = listing_data.get('notes', '')
            validated_data['notes'] = InputValidator.validate_notes(notes)
            
            # Validate date and time if provided
            if 'date' in listing_data and 'time' in listing_data:
                date_obj = InputValidator.validate_date_range(listing_data['date'])
                time_str = InputValidator.validate_time_format(listing_data['time'])
                
                # Combine date and time
                hour, minute = map(int, time_str.split(':'))
                scheduled_time = date_obj.replace(hour=hour, minute=minute, tzinfo=timezone.utc)
                validated_data['scheduled_time'] = scheduled_time
            
            return validated_data
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating listing data: {e}")
            raise ValidationError("Invalid listing data")

class ContentFilter:
    """Filter for inappropriate content."""
    
    # Basic profanity filter (can be expanded)
    BLOCKED_WORDS = [
        'spam', 'scam', 'hack', 'cheat', 'exploit',
        'bot', 'automation', 'script', 'macro'
    ]
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        r'\b(?:real money|rm|rmt|dollar|usd|eur|paypal|venmo)\b',  # RMT detection
        r'\b(?:discord\.gg|bit\.ly|tinyurl)\b',  # External links
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email addresses
        r'\b(?:\d{1,3}[-.]){3}\d{1,3}\b',  # IP addresses
    ]
    
    @classmethod
    def check_content(cls, text: str) -> Tuple[bool, List[str]]:
        """Check if content contains inappropriate material."""
        try:
            if not text:
                return True, []
            
            text_lower = text.lower()
            issues = []
            
            # Check blocked words
            for word in cls.BLOCKED_WORDS:
                if word in text_lower:
                    issues.append(f"Contains blocked word: {word}")
            
            # Check suspicious patterns
            for pattern in cls.SUSPICIOUS_PATTERNS:
                if re.search(pattern, text_lower):
                    issues.append("Contains suspicious content")
                    break
            
            # Check for excessive caps
            if len(text) > 10 and sum(1 for c in text if c.isupper()) / len(text) > 0.7:
                issues.append("Excessive capital letters")
            
            # Check for repeated characters
            if re.search(r'(.)\1{4,}', text):
                issues.append("Excessive repeated characters")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            logger.error(f"Error checking content: {e}")
            return False, ["Content validation error"]
    
    @classmethod
    def clean_content(cls, text: str) -> str:
        """Clean content by removing suspicious elements."""
        try:
            if not text:
                return text
            
            # Remove excessive repeated characters
            text = re.sub(r'(.)\1{3,}', r'\1\1\1', text)
            
            # Normalize case (if all caps, convert to title case)
            if text.isupper() and len(text) > 10:
                text = text.title()
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Error cleaning content: {e}")
            return text

class SecurityValidator:
    """Security-focused validation utilities."""
    
    @staticmethod
    def validate_user_input_safety(text: str) -> bool:
        """Check if user input is safe from injection attacks."""
        try:
            if not text:
                return True
            
            # Check for SQL injection patterns
            sql_patterns = [
                r'\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b',
                r'[\'";]',
                r'--',
                r'/\*',
                r'\*/'
            ]
            
            text_upper = text.upper()
            for pattern in sql_patterns:
                if re.search(pattern, text_upper):
                    return False
            
            # Check for script injection
            script_patterns = [
                r'<script',
                r'javascript:',
                r'vbscript:',
                r'on\w+\s*=',
            ]
            
            text_lower = text.lower()
            for pattern in script_patterns:
                if re.search(pattern, text_lower):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating input safety: {e}")
            return False
    
    @staticmethod
    def sanitize_for_database(text: str) -> str:
        """Sanitize text for database storage."""
        try:
            if not text:
                return text
            
            # Remove null bytes
            text = text.replace('\x00', '')
            
            # Escape single quotes for SQL safety (though we use parameterized queries)
            text = text.replace("'", "''")
            
            # Remove control characters except newlines and tabs
            text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
            
            return text
            
        except Exception as e:
            logger.error(f"Error sanitizing for database: {e}")
            return text
    
    @staticmethod
    def validate_discord_mention(mention: str) -> bool:
        """Validate Discord mention format."""
        try:
            # User mention: <@!1234567890> or <@1234567890>
            # Role mention: <@&1234567890>
            # Channel mention: <#1234567890>
            mention_pattern = r'^<[@#&!]?\d{17,19}>$'
            return bool(re.match(mention_pattern, mention))
            
        except Exception as e:
            logger.error(f"Error validating Discord mention: {e}")
            return False

def validate_and_clean_input(input_data: Dict[str, Any], field_rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Generic function to validate and clean input data based on rules."""
    try:
        cleaned_data = {}
        
        for field_name, value in input_data.items():
            if field_name in field_rules:
                rules = field_rules[field_name]
                
                # Check if field is required
                if rules.get('required', False) and (value is None or value == ''):
                    raise ValidationError(f"{field_name} is required")
                
                # Skip validation for empty optional fields
                if value is None or value == '':
                    cleaned_data[field_name] = value
                    continue
                
                # Apply validation based on field type
                field_type = rules.get('type', 'string')
                
                if field_type == 'string':
                    cleaned_data[field_name] = InputValidator.validate_item_name(str(value))
                elif field_type == 'notes':
                    cleaned_data[field_name] = InputValidator.validate_notes(str(value))
                elif field_type == 'quantity':
                    cleaned_data[field_name] = InputValidator.validate_quantity(str(value))
                elif field_type == 'rating':
                    cleaned_data[field_name] = InputValidator.validate_rating(str(value))
                elif field_type == 'comment':
                    cleaned_data[field_name] = InputValidator.validate_comment(str(value))
                elif field_type == 'time':
                    cleaned_data[field_name] = InputValidator.validate_time_format(str(value))
                else:
                    cleaned_data[field_name] = value
                
                # Check content filter if enabled
                if rules.get('content_filter', False):
                    is_clean, issues = ContentFilter.check_content(str(cleaned_data[field_name]))
                    if not is_clean:
                        raise ValidationError(f"{field_name} contains inappropriate content: {', '.join(issues)}")
                
                # Check security
                if rules.get('security_check', True):
                    if not SecurityValidator.validate_user_input_safety(str(cleaned_data[field_name])):
                        raise ValidationError(f"{field_name} contains unsafe content")
            else:
                cleaned_data[field_name] = value
        
        return cleaned_data
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error in generic validation: {e}")
        raise ValidationError("Validation error occurred")

# Pre-defined validation rules for common forms
LISTING_VALIDATION_RULES = {
    'item': {'type': 'string', 'required': True, 'content_filter': True},
    'notes': {'type': 'notes', 'required': False, 'content_filter': True},
    'quantity': {'type': 'quantity', 'required': False},
    'listing_type': {'type': 'string', 'required': True},
    'zone': {'type': 'string', 'required': True},
    'subcategory': {'type': 'string', 'required': True}
}

RATING_VALIDATION_RULES = {
    'rating': {'type': 'rating', 'required': True},
    'comment': {'type': 'comment', 'required': False, 'content_filter': True}
}
