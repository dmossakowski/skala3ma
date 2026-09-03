import os
from datetime import datetime
from typing import Dict, List, Optional, Any


class User:
    """
    Represents a user in the system. Supports both standard users and supervised (dependent) accounts.
    
    Account Types:
    - 'standard': Full user with email and permissions
    - 'supervised': Dependent account linked to a guardian via guardian_id (email should be empty)
    """
    
    def __init__(self, 
                 email: str,
                 role: str,
                 isgod: bool,
                 id: str,
                 fullname: str,
                 nick: str,
                 sex: str,
                 club: str,
                 category: str,
                 firstname: str,
                 lastname: str,
                 permissions: Dict,
                 name: str,
                 gymid: str,
                 fpictureurl: str = '',
                 gpictureurl: str = '',
                 account_type: str = 'standard',
                 guardian_id: Optional[str] = None,
                 dob: Optional[str] = None,
                 is_confirmed: bool = False,
                 auth_provider: str = '',
                 google_sub: str = '',
                 fid: str = '',
                 password: Optional[str] = None,
                 added_at: Optional[str] = None,
                 updated_at: Optional[str] = None):
        
        # Profile fields
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.fullname = fullname
        self.sex = sex
        self.club = club
        self.category = category
        self.dob = dob
        self.name = name
        self.nick = nick
        
        # Account fields
        self.id = id
        self.gymid = gymid
        self.account_type = account_type  # 'standard' or 'supervised'
        self.guardian_id = guardian_id    # user id of the guardian (for supervised accounts only)
        
        # Authentication fields
        self.is_confirmed = is_confirmed
        self.auth_provider = auth_provider  # 'email', 'google', etc.
        self.google_sub = google_sub
        self.fid = fid
        self.password = password
        
        # Picture URLs
        self.fpictureurl = fpictureurl  # First-party / custom profile picture
        self.gpictureurl = gpictureurl  # Google / external picture
        
        # Permissions
        self.permissions = permissions if permissions else self._default_permissions()
        
        # System/legacy fields
        self.role = role
        self.isgod = isgod
        
        # Timestamps
        self.added_at = added_at
        self.updated_at = updated_at

    @staticmethod
    def _default_permissions() -> Dict:
        """Returns default empty permissions dictionary."""
        return {
            "general": [],
            "users": [],
            "competitions": [],
            "gyms": []
        }



    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create a User instance from a dictionary."""
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
            permissions=data.get('permissions', cls._default_permissions()),
            name=data.get('name', ''),
            gymid=data.get('gymid', ''),
            fpictureurl=data.get('fpictureurl', ''),
            gpictureurl=data.get('gpictureurl', ''),
            account_type=data.get('account_type', 'standard'),
            guardian_id=data.get('guardian_id', None),
            dob=data.get('dob', None),
            is_confirmed=data.get('is_confirmed', False),
            auth_provider=data.get('auth_provider', ''),
            google_sub=data.get('google_sub', ''),
            fid=data.get('fid', ''),
            password=data.get('password'),
            added_at=data.get('added_at', None),
            updated_at=data.get('updated_at', None)
        )

    def __str__(self) -> str:
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
    
    def validate(self) -> None:
        """
        Validate user data consistency.
        
        Raises:
            ValueError: If validation fails
        """
        # Standard users must have email
        if self.account_type == 'standard' and not self.email:
            raise ValueError("Standard user accounts must have a valid email address")
        
        # Supervised users must NOT have email
        if self.account_type == 'supervised' and self.email:
            raise ValueError("Supervised accounts must have empty email field")
        
        # Supervised users must have guardian_id
        if self.account_type == 'supervised' and not self.guardian_id:
            raise ValueError("Supervised accounts must have a guardian_id")
        
        # Standard users must NOT have guardian_id
        if self.account_type == 'standard' and self.guardian_id:
            raise ValueError("Standard accounts must not have a guardian_id")
    
    def is_dependent(self) -> bool:
        """Check if this user is a dependent (supervised) account."""
        return self.account_type == 'supervised'
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Serialize user to a dictionary suitable for application and API use.

        Password hashes are excluded by default. Use to_storage_dict() only at
        the database persistence boundary.
        """
        data = {
            'id': self.id,
            'email': self.email,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'fullname': self.fullname,
            'name': self.name if self.name else self.fullname,  # Normalize name field
            'sex': self.sex,
            'club': self.club,
            'category': self.category,
            'dob': self.dob,
            'nick': self.nick,
            'gymid': self.gymid,
            'account_type': self.account_type,
            'guardian_id': self.guardian_id,
            'is_confirmed': self.is_confirmed,
            'auth_provider': self.auth_provider,
            'google_sub': self.google_sub,
            'fid': self.fid,
            'fpictureurl': self.fpictureurl,
            'gpictureurl': self.gpictureurl,
            'permissions': self.permissions,
            'role': self.role,
            'isgod': self.isgod,
            'added_at': self.added_at,
            'updated_at': self.updated_at,
        }
        if include_sensitive:
            data['password'] = self.password
        return data

    def to_storage_dict(self) -> Dict[str, Any]:
        """Serialize all persisted fields, including the password hash."""
        return self.to_dict(include_sensitive=True)
    
    def to_minimal_dict(self) -> Dict[str, Any]:
        """
        Serialize user to a minimal dictionary (public-safe, for external APIs).
        Excludes sensitive fields like email, isgod, role.
        For dependents, excludes email by design (they have empty email anyway).
        """
        return {
            'id': self.id,
            'email': self.email if self.account_type == 'standard' else '',  # Empty for dependents
            'firstname': self.firstname,
            'lastname': self.lastname,
            'fullname': self.fullname,
            'name': self.name if self.name else self.fullname,
            'sex': self.sex,
            'category': self.category,
            'nick': self.nick,
            'dob': self.dob,
        }
    
    def to_gym_admin_dict(self) -> Dict[str, Any]:
        """
        Serialize user for gym admin view (excludes email, isgod).
        Used by endpoints like GET /gyms/<id>/users
        """
        data = self.to_minimal_dict()
        data.pop('email', None)  # Remove email for gym admin view
        return data
    
    def get_picture_url(self) -> str:
        """
        Return a picture URL for this user.
        
        Preference order:
          1) gpictureurl (Google / external picture)
          2) fpictureurl (first party / custom profile picture)
          3) fallback default icon
        """
        if self.gpictureurl:
            return self.gpictureurl
        if self.fpictureurl:
            return self.fpictureurl
        return '/public/images/favicon.png'
    

    # returns base empty permissions dictionary
    # who can create new competition? gym admins?
    @staticmethod
    def generate_permissions() -> Dict[str, List]:
        """Returns base empty permissions dictionary structure."""
        return {
            "general": [],
            "users": [],
            "competitions": [],
            "gyms": []
        }
    
    @staticmethod
    def is_admin(user: Any) -> bool:
        """
        Check if a user has admin privileges based on ADMIN_USERS environment variable.
        
        Args:
            user: User object or User dictionary with 'email' field
            
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
    
    def is_admin_instance(self) -> bool:
        """Instance method: Check if this user is an admin."""
        return self.is_admin(self)
    
    def get_permissions(self, perm_type: Optional[str] = None) -> List | Dict:
        """
        Get permissions of a specific type, or all permissions.
        
        Args:
            perm_type: Type of permissions to retrieve (e.g., 'competitions', 'gyms', 'general', 'users')
                      If None, returns all permissions.
        
        Returns:
            List of permission IDs for the type, or full permissions dict if type is None
        """
        if perm_type is None:
            return self.permissions
        return self.permissions.get(perm_type, [])
    
    def get_general_permissions(self) -> Dict[str, List]:
        """Get only general permissions."""
        return {"general": self.permissions.get("general", [])}
    
    def get_home_gym(self) -> Optional[str]:
        """Get the user's home gym ID, if set."""
        if not self.gymid:
            return None
        return self.gymid
    
    # Backward compatibility alias for old camelCase method name
    def getPictureUrl(self) -> str:
        """Deprecated: Use get_picture_url() instead."""
        return self.get_picture_url()
    
    # ========================================================================
    # Dict-like access for backward compatibility with code expecting dicts
    # ========================================================================
    
    def __getitem__(self, key):
        """Allow dict-style access: user['id'], user['email'], etc."""
        return getattr(self, key, None)
    
    def __setitem__(self, key, value):
        """Allow dict-style assignment: user['id'] = value."""
        setattr(self, key, value)
    
    def get(self, key, default=None):
        """Dict-style get with default: user.get('email', '')."""
        return getattr(self, key, default)
    
    def __contains__(self, key):
        """Allow 'in' operator: if 'email' in user:"""
        return hasattr(self, key) and getattr(self, key) is not None
    
    def update(self, other):
        """Update multiple fields from a dict."""
        if isinstance(other, dict):
            for key, value in other.items():
                setattr(self, key, value)
        elif isinstance(other, User):
            for key, value in other.to_dict().items():
                setattr(self, key, value)


