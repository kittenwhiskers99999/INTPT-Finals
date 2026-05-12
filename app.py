from flask import Flask, request, redirect, url_for, session, render_template
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
UPLOAD_FOLDER = os.path.join('static', 'uploads')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'change-this-secret'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# DATABASE CONNECTION
# =========================
def get_db():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='spotifind'
    )


# =========================
# ROUTES
# =========================
@app.route('/', methods=['GET', 'POST'])
def index():
    if session.get('username'):
        return redirect(url_for('homepage'))

    message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            message = 'Please enter both username and password.'
        else:
            try:
                db = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()
                cursor.close()
                db.close()

                if not user or not check_password_hash(user['password'], password):
                    message = 'Invalid username or password.'
                else:
                    session['username'] = username
                    return redirect(url_for('homepage'))

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('login.html', title='Login', message=message)


@app.route('/home')
def homepage():
    if not session.get('username'):
        return redirect(url_for('index'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM lost_items ORDER BY reported_at DESC')
        lost_items = cursor.fetchall()
        cursor.execute('SELECT * FROM found_items ORDER BY reported_at DESC')
        found_items = cursor.fetchall()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        lost_items = []
        found_items = []
    return render_template('home.html', lost_items=lost_items, found_items=found_items, active='all')


@app.route('/lost')
def lost_page():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM lost_items ORDER BY reported_at DESC')
        lost_items = cursor.fetchall()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        lost_items = []
    return render_template('home.html', lost_items=lost_items, found_items=[], active='lost')


@app.route('/found')
def found_page():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM found_items ORDER BY reported_at DESC')
        found_items = cursor.fetchall()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        found_items = []
    return render_template('home.html', lost_items=[], found_items=found_items, active='found')


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            message = 'Please enter both username and password.'
        else:
            try:
                db = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()
                cursor.close()
                db.close()

                if not user or not check_password_hash(user['password'], password):
                    message = 'Invalid username or password.'
                else:
                    session['username'] = username
                    return redirect(url_for('homepage'))

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('login.html', title='Login', message=message)


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        username         = request.form.get('username', '').strip()
        email            = request.form.get('email', '').strip()
        contact_number   = request.form.get('contact_number', '').strip()
        location         = request.form.get('location', '').strip()
        password         = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not all([username, email, contact_number, location, password, confirm_password]):
            message = 'Please fill in all fields.'
        elif password != confirm_password:
            message = 'Passwords do not match.'
        else:
            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute(
                    'SELECT id FROM users WHERE username = %s OR email = %s',
                    (username, email)
                )
                existing = cursor.fetchone()

                if existing:
                    message = 'Username or email is already taken.'
                else:
                    hashed_pw = generate_password_hash(password)
                    cursor.execute(
                        'INSERT INTO users (username, password, email, contact_number, location) VALUES (%s, %s, %s, %s, %s)',
                        (username, hashed_pw, email, contact_number, location)
                    )
                    db.commit()
                    session['username'] = username
                    cursor.close()
                    db.close()
                    return redirect(url_for('homepage'))

                cursor.close()
                db.close()

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('register.html', title='Register', message=message)


@app.route('/report-lost', methods=['GET', 'POST'])
def report_lost():
    if not session.get('username'):
        return redirect(url_for('index'))

    message = None
    success = None

    if request.method == 'POST':
        item_type   = request.form.get('type', '').strip()
        color       = request.form.get('color', '').strip()
        location    = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()

        if not all([item_type, color, location, description]):
            message = 'Please fill in all fields.'
        else:
            try:
                # Handle image upload
                image_filename = None
                file = request.files.get('image')
                if file and allowed_file(file.filename):
                    image_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

                db = get_db()
                cursor = db.cursor()

                cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
                user = cursor.fetchone()
                user_id = user[0] if user else None

                cursor.execute(
                    'INSERT INTO lost_items (user_id, type, color, location, description, image) VALUES (%s, %s, %s, %s, %s, %s)',
                    (user_id, item_type, color, location, description, image_filename)
                )
                db.commit()
                cursor.close()
                db.close()
                success = 'Your lost item has been reported successfully!'

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('report_lost.html', message=message, success=success)



@app.route('/report-found', methods=['GET', 'POST'])
def report_found():
    if not session.get('username'):
        return redirect(url_for('index'))

    message = None
    success = None

    if request.method == 'POST':
        item_type   = request.form.get('type', '').strip()
        color       = request.form.get('color', '').strip()
        location    = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()

        if not all([item_type, color, location, description]):
            message = 'Please fill in all fields.'
        else:
            try:
                # Handle image upload
                image_filename = None
                file = request.files.get('image')
                if file and allowed_file(file.filename):
                    image_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

                db = get_db()
                cursor = db.cursor()

                cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
                user = cursor.fetchone()
                user_id = user[0] if user else None

                cursor.execute(
                    'INSERT INTO found_items (user_id, type, color, location, description, image) VALUES (%s, %s, %s, %s, %s, %s)',
                    (user_id, item_type, color, location, description, image_filename)
                )
                db.commit()
                cursor.close()
                db.close()
                success = 'Your found item has been reported successfully!'

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('report_found.html', message=message, success=success)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)
