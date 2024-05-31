# Server side session with added import stored
from flask import Flask, request, jsonify, session, abort # core flask imports
from flask_bcrypt import Bcrypt # For Password Hashing
from flask_session import Session # For server-side Session Management
from models import User, Post # Import the user and post model
from config import ApplicationConfig # Import App config
from database import db # Import the database instance
from sqlalchemy import desc
from werkzeug.utils import secure_filename 
from flask_cors import CORS 
# Create flask application instance 
app = Flask(__name__)
app.config.from_object(ApplicationConfig) # Load config from App Config

bcrypt = Bcrypt(app) # Initialize Bcrypt for password hashing
server_session = Session(app) # Initialize server-side session management 
db.init_app(app) # Initialize database with the Flask App
CORS(app, resources={r"/register": {"origins": "*"}})
# Create database tables if they don't exist 
with app.app_context():
    db.create_all()


# Fetch posts for home feed 
@app.route('/posts', methods=['GET'])
def get_posts():
    # Pagination parameters form query string each a page full of metadata
    page = request.args.get('page', 1, type=int)
    # Creates a max number of posts per page
    per_page = request.args.get('per_page', 10, type=int)

    # Query posts order by timestamp and descending 
    posts = Post.query.order_by(desc[Post.timestamp]).paginate(page=page, per_page=per_page, error_out=False)

    # Handle case where no posts are found 
    if not posts.items:
        return jsonify({"error": "Not Found, there are no posts"}), 404 # No posts found returns 
    # Prepare response data: lost of post dictionaries
    return jsonify({
        "posts": [
            {
                "id": post.id,
                "user_id": post.user_id,
                "content_type": post.content_type,
                "content_url": post.content_url,
                "timestamp": post.timestamp
            }
            for post in posts.items # Converts posts object to dictionary
        ],
        "total": posts.total,
        "has_next": posts.has_next
    })

    # Create a new Post 
@app.route('/posts', methods=['POST'])
def create_post():
    user_id = session.get('user_id') # Getting user_id
    if not user_id:
        return jsonify({"error": "Not Found, there are no posts"}), 404 # Unauthorized
    
    # Put logic to handle file upload, determing content type and
     # store url also implement file storage choice
    new_post = Post(user_id=user_id, content_type=content_type, content_url=content_url)
    db.session.add(new_post) # Adds the new post to the database session
    db.session.commit() # Commits the changes to database

        # Returns the JSON response with the new post 

    return jsonify ({
            "id": new_post.id,
            "user_id": new_post.user_id,
            "content_type": new_post.content_type,
            "content_url": new_post.content_url,
            "timestamp": new_post.timestamp
    }), 201 # Successful

        # Get a specific post's details 
@app.route('/posts/<post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.query.get(post_id) # Gets post_id
    if not post:
        return jsonify({"error": "Not Found, there are no posts"}), 404 # no posts found returns 

    #Returns the JSON response with the new post
    return jsonify({ 
            "id": new_post.id, 
            "user_id": new_post.user_id,
            "content_type": new_post.content_type,
            "content_url": new_post.content_type,
            "timestamp": new_post.timestamp
    }), 201 # Success

# Delete A Post 
@app.route('/posts/<post_id>', methods=['DELETE'])
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
    if not user: # else error not found
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "id": user.id,
        "email": user.email,
        "username": user.username, # including username
        'profile_picture':user.profile_picture
      })
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
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unathorized"}), 401
    
    user = User.query.get(user_id) # Gets user id 
    if not user: # else error not found
        return jsonify({"error": "Not found"}), 404
    
    # Update Username 
    new_username = request.json.get('username')
    if new_username:
        if User.query.filter_by(username=new_username).first() and new_username != user.username:
            abort(409, description="Username already exists") # Check for username uniqueness
        user.username = new_username
    
    # Update profile picture (similar to registration)
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and allowed_file(file.filename):
            # .. save file to choosen location
            user.profile_picture = filename
    
    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200 # success

# For profile pic on register
ALLOWED_EXTENSIONS = {"png", "jpg","jpeg", "gif"}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for register users
@app.route('/register', methods=["POST"])
def register_user():
    # Registration logic 
    email = request.json['email']
    username = request.json['username']
    password = request.json['password']

    # If user exists alreadu in data 
    user_exists = User.query.filter_by(email=email).first() is not None
     # Gives 409 conflict - user exists
    if user_exists:
        return jsonify({"error": "User already exists"}), 409
    hased_password = bcrypt.generate_password_hash(password)
    new_user = User(email=email, password=hashed_password, username=username)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "id": new_user.id,
        "email": new_user.email,
        "username": new_user.username,
        "password": new_user.password
            })

# LOGIN STATUS   
@app.route('/login', methods=["POST"]) 
def login_user():
    email = request.json["email"]
    password = request.json["password"]

    user = User.query.filer_by(email=email).first()
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
@app.route('/login', methods=['POST'])
def logout():
    session.pop('user_id', None) # Clear the user ID from the sessionn
    return jsonify({"Message": "Logged out successfully"}), 200



# Main entry point
if __name__ == "__main__":
    app.run(debug=True)