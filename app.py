from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId
import jwt, bcrypt, secrets, io, csv, re,os

app = Flask(__name__)
CORS(app)

# -----------------------------
# Config
# -----------------------------
app.config["SECRET_KEY"] = "supersecretjwtkey"
app.config["JWT_EXP_DELTA_SECONDS"] = 3600

# ✅ MongoDB Atlas connection
client = MongoClient(
    "mongodb+srv://drroshini16_db_user:RPmF63fvR3eiZvjD@cluster0.pdu4tsr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
db = client["student_admin"]

# -----------------------------
# Helper Functions
# -----------------------------
def encode_token(user_id, role):
    payload = {
        "user_id": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(seconds=app.config["JWT_EXP_DELTA_SECONDS"])
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

def decode_token(token):
    try:
        return jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    except:
        return None

def token_required(role=None):
    def decorator(f):
        def wrapper(*args, **kwargs):
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if not token:
                return jsonify({"error": "Authentication required"}), 401
            data = decode_token(token)
            if not data:
                return jsonify({"error": "Invalid or expired token"}), 401
            if role and data.get("role") != role:
                return jsonify({"error": "Forbidden"}), 403
            return f(*args, **kwargs, user_id=data["user_id"], role=data["role"])
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

def safe_objectid(oid):
    try:
        return ObjectId(oid)
    except:
        return None

def validate_password(password: str):
    """Simple password policy: at least 8 chars, 1 digit, 1 letter"""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True

# -----------------------------
# AUTH ROUTES
# -----------------------------
@app.route("/auth/signup", methods=["POST"])
def signup():
    data = request.json
    email = data["email"].lower()
    if db.users.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 400
    if not validate_password(data["password"]):
        return jsonify({"error": "Weak password (min 8 chars, include letters & numbers)"}), 400
    hashed = hash_password(data["password"])
    user = {
        "name": data["name"],
        "email": email,
        "password": hashed,
        "role": "student",
        "phone": "",
        "dob": "",
        "address": "",
        "profile_picture": "",
        "blocked": False
    }
    res = db.users.insert_one(user)
    return jsonify({"id": str(res.inserted_id), "message": "User created"}), 201

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    email = data["email"].lower()
    user = db.users.find_one({"email": email})
    if not user or not verify_password(data["password"], user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    if user.get("blocked", False):
        return jsonify({"error": "User blocked"}), 403
    token = encode_token(user["_id"], user["role"])
    return jsonify({"token": token})

@app.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    email = request.json.get("email", "").lower()
    user = db.users.find_one({"email": email})
    if not user:
        return jsonify({"error": "Email not found"}), 404
    reset_token = secrets.token_urlsafe(16)
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"reset_token": reset_token, "reset_expires": datetime.utcnow() + timedelta(hours=1)}}
    )
    # ⚠️ In production, send email with reset link instead of returning token
    return jsonify({"reset_token": reset_token})

@app.route("/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.json
    email = data["email"].lower()
    user = db.users.find_one({"email": email, "reset_token": data["token"]})
    if not user or datetime.utcnow() > user.get("reset_expires", datetime.utcnow()):
        return jsonify({"error": "Invalid or expired token"}), 400
    if not validate_password(data["new_password"]):
        return jsonify({"error": "Weak password (min 8 chars, include letters & numbers)"}), 400
    hashed = hash_password(data["new_password"])
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hashed}, "$unset": {"reset_token": "", "reset_expires": ""}}
    )
    return jsonify({"message": "Password reset successful"})

# -----------------------------
# PROFILE ROUTES
# -----------------------------
@app.route("/profile", methods=["GET"])
@token_required()
def get_profile(user_id, role):
    obj_id = safe_objectid(user_id)
    if not obj_id:
        return jsonify({"error": "Invalid user ID"}), 400
    user = db.users.find_one({"_id": obj_id}, {"password": 0})
    if not user:
        return jsonify({"error": "User not found"}), 404
    user["_id"] = str(user["_id"])
    return jsonify(user)

@app.route("/profile", methods=["PUT"])
@token_required()
def update_profile(user_id, role):
    obj_id = safe_objectid(user_id)
    if not obj_id:
        return jsonify({"error": "Invalid user ID"}), 400
    data = request.json
    allowed_fields = ["name", "phone", "dob", "address", "profile_picture"]
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    db.users.update_one({"_id": obj_id}, {"$set": update_fields})
    return jsonify({"message": "Profile updated"})

@app.route("/profile/change-password", methods=["POST"])
@token_required()
def change_password(user_id, role):
    obj_id = safe_objectid(user_id)
    if not obj_id:
        return jsonify({"error": "Invalid user ID"}), 400
    data = request.json
    user = db.users.find_one({"_id": obj_id})
    if not user or not verify_password(data["current_password"], user["password"]):
        return jsonify({"error": "Current password incorrect"}), 400
    if not validate_password(data["new_password"]):
        return jsonify({"error": "Weak password"}), 400
    db.users.update_one({"_id": obj_id}, {"$set": {"password": hash_password(data["new_password"])}})
    return jsonify({"message": "Password changed"})

# -----------------------------
# COURSES ROUTES (Admin)
# -----------------------------
@app.route("/courses", methods=["POST"])
@token_required(role="admin")
def add_course(user_id, role):
    data = request.json
    if db.courses.find_one({"code": data["code"]}):
        return jsonify({"error": "Course already exists"}), 400
    course = {
        "code": data["code"],
        "title": data["title"],
        "description": data.get("description", ""),
        "created_at": datetime.utcnow()
    }
    db.courses.insert_one(course)
    return jsonify({"message": "Course added"})

