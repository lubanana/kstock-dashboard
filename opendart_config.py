"""
OpenDart API Configuration Module
Loads API key from environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the same directory as this module
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# API Configuration
OPENDART_API_KEY = os.getenv('OPENDART_API_KEY')
OPENDART_BASE_URL = os.getenv('OPENDART_BASE_URL', 'https://opendart.fss.or.kr/api')
OPENDART_RATE_LIMIT = int(os.getenv('OPENDART_RATE_LIMIT', '5'))

def get_api_key() -> str:
    """Get OpenDart API key from environment"""
    if not OPENDART_API_KEY:
        raise ValueError("OPENDART_API_KEY not found. Please set it in .env file")
    return OPENDART_API_KEY

def get_headers() -> dict:
    """Get default headers for API requests"""
    return {
        'User-Agent': 'KStock-Scanner/1.0',
        'Accept': 'application/json'
    }

def validate_config() -> bool:
    """Validate API configuration"""
    try:
        key = get_api_key()
        return len(key) > 0
    except ValueError:
        return False

if __name__ == '__main__':
    # Test configuration
    if validate_config():
        print(f"✅ OpenDart API Key configured: {OPENDART_API_KEY[:10]}...")
        print(f"   Base URL: {OPENDART_BASE_URL}")
        print(f"   Rate Limit: {OPENDART_RATE_LIMIT} req/sec")
    else:
        print("❌ OpenDart API Key not found!")
