import datetime
import logging
import time
import os

from flask import render_template, url_for, session, request
from itsdangerous import URLSafeTimedSerializer


class EmailLoginService:
    """Encapsulates email registration / password reset flows with CAPTCHA.

    Returns dict objects with either:
      - {'template': 'template.html', 'context': {...}}
      - {'redirect': '/path'} (not currently used but reserved)
    The Flask route should render/redirect based on the returned dict.
    """

    def __init__(self, competitions_engine, email_sender, bcrypt, simple_captcha=None):
        """simple_captcha may be None for contexts (e.g. API) that don't use CAPTCHA."""
        self.ce = competitions_engine
        self.email_sender = email_sender
        self.bcrypt = bcrypt
        self.captcha = simple_captcha

    # ----------------------------- Helpers -----------------------------
    def _generate_token(self, email):
        serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
        return serializer.dumps(email, salt=os.getenv("SECURITY_PASSWORD_SALT"))

    def _confirm_token(self, token, expiration=3600):
        serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
        try:
            email = serializer.loads(
                token, salt=os.getenv('SECURITY_PASSWORD_SALT'), max_age=expiration
            )
            return email
        except Exception as e:  # pragma: no cover - defensive
            logging.warning("Token confirmation failed: %s", e)
            return False

    def _send_registration_email(self, email):
        token = self._generate_token(email)
        confirm_url = url_for('confirm_email', type='register', token=token, _external=True)
        self.email_sender.send_registration_email(email, confirm_url)
        return token

    def _get_translation(self, key):
        ref_lang = self.ce.reference_data.get('current_language', {})
        return ref_lang.get(key, key)

    # --------------------------- Public API ----------------------------
    def register_with_email(self):
        new_captcha_dict = self.captcha.create() if self.captcha else {}
        time.sleep(1)
        return {
            'template': 'register.html',
            'context': {
                'reference_data': self.ce.reference_data,
                'captcha': new_captcha_dict
            }
        }

    def register(self, form):
        new_captcha_dict = self.captcha.create() if self.captcha else {}
        email = form.get('email')
        if not email:
            return {
                'template': 'register.html',
                'context': {
                    'reference_data': self.ce.reference_data,
                    'error': self._get_translation('Please_try_again'),
                    'email': email,
                    'captcha': new_captcha_dict
                }
            }

        c_hash = form.get('captcha-hash')
        c_text = form.get('captcha-text')
        if self.captcha and not self.captcha.verify(c_text, c_hash):
            time.sleep(1)
            logging.info('captcha failed %s', email)
            return {
                'template': 'register.html',
                'context': {
                    'reference_data': self.ce.reference_data,
                    'error': self._get_translation('Please_try_again'),
                    'email': email,
                    'captcha': new_captcha_dict
                }
            }

        email = email.lower()
        user = self.ce.get_user_by_email(email)

        # User exists but not confirmed -> resend confirmation
        if user is not None and user.get('is_confirmed') is False:
            self._send_registration_email(email)
            logging.info('resending registration email to unconfirmed user %s', email)
            return {
                'template': 'competitionLogin.html',
                'context': {
                    'reference_data': self.ce.reference_data,
                    'error': self._get_translation('Please_check_your_email_for_confirmation_link'),
                    'email': email
                }
            }

        # User confirmed already -> send reset password link
        if user is not None and user.get('is_confirmed') is True:
            token = self._generate_token(email)
            confirm_url = url_for('confirm_email', type='reset_password', token=token, _external=True)
            self.email_sender.send_password_reset_email(email, confirm_url)
            logging.info("reset password email sent to %s", email)
            return {
                'template': 'competitionLogin.html',
                'context': {
                    'reference_data': self.ce.reference_data,
                    'error': self._get_translation('Link_to_reset_password_sent_to_email')
                }
            }

        # New registration flow
        self._send_registration_email(email)
        logging.info('sending registration email to %s', email)
        return {
            'template': 'register.html',
            'context': {
                'reference_data': self.ce.reference_data,
                'error': self._get_translation('Please_check_your_email_for_confirmation_link'),
                'email': email,
                'captcha': new_captcha_dict
            }
        }

    def forgot_password(self):
        new_captcha_dict = self.captcha.create() if self.captcha else {}
        return {
            'template': 'register.html',
            'context': {
                'reference_data': self.ce.reference_data,
                'action': 'forgot_password',
                'captcha': new_captcha_dict
            }
        }

    def change_password(self, password, password2):
        email = session.get('email')
        if email is None:
            return {
                'template': 'competitionLogin.html',
                'context': {
                    'reference_data': self.ce.reference_data,
                    'error': 'Please login first'
                }
            }

        email = email.lower()
        if not email or not password or not password2 or password != password2 or len(password) < 6:
            return {
                'template': 'change_password.html',
                'context': {
                    'reference_data': self.ce.reference_data,
                    'error': self._get_translation('Invalid_parameters_passwords_do_not_match_or_password_too_short'),
                    'email': email
                }
            }

        user = self.ce.get_user_by_email(email)
        if user is None:
            new_captcha_dict = self.captcha.create() if self.captcha else {}
            return {
                'template': 'register.html',
                'context': {
                    'reference_data': self.ce.reference_data,
                    'error': None,
                    'captcha': new_captcha_dict
                }
            }

        hashed = self.bcrypt.generate_password_hash(password).decode('utf-8')
        self.ce.user_authenticated(email, hashed)
        return {
            'template': 'competitionLogin.html',
            'context': {
                'reference_data': self.ce.reference_data,
                'error': self._get_translation('Please_login_again_with_your_new_password'),
                'email': email
            }
        }

    def confirm_email(self, type, token):
        email = self._confirm_token(token)
        if email is False:
            new_captcha_dict = self.captcha.create() if self.captcha else {}
            logging.info('Invalid or expired token')
            return {
                'template': 'register.html',
                'context': {
                    'reference_data': self.ce.reference_data,
                    'error': 'Invalid or expired token. ',
                    'captcha': new_captcha_dict
                }
            }

        user = self.ce.get_user_by_email(email)
        if user is not None and user.get('is_confirmed') is True and type == 'register':
            logging.info('user already confirmed (register flow) %s', email)
            return {
                'template': 'competitionLogin.html',
                'context': {
                    'reference_data': self.ce.reference_data,
                    'error': 'User already confirmed. Please login. '
                }
            }

        user = self.ce.confirm_user(email)
        session['username'] = user.get('email')
        session['email'] = user.get('email')
        session['access_token'] = token
        return {
            'template': 'change_password.html',
            'context': {
                'reference_data': self.ce.reference_data,
                'error': None
            }
        }

    # ---------------------- Shared (API + Server) ----------------------
    def login_with_password(self, email: str | None, password: str | None, apply_session: bool = True):
        """Authenticate user by email/password.

        Returns a dict not tied to templates so API and server can both use it.
        Structure:
          success: bool
          error / error_key when failed
          user (limited public fields) when success
        """
        if not email or not password:
            return {
                'success': False,
                'error_key': 'User_does_not_exist_or_wrong_password',
                'error': self._get_translation('User_does_not_exist_or_wrong_password')
            }
        email_l = email.lower()
        user = self.ce.get_user_by_email(email_l)
        if user is None:
            return {
                'success': False,
                'error_key': 'User_does_not_exist_or_wrong_password',
                'error': self._get_translation('User_does_not_exist_or_wrong_password')
            }
        if user.get('password') is None:
            return {
                'success': False,
                'error_key': 'You_must_set_your_password',
                'error': self._get_translation('You_must_set_your_password')
            }
        if user.get('is_confirmed') is not None and user.get('is_confirmed') is False:
            return {
                'success': False,
                'error_key': 'User_not_confirmed_Please_check_your_email_for_confirmation_link',
                'error': self._get_translation('User_not_confirmed_Please_check_your_email_for_confirmation_link')
            }
        if user.get('fpictureurl') is not None or user.get('gpictureurl') is not None:
            return {
                'success': False,
                'error_key': 'User_is_registered_with_Google_or_Facebook_Please_click_the_appropriate_button_to_login',
                'error': self._get_translation('User_is_registered_with_Google_or_Facebook_Please_click_the_appropriate_button_to_login')
            }
        if not self.bcrypt.check_password_hash(user.get('password'), password):
            return {
                'success': False,
                'error_key': 'User_does_not_exist_or_wrong_password',
                'error': self._get_translation('User_does_not_exist_or_wrong_password')
            }

        # success
        expires_at = int(datetime.datetime.now().timestamp()+int(1000*60*60*24))
        if apply_session:
            session['username'] = user.get('email')
            session['email'] = user.get('email')
            session['picture'] = '/public/images/favicon.png'
            session['expires_at'] = expires_at
            session['authsource'] = 'self'
            if self.ce.is_god(user):
                session['godmode'] = True
        public_user = {
            'email': user.get('email'),
            'firstname': user.get('firstname'),
            'lastname': user.get('lastname'),
            'club': user.get('club'),
            'godmode': bool(user.get('permissions', {}).get('godmode') or user.get('godmode') or session.get('godmode'))
        }
        return {
            'success': True,
            'user': public_user,
            'expires_at': expires_at
        }