@app.route("/courses/<code>", methods=["DELETE"])
@token_required(role="admin")
def delete_course(user_id, role, code):
    db.courses.delete_one({"code": code})
    return jsonify({"message": "Course deleted"})

@app.route("/courses", methods=["GET"])
@token_required()
def list_courses(user_id, role):
    courses = list(db.courses.find({}, {"_id": 0}))
    return jsonify(courses)

# -----------------------------
# FEEDBACK ROUTES
# -----------------------------
@app.route("/feedback", methods=["POST"])
@token_required(role="student")
def submit_feedback(user_id, role):
    data = request.json
    if not all(k in data for k in ["course_code", "rating", "message"]):
        return jsonify({"error": "Missing fields"}), 400
    user_doc = db.users.find_one({"_id": safe_objectid(user_id)})
    course_doc = db.courses.find_one({"code": data["course_code"]})
    if not course_doc:
        return jsonify({"error": "Course not found"}), 404
    db.feedback.insert_one({
        "course_code": data["course_code"],
        "rating": data["rating"],
        "message": data["message"],
        "student_id": user_id,
        "student_name": user_doc["name"],
        "created_at": datetime.utcnow()
    })
    return jsonify({"message": "Feedback submitted"}), 201

@app.route("/feedback", methods=["GET"])
@token_required(role="student")
def list_my_feedback(user_id, role):
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 5))
    feedbacks = list(db.feedback.find({"student_id": user_id}).skip((page-1)*per_page).limit(per_page))
    for f in feedbacks:
        f["_id"] = str(f["_id"])
    return jsonify(feedbacks)

@app.route("/feedback/<feedback_id>", methods=["PUT"])
@token_required(role="student")
def edit_feedback(user_id, role, feedback_id):
    fid = safe_objectid(feedback_id)
    if not fid:
        return jsonify({"error": "Invalid feedback ID"}), 400
    data = request.json
    db.feedback.update_one({"_id": fid, "student_id": user_id}, {"$set": data})
    return jsonify({"message": "Feedback updated"})

@app.route("/feedback/<feedback_id>", methods=["DELETE"])
@token_required(role="student")
def delete_feedback(user_id, role, feedback_id):
    fid = safe_objectid(feedback_id)
    if not fid:
        return jsonify({"error": "Invalid feedback ID"}), 400
    db.feedback.delete_one({"_id": fid, "student_id": user_id})
    return jsonify({"message": "Feedback deleted"})

# -----------------------------
# ADMIN FEEDBACK MANAGEMENT
# -----------------------------
@app.route("/admin/stats", methods=["GET"])
@token_required(role="admin")
def admin_stats(user_id, role):
    total_feedback = db.feedback.count_documents({})
    total_students = db.users.count_documents({"role": "student"})
    pipeline = [{"$group": {"_id": "$course_code", "average_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}]
    trends = list(db.feedback.aggregate(pipeline))
    return jsonify({"total_feedback": total_feedback, "total_students": total_students, "feedback_trends": trends})

@app.route("/admin/students", methods=["GET"])
@token_required(role="admin")
def list_students(user_id, role):
    students = list(db.users.find({"role": "student"}, {"password": 0}))
    for s in students:
        s["_id"] = str(s["_id"])
    return jsonify(students)

@app.route("/admin/students/<student_id>/block", methods=["POST"])
@token_required(role="admin")
def block_unblock_student(user_id, role, student_id):
    obj_id = safe_objectid(student_id)
    if not obj_id:
        return jsonify({"error": "Invalid student ID"}), 400
    action = request.json.get("action")
    if action not in ["block", "unblock"]:
        return jsonify({"error": "Invalid action, must be 'block' or 'unblock'"}), 400
    blocked = True if action == "block" else False
    db.users.update_one({"_id": obj_id}, {"$set": {"blocked": blocked}})
    return jsonify({"message": f"Student {'blocked' if blocked else 'unblocked'}"})

@app.route("/admin/students/<student_id>", methods=["DELETE"])
@token_required(role="admin")
def delete_student(user_id, role, student_id):
    obj_id = safe_objectid(student_id)
    if not obj_id:
        return jsonify({"error": "Invalid student ID"}), 400
    db.users.delete_one({"_id": obj_id})
    return jsonify({"message": "Student deleted"})

@app.route("/admin/feedback", methods=["GET"])
@token_required(role="admin")
def view_all_feedback(user_id, role):
    query = {}
    course_filter = request.args.get("course")
    rating_filter = request.args.get("rating")
    student_filter = request.args.get("student")
    if course_filter:
        query["course_code"] = course_filter
    if rating_filter:
        try:
            query["rating"] = int(rating_filter)
        except:
            return jsonify({"error": "Invalid rating filter"}), 400
    if student_filter:
        query["student_name"] = student_filter
    feedbacks = list(db.feedback.find(query))
    for f in feedbacks:
        f["_id"] = str(f["_id"])
    return jsonify(feedbacks)

@app.route("/feedback/export", methods=["GET"])
@token_required(role="admin")
def export_feedback(user_id, role):
    feedbacks = list(db.feedback.find({}))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["course_code","student_name","rating","message","created_at"])
    for f in feedbacks:
        writer.writerow([f["course_code"], f["student_name"], f["rating"], f["message"], f["created_at"]])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="feedback_export.csv")

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    # Create default admin if not exists
    if not db.users.find_one({"email": "admin123@example.com"}):
        db.users.insert_one({
            "name": "Admin User",
            "email": "admin123@example.com",
            "password": hash_password("Admin@1234"),
            "role": "admin"
        })
    port = int(os.environ.get("PORT", 7860))  # use HF-provided port or default 7860
    app.run(host="0.0.0.0", port=port, debug=True)
