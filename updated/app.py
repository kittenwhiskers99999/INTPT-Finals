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
        cursor.execute('SELECT * FROM lost_items WHERE status = %s ORDER BY reported_at DESC', ('active',))
        lost_items = cursor.fetchall()
        cursor.execute('SELECT * FROM found_items WHERE status = %s ORDER BY reported_at DESC', ('active',))
        found_items = cursor.fetchall()
        cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
        u = cursor.fetchone()
        current_user_id = u['id'] if u else None
        cursor.close()
        db.close()
    except mysql.connector.Error:
        lost_items = []
        found_items = []
        current_user_id = None
    return render_template('home.html', lost_items=lost_items, found_items=found_items, active='all', current_user_id=current_user_id)


@app.route('/lost')
def lost_page():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM lost_items WHERE status = %s ORDER BY reported_at DESC', ('active',))
        lost_items = cursor.fetchall()
        cursor.execute('SELECT id FROM users WHERE username = %s', (session.get('username'),))
        u = cursor.fetchone()
        current_user_id = u['id'] if u else None
        cursor.close()
        db.close()
    except mysql.connector.Error:
        lost_items = []
        current_user_id = None
    return render_template('home.html', lost_items=lost_items, found_items=[], active='lost', current_user_id=current_user_id)


@app.route('/found')
def found_page():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM found_items WHERE status = %s ORDER BY reported_at DESC', ('active',))
        found_items = cursor.fetchall()
        cursor.execute('SELECT id FROM users WHERE username = %s', (session.get('username'),))
        u = cursor.fetchone()
        current_user_id = u['id'] if u else None
        cursor.close()
        db.close()
    except mysql.connector.Error:
        found_items = []
        current_user_id = None
    return render_template('home.html', lost_items=[], found_items=found_items, active='found', current_user_id=current_user_id)


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


