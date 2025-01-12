from flask import Blueprint, current_app, flash
from flask import request, render_template, redirect, url_for

from flask_login import login_user, logout_user, login_required
from google.oauth2 import id_token
from google.auth.transport import requests


bp = Blueprint("auth", "auth", url_prefix="/auth")

@bp.route("/login/student", methods=["GET"])
def loginStudent():
    next = ''
    if 'next' in request.args:
        next = request.args.get('next')

    return render_template('login_student.html',next=next)

@bp.route("/login/admin", methods=["GET"])
def loginAdmin():
    next = ''
    if 'next' in request.args:
        next = request.args.get('next')
    return render_template('login_admin.html',next=next)

@bp.route("/login/callback", methods=["POST"])
def loginCallback():

    csrf_token_cookie = request.cookies.get('g_csrf_token')
    if not csrf_token_cookie:
        return 'No CSRF token in Cookie.', 400
    csrf_token_body = request.form.get('g_csrf_token')
    if not csrf_token_body:
        return 'No CSRF token in post body.', 400
    if csrf_token_cookie != csrf_token_body:
        return 'Failed to verify double submit cookie.', 400

    token = request.form.get('credential')
    
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), current_app.config['GOOGLE_CLIENT_ID'])

        # Or, if multiple clients access the backend server:
        # idinfo = id_token.verify_oauth2_token(token, requests.Request())
        # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
        #     raise ValueError('Could not verify audience.')

        # If auth request is from a G Suite domain:
        # if idinfo['hd'] != GSUITE_DOMAIN_NAME:
        #     raise ValueError('Wrong hosted domain.')

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        if idinfo['email_verified']:
            id_ = idinfo['sub']
            email = idinfo['email']
            profilePic = idinfo['picture']
            name = idinfo['name']

            
            from .user import User

            userClass=request.args.get('user-class')

            if not User.get(id_):
                if userClass == "student":
                    retCode = User.createStudent(id=id_, name=name, email=email, profilePic=profilePic)
                    if retCode == -1:
                        return "Student not in database.", 400
                elif userClass == "admin":
                    retCode = User.createAdmin(id=id_, name=name, email=email, profilePic=profilePic)
                    if retCode == -1:
                        return "Admin not in database.", 400
                else:
                    return "Invalid request format", 400
            
            user = User.get(id_)

            if user.admin and userClass=="student":
                return "Not a student", 400
            elif not user.admin and userClass=="admin":
                return "Not an admin", 400

            # Send user back to homepage
            login_user(user)
            if 'next' not in request.args:
                if user.admin:
                    next_url = url_for('admin.index')
                else:
                    next_url = url_for('student.dashboard')
            else:
                if request.args.get('next') == '':
                    if user.admin:
                        next_url = url_for('admin.index')
                    else:
                        next_url = url_for('student.dashboard')
                else:
                    from .utils import get_safe_redirect
                    next_url = get_safe_redirect(request.args.get('next'))
            return redirect(next_url)

        else:
            return "User email not available or not verified by Google.", 400

    except ValueError:
        return "Invalid token.", 400

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Successfully logged out")

    if 'next' not in request.args:
        next_url = url_for('index')
    else:
        if request.args.get('next') == '':
            next_url = url_for('index')
        else:
            from .utils import get_safe_redirect
            next_url = get_safe_redirect(request.args.get('next'))
    return redirect(next_url)
