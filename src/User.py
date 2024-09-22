class User:
    def __init__(self, email, role, isgod, id, fullname, nick, sex, club, category, firstname, lastname, permissions, name, gymid):
        self.fid = fid
        self.fname = fname
        self.email = email
        self.fpictureurl = fpictureurl
        self.role = role
        self.isgod = isgod
        self.id = id
        self.fullname = fullname
        self.nick = nick
        self.sex = sex
        self.club = club
        self.category = category
        self.gname = gname
        self.gpictureurl = gpictureurl
        self.firstname = firstname
        self.lastname = lastname
        self.permissions = permissions
        self.name = name
        self.gymid = gymid


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
    
    