@app.route('/claim/<string:table>/<int:item_id>', methods=['POST'])
def claim_item(table, item_id):
    if not session.get('username'):
        return redirect(url_for('index'))
    if table not in ('lost_items', 'found_items'):
        return redirect(url_for('homepage'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get user id
        cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
        user = cursor.fetchone()
        user_id = user['id'] if user else None

        # Only update if this user owns the item
        cursor.execute(f'UPDATE {table} SET status = %s WHERE id = %s AND user_id = %s', ('claimed', item_id, user_id))
        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        pass
    return redirect(url_for('lost_page') if table == 'lost_items' else url_for('found_page'))


@app.route('/delete/<string:table>/<int:item_id>', methods=['POST'])
def delete_item(table, item_id):
    if not session.get('username'):
        return redirect(url_for('index'))
    if table not in ('lost_items', 'found_items'):
        return redirect(url_for('homepage'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get user id
        cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
        user = cursor.fetchone()
        user_id = user['id'] if user else None

        # Only delete if this user owns the item
        cursor.execute(f'UPDATE {table} SET status = %s WHERE id = %s AND user_id = %s', ('deleted', item_id, user_id))
        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        pass
    return redirect(url_for('lost_page') if table == 'lost_items' else url_for('found_page'))


# =========================
# CHAT ROUTES
# =========================

@app.route('/chat/<string:item_type>/<int:item_id>')
def chat(item_type, item_id):
    if not session.get('username'):
        return redirect(url_for('index'))
    if item_type not in ('lost', 'found'):
        return redirect(url_for('homepage'))

    table = 'lost_items' if item_type == 'lost' else 'found_items'

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get current user
        cursor.execute('SELECT id, username FROM users WHERE username = %s', (session['username'],))
        current_user = cursor.fetchone()

        # Get item + reporter info
        cursor.execute(f'''
            SELECT i.*, u.username AS reporter_name, u.id AS reporter_id
            FROM {table} i
            JOIN users u ON i.user_id = u.id
            WHERE i.id = %s
        ''', (item_id,))
        item = cursor.fetchone()

        if not item:
            cursor.close()
            db.close()
            return redirect(url_for('homepage'))

        # Determine the other user (if reporter viewing, show all threads; if visitor, show their thread)
        is_reporter = current_user['id'] == item['reporter_id']

        if is_reporter:
            # Reporter sees list of all users who messaged about this item
            cursor.execute('''
                SELECT DISTINCT u.id, u.username
                FROM messages m
                JOIN users u ON (
                    CASE WHEN m.sender_id = %s THEN m.receiver_id ELSE m.sender_id END = u.id
                )
                WHERE m.item_id = %s AND m.item_type = %s
                AND (m.sender_id = %s OR m.receiver_id = %s)
            ''', (item['reporter_id'], item_id, item_type, item['reporter_id'], item['reporter_id']))
            threads = cursor.fetchall()

            # Get selected thread (from query param)
            from flask import request as freq
            selected_user_id = freq.args.get('with', type=int)

            messages = []
            other_user = None
            if selected_user_id:
                cursor.execute('SELECT id, username FROM users WHERE id = %s', (selected_user_id,))
                other_user = cursor.fetchone()
                cursor.execute('''
                    SELECT m.*, u.username AS sender_name
                    FROM messages m
                    JOIN users u ON m.sender_id = u.id
                    WHERE m.item_id = %s AND m.item_type = %s
                    AND ((m.sender_id = %s AND m.receiver_id = %s) OR (m.sender_id = %s AND m.receiver_id = %s))
                    ORDER BY m.sent_at ASC
                ''', (item_id, item_type, item['reporter_id'], selected_user_id, selected_user_id, item['reporter_id']))
                messages = cursor.fetchall()
                # Mark as read
                cursor.execute('''
                    UPDATE messages SET is_read = 1
                    WHERE item_id = %s AND item_type = %s AND sender_id = %s AND receiver_id = %s AND is_read = 0
                ''', (item_id, item_type, selected_user_id, item['reporter_id']))
                db.commit()
        else:
            threads = []
            other_user = {'id': item['reporter_id'], 'username': item['reporter_name']}
            cursor.execute('''
                SELECT m.*, u.username AS sender_name
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.item_id = %s AND m.item_type = %s
                AND ((m.sender_id = %s AND m.receiver_id = %s) OR (m.sender_id = %s AND m.receiver_id = %s))
                ORDER BY m.sent_at ASC
            ''', (item_id, item_type, current_user['id'], item['reporter_id'], item['reporter_id'], current_user['id']))
            messages = cursor.fetchall()
            # Mark as read
            cursor.execute('''
                UPDATE messages SET is_read = 1
                WHERE item_id = %s AND item_type = %s AND sender_id = %s AND receiver_id = %s AND is_read = 0
            ''', (item_id, item_type, item['reporter_id'], current_user['id']))
            db.commit()

        cursor.close()
        db.close()

        return render_template('chat.html',
            item=item,
            item_type=item_type,
            current_user=current_user,
            is_reporter=is_reporter,
            threads=threads,
            messages=messages,
            other_user=other_user
        )

    except mysql.connector.Error as e:
        return f'Database error: {e}'


@app.route('/chat/<string:item_type>/<int:item_id>/send', methods=['POST'])
def send_message(item_type, item_id):
    if not session.get('username'):
        return redirect(url_for('index'))

    message_text = request.form.get('message', '').strip()
    receiver_id  = request.form.get('receiver_id', type=int)

    if not message_text or not receiver_id:
        return redirect(url_for('chat', item_type=item_type, item_id=item_id))

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
        sender = cursor.fetchone()
        sender_id = sender['id']

        cursor.execute('''
            INSERT INTO messages (item_id, item_type, sender_id, receiver_id, message)
            VALUES (%s, %s, %s, %s, %s)
        ''', (item_id, item_type, sender_id, receiver_id, message_text))
        db.commit()
        cursor.close()
        db.close()

    except mysql.connector.Error as e:
        pass

    # Redirect back to chat
    from flask import request as freq
    with_param = request.form.get('with_user_id', type=int)
    if with_param:
        return redirect(url_for('chat', item_type=item_type, item_id=item_id) + f'?with={with_param}')
    return redirect(url_for('chat', item_type=item_type, item_id=item_id))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)