# Server side session with added import stored
from flask import Flask, request, jsonify, session, abort, send_from_directory, url_for # core flask imports
from flask_bcrypt import Bcrypt # For Password Hashing
from flask_session import Session # For server-side Session Management
from models import User, Post, Comment # Import the user and post model
from flask_migrate import Migrate
from sqlalchemy.orm import joinedload
from config import ApplicationConfig # Import App config
from database import db # Import the database instance
from sqlalchemy import desc
from werkzeug.utils import secure_filename 
from flask_cors import CORS 
from openai import OpenAI 
client = OpenAI()

import os
import uuid
import base64
from sqlalchemy.sql import func 
# Create flask application instance 
app = Flask(__name__)
app.config.from_object(ApplicationConfig) # Load config from App Config


bcrypt = Bcrypt(app) # Initialize Bcrypt for password hashing
server_session = Session(app) # Initialize server-side session management 
db.init_app(app) # Initialize database with the Flask App
migrate = Migrate(app, db)
CORS(app, origins= '*')

# Create database tables if they don't exist 
with app.app_context():
    db.create_all()

# For profile pic on register
ALLOWED_EXTENSIONS = {"png", "jpg","jpeg"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/save_post/<post_id>', methods=['POST'])
def save_post(post_id):
    user_id = session.get('user_id')
    print(user_id)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request data. Expected JSON."}), 400
        
        data = request.get_json()
        user_id = data.get('user_id')

        if user_id != session_user_id:
            return jsonify({'error': 'Unathorized access to save post'})
        

        user = User.query.get(user_id)
        post = Post.query.get(post_id)

        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Check if the post is already saved by the user 

        if post in user.saved_posts:
            return jsonify({"message": "Post already saved"}), 200
        
        user.saved_posts.append(post)
        db.session.commit()

        return jsonify({"message": "Post saved successfully"}), 201
    except Exception as e:
        print(f'Error saving post: {e}')
        return jsonify({"error": "Internal Server Error"}), 500

# Get saved POsts for the Logged in User
@app.route('/saved_posts', methods=['GET'])
def get_saved_post():
    user = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unathorized"}), 401
    
    try: 
        user = User.query.get(user_id)
        saved_posts_data = [
            {
                'id': post.id,
                'user_id': post.user.user_id,
                'username': post.user.username,
                'content_type': post.content_type,
                'content_url': post.content_url,
                'timestamp': post.timestamp,
                'category': post.category

            } for post in user.saved_posts
        ]
        if not saved_posts_data:
            return jsonify({"message": "No saved posts found."}), 200 
        return jsonify(saved_posts_data), 200
    except Exception as e:
        print(f"Error getting saved posts: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
# On the user Icon when submit new comment in explore
@app.route('/create_comments', methods=['POST'])
def create_comments():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    post_id = data.get('post_id')
    text = data.get('text')

    if not post_id or not text:
        return jsonify({"error": "Missing post_id or comment text"}), 400
    
    try:
        new_comment = Comment(user_id=user_id, post_id=post_id, text=text)
        db.session.add(new_comment)
        db.session.commit()

        # Optionally, you might want to return the created comment details
        return jsonify({
            'id': new_comment.id,
            'user_id': new_comment.user_id,
            'post_id': new_comment.post_id,
            'text': new_comment.text,
            'timestamp': new_comment.timestamp.isoformat(),
            'username': new_comment.user.username # Include username
        }), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Error creating comment:  {e}")
        return jsonify({"error": str(e)}), 500

    

# In Home page displays all users only comments
@app.route('/comments/me', methods=["GET"])
def get_own_comments():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    comments = Comment.query.filter_by(user_id=user_id).options(joinedload(Comment.user)).all()

    comments_data = [{
        'id': comment.id,
        'post_id': comment.post_id,
        'text': comment.text,
        'timestamp': comment.timestamp,
        'username': comment.user.username # Include eusername 

    } for comment in comments]

    return jsonify(comments_data), 200


# In explore when press on comments icon it opens and displays all comments associated with post_id
@app.route('/newComments/<post_id>', methods=["GET"])
def get_posts_comments(post_id):
    print(post_id)
    try:
        comments = (
            Comment.query
            .filter_by(post_id=post_id)
            .options(joinedload(Comment.user))
            .order_by(Comment.timestamp)
            .all()
        )
        print(comments)
        if not comments:
            return jsonify({"message": "No comments found for this Post"})
        
        comments_data = []
        for comment in comments:
            comment_data = {
                'id': comment.id,
                'user_id': comment.user_id,
                'text': comment.text,
                'timestamp': comment.timestamp,
                'username': comment.user.username # Include username
            }
            comments_data.append(comment_data)

        return jsonify(comments_data), 200
    
    except Exception as e:
        print(f"Error getting comments: {e}")
        return jsonify({"error": "Internal Server Error"}), 500



# Sending Image Through OpenAI
@app.route('/openAI', methods=['GET']) 
def get_openAI(photoUri):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
         
            # Sent to gemini API messages
        ]
    )

