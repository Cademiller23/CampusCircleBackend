from flask_sqlalchemy import SQLAlchemy # Import SQLAlchemy for database Interaction
from uuid import uuid4  # Import the uuid module for generating unique IDs
from database import db # Import the database instance from your database
from sqlalchemy.sql import func # import for timestamp
from flask_migrate import Migrate
# Function to generate a unqiue hexidecimal ID 
def get_uuid():
    return uuid4().hex 
saved_posts_table = db.Table('saved_posts', 
    db.Column('user_id', db.String(32), db.ForeignKey('users.id')),
    db.Column('post_id', db.String(32), db.ForeignKey('posts.id')),
 )
# User Model representing the structor of the "Users" table and attributes 
class User(db.Model):
    __tablename__ = "users" # Specify the table name 
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid) # Primary key, uses UUID for ID generation
    email = db.Column(db.String(345), unique=True) # Unique email column
    password = db.Column(db.Text, nullable=False) # Non-nullable password column
    profile_picture = db.Column(db.String(255)) # Store profile picture URL
    username = db.Column(db.String(50), unique=True, nullable=False) # Unique username 
    saved_posts = db.relationship('Post', secondary=saved_posts_table, backref="saved")
# Post Model representing users posts
class Post(db.Model):
    __tablename__ = "posts" # Specifies table name
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid) # Independent post id - Primary key
    user_id = db.Column(db.String(32), db.ForeignKey('users.id'), nullable=False) # Gets the foreign key for the table which is user_id
    content_type = db.Column(db.String(10), nullable=False) # Image or Video have to program with setTimeout in React to make it so holding camera inputs Video and clicking is Image
    content_url = db.Column(db.String(255), nullable=False) # URL to store content
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    category = db.Column(db.String)
    like_count = db.Column(db.Integer, nullable=False, default=0) # New like_count
    user = db.relationship("User", backref="posts")
    

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    post_id = db.Column(db.String(32), db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.String(32), db.ForeignKey('users.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    post = db.relationship("Post", backref="comments")
    user = db.relationship("User", backref="comments")

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(32), db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.String(32), db.ForeignKey('posts.id'), nullable=False)
    is_like = db.Column(db.Boolean, nullable=False) # True for likes, False for dislikes
    user = db.relationship('User', backref=db.backref('likes', lazy=True))
    post = db.relationship('Post', backref=db.backref('likes', lazy=True))

# Poll model
class Poll(db.Model):
    id = db.Column(db.String(32), primary_key=True, default=get_uuid)
    title = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.String(32), db.ForeignKey('users.id'), nullable=False)
    options = db.relationship('PollOption', backref='poll', lazy=True, cascade="all, delete-orphan")
    user = db.relationship('User', backref='polls')  # Add this line to define the relationship
# Poll Option model
class PollOption(db.Model):
    id = db.Column(db.String(32), primary_key=True, default=get_uuid)
    poll_id = db.Column(db.String(32), db.ForeignKey('poll.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    vote_count = db.Column(db.Integer, default=0)

# Poll Vote model
class PollVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(32), db.ForeignKey('users.id'), nullable=False)
    poll_id = db.Column(db.String(32), db.ForeignKey('poll.id'), nullable=False)
    option_id = db.Column(db.String(32), db.ForeignKey('poll_option.id'), nullable=False)
    

    