class CompetitionClimber(User):
    """
    Represents a climber registered in a specific competition.
    Extends User with competition-specific fields (score, rank, routes, etc.).
    """
    
    def __init__(self,
                 user: User,
                 score: int = 0,
                 rank: Optional[int] = None,
                 routes_climbed: Optional[List[str]] = None,
                 present: bool = False,
                 registration_timestamp: Optional[str] = None):
        """
        Create a CompetitionClimber from a User object.
        
        Args:
            user: The User object to base this climber on
            score: Climber's score in the competition
            rank: Climber's rank in the competition
            routes_climbed: List of route IDs the climber has climbed
            present: Whether the climber is present at the competition
            registration_timestamp: When the climber registered for this competition
        """
        # Copy all User fields
        super().__init__(
            email=user.email,
            role=user.role,
            isgod=user.isgod,
            id=user.id,
            fullname=user.fullname,
            nick=user.nick,
            sex=user.sex,
            club=user.club,
            category=user.category,
            firstname=user.firstname,
            lastname=user.lastname,
            permissions=user.permissions,
            name=user.name,
            gymid=user.gymid,
            fpictureurl=user.fpictureurl,
            gpictureurl=user.gpictureurl,
            account_type=user.account_type,
            guardian_id=user.guardian_id,
            dob=user.dob,
            is_confirmed=user.is_confirmed,
            auth_provider=user.auth_provider,
            google_sub=user.google_sub,
            fid=user.fid,
            added_at=user.added_at,
            updated_at=user.updated_at
        )
        
        # Competition-specific fields
        self.score = score
        self.rank = rank
        self.routes_climbed = routes_climbed if routes_climbed is not None else []
        self.present = present
        self.registration_timestamp = registration_timestamp
    
    def to_competition_dict(self) -> Dict[str, Any]:
        """
        Serialize competition climber to a dictionary for storage in competition JSON.
        Includes score, rank, routes, and presence data.
        """
        return {
            'id': self.id,
            'email': self.email,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'fullname': self.fullname,
            'name': self.name if self.name else self.fullname,
            'sex': self.sex,
            'category': self.category,
            'score': self.score,
            'rank': self.rank,
            'routesClimbed': self.routes_climbed,  # Note: using camelCase for JSON compatibility
            'present': self.present,
            'registration_timestamp': self.registration_timestamp,
        }
    
    @classmethod
    def copy_from_user(cls, user: User, 
                      registration_timestamp: Optional[str] = None) -> 'CompetitionClimber':
        """
        Create a CompetitionClimber from a User with default competition values.
        
        Args:
            user: The User object
            registration_timestamp: When the registration occurred (defaults to now)
        
        Returns:
            CompetitionClimber with default values
        """
        if registration_timestamp is None:
            registration_timestamp = datetime.utcnow().isoformat()
        
        return cls(
            user=user,
            score=0,
            rank=None,
            routes_climbed=[],
            present=False,
            registration_timestamp=registration_timestamp
        )


