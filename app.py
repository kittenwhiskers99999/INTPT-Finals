from flask import Flask, request, redirect, url_for, session, render_template

app = Flask(__name__)
app.secret_key = 'change-this-secret'

# In-memory user store: username -> password
users = {}

# Sample data
lost_items = [
    {
        "emoji": "📱",
        "title": "iPhone 13",
        "location": "Near school gate",
        "description": "Black phone with stickers"
    },
    {
        "emoji": "🎧",
        "title": "Wireless Earbuds",
        "location": "Library Area",
        "description": "White earbuds in blue case"
    }
]

found_items = [
    {
        "emoji": "⌚",
        "title": "Silver Watch",
        "location": "Gymnasium",
        "description": "Found near bleachers"
    },
    {
        "emoji": "📘",
        "title": "Blue Notebook",
        "location": "Room 204",
        "description": "Contains science notes"
    }
]


@app.route('/')
def index():
    # Already logged in → go to home
    if session.get('username'):
        return redirect(url_for('homepage'))
    # Not logged in → show login page
    return render_template('login.html', title='Login', message=None)


@app.route('/home')
def homepage():
    if not session.get('username'):
        return redirect(url_for('index'))
    return render_template(
        'home.html',
        lost_items=lost_items,
        found_items=found_items,
        active='all'
    )


@app.route('/lost')
def lost_page():
    return render_template(
        'home.html',
        lost_items=lost_items,
        found_items=[],
        active='lost'
    )


@app.route('/found')
def found_page():
    return render_template(
        'home.html',
        lost_items=[],
        found_items=found_items,
        active='found'
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            message = 'Please enter both username and password.'
        elif users.get(username) != password:
            message = 'Invalid username or password.'
        else:
            session['username'] = username
            return redirect(url_for('homepage'))

    return render_template('login.html', title='Login', message=message)


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username or not password or not confirm_password:
            message = 'Please fill in all fields.'
        elif password != confirm_password:
            message = 'Passwords do not match.'
        elif username in users:
            message = 'That username is already taken.'
        else:
            users[username] = password
            session['username'] = username
            return redirect(url_for('homepage'))

    return render_template('register.html', title='Register', message=message)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)