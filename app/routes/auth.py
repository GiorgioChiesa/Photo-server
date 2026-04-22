from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.gallery'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash('Invalid username or password', 'error')
            return render_template('auth/login.html')

        login_user(user, remember=True)
        flash(f'Welcome back, {user.username}!', 'success')

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.gallery'))

    return render_template('auth/login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.gallery'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html')

        user = User(username=username, email=email)
        user.set_password(password)

        if User.query.count() == 0:
            user.is_admin = True

        db.session.add(user)
        db.session.commit()

        flash('Account created! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/api/users/me')
def api_current_user():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401

    return jsonify({
        'user': current_user.to_dict(),
        'album_count': current_user.albums.count(),
        'media_count': current_user.media.count()
    })


@auth.route('/api/users/<int:user_id>')
@login_required
def api_user(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({'error': 'Permission denied'}), 403

    user = User.query.get_or_404(user_id)
    return jsonify({'user': user.to_dict()})