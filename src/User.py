class User:
    def __init__(self, email, role, isgod, id, fullname, nick, sex, club, category, firstname, lastname, permissions, name, gymid):
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
            gymid=data.get('gymid', '')
        )

    def __str__(self):
        return self.fid+" "+self.fname + " " + self.email + " " + self.fpictureurl + " " + self.role + " " + self.isgod + " " + self.id + " " + self.fullname + " " + self.nick + " "
    

    # returns base empty permissions dictionary
    # who can create new competition? gym admins?
    # if this is the first user who logs in then this user becomes the godmode user
    @staticmethod
    def generate_permissions():
        return {
            "godmode": False,
            "general": [], # crud_competition crud_gym
            "users":[''],
            "competitions":['abc','def'], # everyone has ability to modify these test competitions
            "gyms":[] # contains gym ids
        }
    
    
    def get_permissions(self, type=None):
        return self.permissions.get(type, [])
    
    def get_home_gym(self):
        if not self.gymid:
            return None
        return self.gymid