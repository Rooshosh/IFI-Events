import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # API configuration
    API_BASE_URL = os.getenv('API_BASE_URL', 'https://ifi-events-data-service.up.railway.app')
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30')) 