# ============================================================================
# Factory Functions and Adapters for Database/API Integration
# ============================================================================

def dict_to_user(data: Dict[str, Any]) -> User:
    """
    Create a User from a dictionary (factory function).
    Wrapper around User.from_dict() for explicit API clarity.
    
    Args:
        data: Dictionary with user fields
        
    Returns:
        User instance
    """
    return User.from_dict(data)


def users_from_db_row(id_val: str, email: str, jsondata: str, added_at: str) -> User:
    """
    Parse a database row from the climbers table into a User object.
    
    Args:
        id_val: User ID (UUID)
        email: Email address
        jsondata: JSON string containing all user data
        added_at: Timestamp string when user was added
        
    Returns:
        User instance
        
    Raises:
        ValueError: If JSON parsing fails
    """
    import json
    try:
        data = json.loads(jsondata)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse user JSON data for user {id_val}: {e}")
    
    # Ensure core fields are set
    data['id'] = id_val
    data['email'] = email
    data['added_at'] = added_at
    
    # Set updated_at if not present
    if 'updated_at' not in data:
        data['updated_at'] = added_at
    
    return User.from_dict(data)


def dependent_from_db_row(id_val: str, jsondata: str, added_at: str) -> User:
    """
    Parse a database row for a dependent (supervised account) into a User object.
    Dependent results don't include email field in the query result.
    
    Args:
        id_val: User ID (UUID)
        jsondata: JSON string containing all user data
        added_at: Timestamp string when user was added
        
    Returns:
        User instance with account_type='supervised' and email=''
        
    Raises:
        ValueError: If JSON parsing fails or user is not a dependent
    """
    import json
    try:
        data = json.loads(jsondata)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse dependent JSON data for user {id_val}: {e}")
    
    # Ensure core fields are set
    data['id'] = id_val
    data['email'] = ''  # Dependents always have empty email
    data['added_at'] = added_at
    data['account_type'] = 'supervised'
    
    # Set updated_at if not present
    if 'updated_at' not in data:
        data['updated_at'] = added_at
    
    user = User.from_dict(data)
    
    # Validate that this is actually a dependent
    if not user.is_dependent():
        raise ValueError(f"User {id_val} is not a dependent account (missing guardian_id or wrong account_type)")
    
    return user

    