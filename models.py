from flask_sqlalchemy import SQLAlchemy # Import SQLAlchemy for database Interaction
from uuid import uuid4  # Import the uuid module for generating unique IDs
from database import db # Import the database instance from your database
from sqlalchemy.sql import func # import for timestamp
from flask_migrate import Migrate
# Function to generate a unqiue hexidecimal ID 
def get_uuid():
    return uuid4().hex 

# User Model representing the structor of the "Users" table and attributes 
class User(db.Model):
    __tablename__ = "users" # Specify the table name 
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid) # Primary key, uses UUID for ID generation
    email = db.Column(db.String(345), unique=True) # Unique email column
    password = db.Column(db.Text, nullable=False) # Non-nullable password column
    profile_picture = db.Column(db.String(255)) # Store profile picture URL
    username = db.Column(db.String(50), unique=True, nullable=False) # Unique username 
    
# Post Model representing users posts
class Post(db.Model):
    __tablename__ = "posts" # Specifies table name
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid) # Independent post id - Primary key
    user_id = db.Column(db.String(32), db.ForeignKey('users.id'), nullable=False) # Gets the foreign key for the table which is user_id
    content_type = db.Column(db.String(10), nullable=False) # Image or Video have to program with setTimeout in React to make it so holding camera inputs Video and clicking is Image
    content_url = db.Column(db.String(255), nullable=False) # URL to store content
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    category = db.Column(db.String)
    user = db.relationship("User", backref="posts")
    # upVotes = db.Column(db.integer())
# Comment class 
    # comment id 
    # Foreign Key - Post, User 
    # Comment text 
    # Timestamp 


    # Creates the relationship between user and post (1:M) relationship 
    
