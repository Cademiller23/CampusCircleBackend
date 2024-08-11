# Server side session with added import stored
# Server side session with added import stored
# Server side session with added import stored
from flask import Flask, request, jsonify, session, abort, send_from_directory, url_for # core flask imports
from flask_bcrypt import Bcrypt # For Password Hashing
from flask_session import Session # For server-side Session Management
from models import User, Post, Comment, Like, Poll, PollOption, PollVote # Import the user and post model
from flask_migrate import Migrate
from sqlalchemy.orm import joinedload
from google.cloud import storage
from config import ApplicationConfig # Import App config
from database import db # Import the database instance
from sqlalchemy import desc
from werkzeug.utils import secure_filename 
# from authlib.integrations.flask_client import OAuth
from flask_cors import CORS 
from openai import OpenAI, Image
from pathlib import Path
from PIL import Image as PILImage, ImageDraw, ImageFont
import io
import random
import smtplib
import os
import uuid
import base64
from sqlalchemy.sql import func 
# Create flask application instance 
app = Flask(__name__)
app.config.from_object(ApplicationConfig) # Load config from App Config

FONT_SIZE = 36

bcrypt = Bcrypt(app) # Initialize Bcrypt for password hashing
server_session = Session(app) # Initialize server-side session management 
db.init_app(app) # Initialize database with the Flask App
migrate = Migrate(app, db)
CORS(app, origins= '*')
client = OpenAI(api_key=app.config['SECRET_KEY'])


# GOOGLE API INTEGRATION
def get_gcs_client():
    return storage.Client()

# oauth = OAuth(app)
# google = oauth.register(
#     name='google',
#     client_id=app.config['GOOGLE_CLIENT_ID'],
#     client_secret= app.config['GOOGLE_CLIENT_SECRET'],
#     authorize_url='https://accounts.google.com/o/oauth2/auth',
#     access_token_url='https://accounts.google.com/o/oauth2/token',
#     client_kwargs={'scope': 'openid profile email'},
#     redirect_uri='http://127.0.0.1:5000/auth/callback' # ADJUST WHEN GET DOMAIN
# )
# # Auth_CallBACK
# @app.route('/auth/callback')
# def auth_callback():
#     token = google.authorize_access_token()
#     user_info = google.parse_id_token(token)

#     if not user_info:
#         return jsonify({"error": "Failed to get user info"}), 400
#         user = User.query.filter_by(email=user_info['email']).first()

#         if not user: 
#             # If user doesn't exist create a new One
#             user = User(
#                 email=user_info['email'],
#                 username=user_info['name'], # Or however you want to handle the username

#             )
#             db.session.add(user)
#         db.session.commit()

#     session['user_id'] = user.id
#     return jsonify({"message": "Login successful", "user": {"id": user.id, "email": user.email}}), 200

# # LOGIN GOOGLE 
# @app.route('/login/google')
# def login_google():
#     redirect_uri = url_for('auth_callback', _external=True)
#     return google.authorize_redirect(redirect_uri)
# Sign Up GOOGLE

   
# Create database tables if they don't exist 
with app.app_context():
    db.create_all()