# Fetch posts for home feed 
@app.route('/posts', methods=['GET'])
def get_posts():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    # Pagination parameters form query string each a page full of metadata
    page = request.args.get('page', 1, type=int)
    # Creates a max number of posts per page
    per_page = request.args.get('per_page', 10, type=int)

    # Query posts order by timestamp and descending 
    posts = Post.query.filter_by(user_id=user_id).order_by(desc(Post.timestamp)).paginate(page=page, per_page=per_page, error_out=False)

    # Handle case where no posts are found 
    if not posts.items:
        return jsonify({
            'posts': [],
            'total': 0,
            'has_next': False
        }), 200
    # Prepare response data: lost of post dictionaries
    return jsonify({
        "posts": [
            {
                "id": post.id,
                "user_id": post.user_id,
                "content_type": post.content_type,
                "content_url": post.content_url,
                "timestamp": post.timestamp,
                "category": post.category,
            }
            for post in posts.items # Converts posts object to dictionary
        ],
        "total": posts.total,
        "has_next": posts.has_next
    }), 200

    # Create a new Post 
@app.route('/posts', methods=['POST'])
def create_post():
    user_id = session.get('user_id') # Getting user_id
    if not user_id:
        return jsonify({"error": "Unathorized"}), 401 # Unauthorized
    try:
        file = request.files['newImage']
        if file and allowed_file(file.filename):
            # Get the original filename from the request 
            original_filename = secure_filename(file.filename)

            # Generate a unique filename using uuid 
            unique_filename = str(uuid.uuid4()) + '.' + original_filename.rsplit('.', 1)[1].lower()

            # Construct the full file path to save the image 
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            # Save the file using the unqiue filename 
            file.save(file_path)

            # Convert the image to base64 for storage in the data base
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

            new_post = Post(
                user_id=user_id,
                content_type=request.form.get('content_type', 'image/jpeg'),  # Default to 'image/jpeg'
                content_url=encoded_string,  # Store the base64 encoded image
                category=request.form.get('category') # Get Category from request 
            )

            db.session.add(new_post)
            db.session.commit()

            return jsonify({
                "id": new_post.id,
                "user_id": new_post.user_id,
                "content_type": new_post.content_type,
                "content_url": new_post.content_url,
                "timestamp": new_post.timestamp,
                "category": new_post.category
            }), 201

    except Exception as e:
            db.session.rollback()
            print(f"Error creating post: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
  

 # Get a specific post's details Explore
@app.route('/explore_posts', methods=['GET'])
def get_other_post():
    current_user_id = session.get('user_id')
    print(current_user_id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', default=None) # Get Category filter if provided
    
    try:
        posts_query = Post.query.filter(Post.content_type != None).order_by(func.random())
        print(posts_query)
        if current_user_id: # If user is logged in exclude their posts
            posts_query = posts_query.filter(Post.user_id != current_user_id)

        # Apply Category Filter
        if category and category != 'all':
            posts_query = posts_query.filter_by(category=category)
        
        posts = posts_query.paginate(page=page, per_page=per_page, error_out=False) 

        posts_list = [
            {
                'id': post.id,
                'user_id': post.user_id,
                'username': post.user.username,
                'content_type': post.content_type,
                'content_url': post.content_url,
                'timestamp': post.timestamp,
                'category': post.category
            } for post in posts.items
        ]

        return jsonify({
            'posts': posts_list,
            'total': posts.total,
            'has_next': posts.has_next
        }), 200
    except Exception as e:
        print(f"Error getting posts: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
# Delete A Post 
@app.route('/posts', methods=['DELETE'])
def delete_post(post_id):
    user_id = session.get('user_id') # Finds user_id
    if not user_id:
         return jsonify({"error": "Not Found"}), 401 # no posts found returns 

    post = Post.query.get(post_id) # If no post 
    if not post or post.user_id != user_id:
         return jsonify({"error": "Forbidden, not the user with post"}), 403  # Forbidden (not owner or post not found)
    
    db.session.delete(post)
    db.session.commit()
    return jsonify({}), 204 # 204 no content

# Get another user profile route 
@app.route('/users/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    
    user = User.query.get(user_id) # User query to find user with that user_id
    print(user)
    if not user: # else error not found
        return jsonify({"error": "Not found"}), 404
    with open(os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture), "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
    return jsonify({
        "id": user.id,
        "email": user.email,
        "username": user.username, # including username
        'profile_picture': encoded_image
      })
# Upload file
@app.route('/uploads/<filename>')
def send_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# Current Logged User
@app.route('/users/me', methods=["GET"])
def get_my_profile():
    # Fetches userId
    user_id = session.get('user_id')
    # if no user_id
    if not user_id:
        return jsonify({"error": "Unathorized"}), 401

    return get_user_profile(user_id) # reuses logic for getting a user profile

# Update user profile (username, profile_picture)
@app.route('/users/<user_id>', methods=['PATCH'])
def update_profile(user_id):
    user = User.query.get(user_id) # Gets user id 
    if user is None: # else error not found
        return jsonify({"error": "Not found"}), 404
    try:
        # Update Username 
        if 'username' in request.form:
            new_username = request.form['username']
            if User.query.filter_by(username=new_username).first() and new_username != user.username:
                abort(409, description="Username already exists") # Check for username uniqueness
            user.username = new_username

        # Update profile picture (similar to registration)
        if 'profileImage' in request.files:
            file = request.files['profileImage']
            print(file.filename)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                user.profile_picture = filename
    
        db.session.commit()
        return jsonify({"message": "Profile updated successfully",
        "profile_picture": f"/{app.config['UPLOAD_FOLDER']}/{user.profile_picture}"}), 200 # success

    except Exception as e:  # Catch any exceptions that may occur
        db.session.rollback()  # Rollback the transaction if an error occurs
        print(f"Error updating profile: {e}")  # Log the error for debugging
        return jsonify({"error": "Internal Server Error"}), 500


# Route for register users
@app.route('/register', methods=["POST"])
def register_user():
    print("DO YOU GET HERE!!!!!!!!")
    # Registration logic 
    data = request.get_json()
    print("DATA:", data)
    email = data['email']
    username = data['username']
    password = data['password']
    # If user exists alreadu in data 
    user_exists = User.query.filter_by(email=email).first() is not None
     # Gives 409 conflict - user exists
    if user_exists:
        return jsonify({"error": "User already exists"}), 409
    
    username_exists = User.query.filter_by(username=username).first() is not None
    if username_exists:
        return jsonify({"error": "Username already exists"}), 409
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(email=email, password=hashed_password, username=username)
    print(new_user)
    db.session.add(new_user)
    db.session.commit()
    try:
        session['user_id'] = new_user.id
    except redis.ConnectionError as e:
        print("Redis Connection Error:", e)
        return jsonify({"error": "Internal server error"}), 500
    return jsonify({
        "id": new_user.id,
        "email": new_user.email,
        "username": new_user.username,
        }), 201

# LOGIN STATUS   
@app.route('/login', methods=["POST"]) 
def login_user():
    email = request.json["email"]
    password = request.json["password"]

    user = User.query.filter_by(email=email).first()
    # No user exists
    if user is None:
        return jsonify({"error": "Unauthorized"}), 401
    
    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "unathorized"}), 401
    
    session["user_id"] = user.id
    return jsonify({
        "id": user.id,
        "email": user.email
      })

# Logout Status 
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None) # Clear the user ID from the sessionn
    return jsonify({"Message": "Logged out successfully"}), 200



# Main entry point
if __name__ == "__main__":
    app.run(debug=True, static_folder='static', host='0.0.0.0')
