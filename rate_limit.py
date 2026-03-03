"""
Rate limiting configuration for PHASE 1
Uses slowapi for protecting endpoints against brute force and abuse
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create a rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Rate limit definitions for different endpoint categories
RATE_LIMITS = {
    "login": "5 per minute",           # Max 5 login attempts per minute per IP
    "register": "3 per hour",          # Max 3 registrations per hour per IP
    "password_reset": "3 per hour",    # Max 3 password reset requests per hour per IP
    "email_verify": "10 per minute",   # Max 10 verification attempts per minute per IP
    "refresh_token": "30 per hour",    # Max 30 token refreshes per hour per IP
    "general": "100 per minute",       # General API rate limit
}