# For profile pic on register
ALLOWED_EXTENSIONS = {"png", "jpg","jpeg", "mp4", "mov"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Upload Google Cloud
def upload_to_gcs(file, bucket_name, filename):
    "Uploads a file to google cloud storage and returns the public URL"

    try:
        client = storage.Client()
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_file(file, content_type=file.content_type)
        # blob.make_public() 
        return f"https://storage.googleapis.com/{bucket_name}/{filename}"
    except Exception as e:
        print(f"Faied to upload to GCS: {e}")
        return None

# The POLLS 
# Fetch other User Polls
@app.route('/fetch_other_polls', methods=['GET'])
def fetch_other_polls():
    current_user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    try:
        polls_query = Poll.query.order_by(func.random()).filter(Poll.user_id != current_user_id)

        response_data = fetch_polls(polls_query, page, per_page)
        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error getting polls: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Get Current User Polls 
@app.route('/get_user_polls', methods=['GET'])
def get_user_polls():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    polls_query = Poll.query.filter_by(user_id=user_id)
    response_data = fetch_polls(polls_query, page=1, per_page=10)
    return jsonify(response_data), 200


def fetch_polls(query, page, per_page):
    polls = query.paginate(page=page, per_page=per_page, error_out=False)
    polls_list = [
        {
            'id': poll.id,
            'user_id': poll.user_id,
            'username': poll.user.username,
            'title': poll.title,
            'options': get_poll_options(poll)
        } for poll in polls.items
    ]
    return {
        'polls': polls_list,
        'total': polls.total,
        'has_next': polls.has_next
    }
def get_poll_options(poll):
    options = PollOption.query.filter_by(poll_id=poll.id).all()
    return [
        {
            'id': option.id,
            'text': option.text,
            'vote_count': option.vote_count
        }
        for option in options
    ]
# Create Poll Route
@app.route('/create_poll', methods=['POST'])
def create_poll():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    title = data.get('title')
    options = data.get('options')
    
    if not title or not options or len(options) < 2:
        return jsonify({"error": "Invalid poll data"}), 400
    
    # Validate unique options
    if len(set(options)) != len(options):
        return jsonify({"error": "Poll options must be unique"}), 400

    try:
        user = User.query.get(user_id)
        new_poll = Poll(title=title, user=user)
        db.session.add(new_poll)
        db.session.flush()

        for option_text in options:
            new_option = PollOption(text=option_text, poll_id=new_poll.id)
            db.session.add(new_option)

        db.session.commit()
        return jsonify({"message": "Poll created successfully", "poll_id": new_poll.id}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error creating poll: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Voting Route
@app.route('/vote_poll/<poll_id>/<option_id>', methods=['POST'])
def vote_poll(poll_id, option_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Fetch and lock the poll and option for update
        poll = Poll.query.with_for_update().get(poll_id)
        poll_option = PollOption.query.filter_by(id=option_id, poll_id=poll_id).with_for_update().first()
        
        if not poll or not poll_option:
            return jsonify({"error": "Invalid poll or option"}), 400
        
        # Check if the user has already voted on this poll
        existing_vote = PollVote.query.filter_by(user_id=user_id, poll_id=poll_id).first()
        if existing_vote:
            return jsonify({"error": "User has already voted on this poll"}), 400

        new_vote = PollVote(user_id=user_id, poll_id=poll_id, option_id=option_id)
        db.session.add(new_vote)
        poll_option.vote_count += 1

        # Refresh poll and options to get the latest data
        db.session.refresh(poll)
        db.session.refresh(poll_option)
        db.session.commit()

        poll_data = {  # Ensure the returned data is consistent
            'id': poll.id,
            'title': poll.title,
            'options': get_poll_options(poll),
            'user_id': poll.user_id,
            'username': poll.user.username
        }
        return jsonify(poll_data), 200
    except Exception as e:  # Add a general exception handler
        db.session.rollback()
        print(f"Error voting on poll: {e}")
        return jsonify({"error": "Internal server error"}), 500



# Count total number of user posts():
@app.route('/user_total_posts', methods=['GET'])
def user_total_posts():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    total_posts = Post.query.filter_by(user_id=user_id).count()
    return jsonify({"total_posts": total_posts}), 200

# Creating the likes for posts
@app.route('/like_post/<post_id>', methods=['POST'])
def like_post(post_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    # Check if the user has already liked or disliked this post
    existing_like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if existing_like:
        if existing_like.is_like:
            return jsonify({"message": "Post already liked"}), 400
        else:
            # If the user has disliked the post, switch to like
            existing_like.is_like = True
            post.like_count += 2  # Increase like_count by 2 (remove dislike, add like)
    else:
        # Add a new like
        new_like = Like(user_id=user_id, post_id=post_id, is_like=True)
        post.like_count += 1  # Increase like_count by 1
        db.session.add(new_like)
    
    db.session.commit()
    update_user_total_likes(user_id)
    return jsonify({"message": "Post liked successfully", "like_count": post.like_count}), 200

# Creating the likes for posts
@app.route('/dislike_post/<post_id>', methods=['POST'])
def dislike_post(post_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    # Check if the user has already liked or disliked this post
    existing_like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()

    if existing_like:
        if not existing_like.is_like:
            return jsonify({"message": "Post already disliked"}), 400
        else:
            # If the user has liked the post, switch to dislike
            existing_like.is_like = False
            post.like_count -= 2  # Decrease like_count by 2 (remove like, add dislike)
    else:
        # Add a new dislike
        new_dislike = Like(user_id=user_id, post_id=post_id, is_like=False)
        post.like_count -= 1  # Decrease like_count by 1
        db.session.add(new_dislike)
    
    db.session.commit()
    update_user_total_likes(user_id)
    return jsonify({"message": "Post disliked successfully", "like_count": post.like_count}), 200

# Update user Likes 
def update_user_total_likes(user_id):
    # Calculate the total likes for the user
    total_likes = db.session.query(db.func.sum(Post.like_count)).filter(Post.user_id == user_id).scalar() or 0
    user = User.query.get(user_id)
    user.total_likes = total_likes
    db.session.commit()
# Creating the total likes 
@app.route('/user_total_likes', methods=['GET'])
def user_total_likes():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    total_likes = db.session.query(db.func.sum(Post.like_count)).filter(Post.user_id == user_id).scalar() or 0
    return jsonify({"total_likes": total_likes}), 200


# AI Portion Finishede can use for profile Image as well
@app.route('/create_image_w_prompt', methods=['POST'])
def create_prompt_image():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unathorized"}), 401
    try:
        prompt = request.form.get("prompt")
        response = client.images.generate(
            model='dall-e-3',
            prompt=prompt,
            size='1024x1024',
            quality='standard',
            n=1,
        )
        print("DALL-E Response:", response)
        image_url = response.data[0].url 
        return jsonify({"image_url": image_url})
    except Exception as e:
        print(f"Error Creating a prompted image: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# NEED for manipulating Image
@app.route('/manipulate_image', methods=['POST'])
def manipulate_image():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        file = request.files.get('image')
        prompt = request.form.get('prompt')

        if not file or not prompt:
            return jsonify({"error": "Missing image or prompt"}), 400

        # Check file format
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file format. Only PNG, JPG, JPEG are allowed."}), 400

        # Open the image using PIL
        image = PILImage.open(file)

        # Convert to RGB if necessary (some PNGs might be in other modes)
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # Create a BytesIO object to store the image data
        img_byte_arr = io.BytesIO()

        # Save the image in PNG format with optimized compression
        image.save(img_byte_arr, format='png', optimize=True)

        # Check size and resize if necessary
        while img_byte_arr.tell() > 4 * 1024 * 1024:  # Loop until size is under 4MB
            img_byte_arr.seek(0)
            image = image.resize((int(image.width * 0.9), int(image.height * 0.9)))  # Reduce by 10% each time
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='png', optimize=True)

        # Reset the file pointer to the beginning
        img_byte_arr.seek(0)

        # DALL-E image manipulation request
        response = client.images.edit(
            image=img_byte_arr,  # Use the BytesIO object directly
            prompt=prompt,
            n=1,
            size="1024x1024",
        )
       
        # Extract URL
        manipulated_image_url = response.data[0].url

        return jsonify({"manipulated_image_url": manipulated_image_url}), 200

    except Exception as e:
        print(f"Error manipulating image: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/save_post/<post_id>', methods=['POST'])
def save_post(post_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Fetch the original post
        original_post = Post.query.get(post_id)
        if not original_post:
            return jsonify({"error": "Original Post not found"}), 400

        
        # Create a new post object with the same content but associated with the current user
        new_post = Post(
            user_id=user_id,
            content_type=original_post.content_type,
            content_url=original_post.content_url,
            category=original_post.category
        )
        db.session.add(new_post)
        db.session.commit()

        return jsonify({"message": "Post saved successfully"}), 201
    except Exception as e:
        print(f'Error saving post: {e}')
        return jsonify({"error": "Internal Server Error"}), 500

# Get saved POsts for the Logged in User
@app.route('/saved_posts', methods=['GET'])
def get_saved_post():
    user_id = session.get('user_id')
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
            filename = secure_filename(file.filename)
            unique_filename = f"{str(uuid.uuid4())}_{filename}"
            bucket_name = app.config['GOOGLE_CLOUD_STORAGE_BUCKET']

            # Upload the file to Google Cloud Storage
            file_url = upload_to_gcs(file, bucket_name, unique_filename)

            if not file_url:
                return jsonify({"error": "Failed to upload to GCS"}), 500

            new_post = Post(
                user_id=user_id,
                content_type=request.form.get('content_type', 'image/jpeg' if file.mimetype.startswith('image') else 'video/mp4'),  # Default to 'image/jpeg'
                content_url=file_url,  # Store the base64 encoded image
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
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', default=None)

    try:
        posts_query = Post.query.filter(Post.content_type != None).order_by(func.random())

        if current_user_id:
            posts_query = posts_query.filter(Post.user_id != current_user_id)

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
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(user_id)
    polls = Poll.query.filter_by(user_id=user_id).all()

    poll_data = [{
        'id': poll.id,
        'title': poll.title,
        'options': [{'id': option.id, 'text': option.text, 'vote_count': option.vote_count} for option in poll.options],
        'category': poll.category
    } for poll in polls]

    return jsonify({
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "profile_picture": user.profile_picture,  # Use the URL directly
        "polls": poll_data
    }), 200

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
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{str(uuid.uuid4())}_{filename}"
                bucket_name = app.config['GOOGLE_CLOUD_STORAGE_BUCKET']
    
        # Upload to GCS
                file_url = upload_to_gcs(file, bucket_name, unique_filename)
                if not file_url:
                    return jsonify({"error": "Failed to upload to GCS"}), 500

                user.profile_picture = file_url  # Store the GCS URL

        db.session.commit()
        return jsonify({
            "message": "Profile updated successfully",
            "profile_picture": user.profile_picture
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating profile: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

verification_codes = {}

# Route for register users
@app.route('/register', methods=["POST"])
def register_user():
    
    # Registration logic 
    data = request.get_json()
    email = data.get('email')

    if not email or not email.endswith('@usc.edu'):
        return jsonify({"error": "Invalid email address"}), 400

    # If user exists alreadu in data 
    user_exists = User.query.filter_by(email=email).first() is not None
     # Gives 409 conflict - user exists
    if user_exists:
        return jsonify({"error": "User already exists"}), 409
    
    # Generate a 6-digit veriification Code
    verification_code = random.randint(100000, 999999)
    verification_codes[email] = verification_code
    
    # Send the verification code via email 
    try: 
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('Caderyland1@gmail.com', 'Caderyland#23')
            server.sendmail('Caderyland@gmail.com', email, f'subject: Verification Code\n\nYour Verification code is {verification_code}')
    except Exception as e:
        return jsonify({"error": "Failed to send verification email"}), 500

    return jsonify({"message": "Verification code sent to email"}), 200

# Route to verify the email code
@app.route('/verify_email', methods=['POST']):
def verify_email():
    data = request.get_json()
    email = data.get('email')
    code = int(data.get('code'))

    if email not in verification_codes or verification_code[email] != code:
        return jsonify({'error', 'Invalid Verification code'})
    retur jsonify({"message": "Email verified successfully"})
# Finishing Registration
@app.route('/complete_registration', methods=["POST"]):
def complete_registration():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    
    # Check if the email has been verified
    if email not in verification_codes:
        return jsonify({"error": "Email not verified"})
    
    # Check if username is already taken
    username_exists = User.query.filter_by(username=username).first() is not None
    if username_exists:
        return jsonify({"error": "Username already exists"}), 409
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(email=email, password=hashed_password, username=username)

    db.session.add(new_user)
    db.session.commit()

    session['user_id'] = new_user.id
    del verification_codes[email]  # Remove the verification code as it is no longer needed

    return jsonify({
        "id": new_user.id,
        "email": new_user.email,
        "username": new_user.username,
    }), 201

    
# LOGIN STATUS   
@app.route('/login', methods=["POST"]) 
def login_user():
    identifier = request.json.get('identifier')
    password = request.json.get('password')

    # CHeck if the identifier is an email or username 
    if '@' in identifier:
        user = User.query.filter_by(email=identifier).first()
    else:
        user = User.query.filter_by(username=identifier).first()

    # No user exists
    if user is None:
        return jsonify({"error": "Unauthorized"}), 401
    
    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Unauthorized"}), 401
    
    session["user_id"] = user.id
    return jsonify({
        "id": user.id,
        "email": user.email,
        "username": user.username
    }), 200

# Logout Status 
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None) # Clear the user ID from the sessionn
    return jsonify({"Message": "Logged out successfully"}), 200



# Main entry point
if __name__ == "__main__":
    app.run(debug=True, static_folder='static', host='0.0.0.0')
