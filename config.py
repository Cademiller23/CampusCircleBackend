from dotenv import load_dotenv # Load environment variables from .env file
import os # For interacting with operating system
import redis # For Redis-based session Management 
load_dotenv() # Load environment Variables from .env

# Configuration Class
class ApplicationConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY") # Secret key for session security 
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Disable SQLAlchemy modification track
    SQLALCHEMY_ECHO = True # Echo SQL queries to the console for debugging
    SQLALCHEMY_DATABASE_URI = "sqlite:///./db.sqlite" # Database URI (SQLite)

    SESSION_TYPE = "REDIS" # Use Radis for session Storage
    SESSION_PERMANENT = False # Sessions not permanent by default 
    SESSION_USE_SIGNER = True # Sign session data for security 
    SESSION_REDIS = redis.from_url('redis://127.0.0.1:5000') # Connect to Radis Server