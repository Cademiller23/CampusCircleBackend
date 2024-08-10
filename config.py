from dotenv import load_dotenv # Load environment variables from .env file
import os # For interacting with operating system
import redis # For Redis-based session Management 
load_dotenv() # Load environment Variables from .env
from sqlalchemy import create_engine
# Configuration Class
class ApplicationConfig:
    UPLOAD_FOLDER = 'static/uploads'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    SECRET_KEY= os.getenv('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Disable SQLAlchemy modification track
    SQLALCHEMY_ECHO = True # Echo SQL queries to the console for debugging
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI') # Database URI (SQLite)
    engine = create_engine(SQLALCHEMY_DATABASE_URI, connect_args={'connect_timeout': 15})  # Example: 15 seconds timeout
    GOOGLE_CLOUD_STORAGE_BUCKET = os.getenv('GOOGLE_CLOUD_STORAGE_BUCKET')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    SESSION_TYPE = "redis" # Use Radis for session Storage
    SESSION_PERMANENT = False # Sessions not permanent by default 
    SESSION_USE_SIGNER = True # Sign session data for security 
    
    try:
        SESSION_REDIS = redis.from_url('redis://127.0.0.1:6379')
    except redis.exceptions.ConnectionError as e:
        raise ValueError("Failed to connect to Redis server:", e)
