import os

class User:
    def __init__(self, email, role, isgod, id, fullname, nick, sex, club, category, firstname, lastname, permissions, name, gymid,
                 fpictureurl='', gpictureurl='', account_type='standard', guardian_id=None, dob=None):
        self.email = email
        self.role = role
        self.isgod = isgod
        self.id = id
        self.fullname = fullname
        self.nick = nick
        self.sex = sex
        self.club = club
        self.category = category
        self.firstname = firstname
        self.lastname = lastname
        self.permissions = permissions
        self.name = name
        self.gymid = gymid
        self.fpictureurl = fpictureurl
        self.gpictureurl = gpictureurl
        self.account_type = account_type  # 'standard' or 'supervised'
        self.guardian_id = guardian_id     # user id of the guardian (for supervised accounts)
        self.dob = dob



    @classmethod
    def from_dict(cls, data):
        return cls(
            email=data.get('email', ''),
            role=data.get('role', ''),
            isgod=data.get('isgod', False),
            id=data.get('id', ''),
            fullname=data.get('fullname', ''),
            nick=data.get('nick', ''),
            sex=data.get('sex', ''),
            club=data.get('club', ''),
            category=data.get('category', ''),
            firstname=data.get('firstname', ''),
            lastname=data.get('lastname', ''),
            permissions=data.get('permissions', {}),
            name=data.get('name', ''),
            gymid=data.get('gymid', ''),
            fpictureurl=data.get('fpictureurl', ''),
            gpictureurl=data.get('gpictureurl', ''),
            account_type=data.get('account_type', 'standard'),
            guardian_id=data.get('guardian_id', None),
            dob=data.get('dob', None)
        )

    def __str__(self):
        return " ".join(str(x) for x in [
            self.id,
            self.name,
            self.email,
            self.fpictureurl,
            self.gpictureurl,
            self.role,
            self.isgod,
            self.fullname,
            self.nick,
        ])
    

    # returns base empty permissions dictionary
    # who can create new competition? gym admins?
    @staticmethod
    def generate_permissions():
        return {
            "general": [], # crud_competition crud_gym
            "users":[''],
            "competitions":['abc','def'], # everyone has ability to modify these test competitions
            "gyms":[] # contains gym ids
        }
    
    @staticmethod
    def is_admin(user):
        """
        Check if a user has admin privileges based on ADMIN_USERS environment variable.
        
        Args:
            user: User dictionary or User object with 'email' field
            
        Returns:
            bool: True if user is an admin, False otherwise
        """
        if user is None:
            return False
        
        # Get email from dict or object
        email = user.get('email') if isinstance(user, dict) else getattr(user, 'email', None)
        
        if email is None:
            return False
        
        # Load admin users from environment variable
        admin_users = os.getenv('ADMIN_USERS', '').split(',')
        admin_users = [e.strip() for e in admin_users if e.strip()]
        
        return email in admin_users
    
    
    def get_permissions(self, type=None):
        return self.permissions.get(type, [])
    

    def get_general_permissions(self):
        return {"general": self.permissions.get("general", [])}

    def getPictureUrl(self):
        """Return a picture URL for this user.

        Preference order:
          1) fpictureurl (first party / custom profile picture)
          2) gpictureurl (Google / external picture)
          3) fallback default icon
        """
        if getattr(self, 'gpictureurl', None):
            return self.gpictureurl
        if getattr(self, 'fpictureurl', None):
            return self.fpictureurl
        return '/public/images/favicon.png'

    def get_home_gym(self):
        if not self.gymid:
            return None
        return self.gymid
    

    