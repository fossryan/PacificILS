from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default="Patron")  # Admin, Patron

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    available = db.Column(db.Boolean, default=True)
    metadata_format = db.Column(db.String(50), default="Dublin Core")
    book_metadata = db.Column(db.Text, nullable=True)
    digital_content_url = db.Column(db.String(200), nullable=True)

class Patron(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    borrowed_books = db.relationship('Borrow', backref='patron', lazy=True)

class Borrow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    patron_id = db.Column(db.Integer, db.ForeignKey('patron.id'), nullable=False)
    borrow_date = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.String(100), nullable=False)
    return_date = db.Column(db.String(100), nullable=True)
    fine = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="Borrowed")

class Acquisition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.Float, nullable=False)
    books_purchased = db.Column(db.Text)

# Role-based access control
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != "Admin":
            flash("Admin access required.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Helper Functions
def extend_due_date(due_date_str):
    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
    new_due_date = due_date + timedelta(days=7)
    return new_due_date.strftime("%Y-%m-%d")

# Routes
@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash('User already exists.', 'error')
            return redirect(url_for('sign_up'))
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('sign_up.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'error')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route("/", methods=["GET"])
def index():
    search_query = request.args.get("search", "")
    if search_query:
        books = Book.query.filter(
            (Book.title.ilike(f"%{search_query}%")) | (Book.author.ilike(f"%{search_query}%"))
        ).all()
    else:
        books = Book.query.all()
    return render_template("index.html", books=books)

@app.route('/add_book', methods=['GET', 'POST'])
@admin_required
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        metadata_format = request.form['metadata_format']
        book_metadata = request.form['book_metadata']
        digital_content_url = request.form.get('digital_content_url')
        new_book = Book(
            title=title, author=author, category=category,
            metadata_format=metadata_format, book_metadata=book_metadata,
            digital_content_url=digital_content_url
        )
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/report')
@admin_required
def report():
    total_books = Book.query.count()
    total_patrons = Patron.query.count()
    total_borrows = Borrow.query.count()
    overdue_books = Borrow.query.filter(Borrow.due_date < datetime.now().strftime("%Y-%m-%d")).count()
    return render_template('report.html', total_books=total_books, total_patrons=total_patrons, total_borrows=total_borrows, overdue_books=overdue_books)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
