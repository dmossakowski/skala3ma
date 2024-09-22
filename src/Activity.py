

class Activity:
    def __init__(self, activity_id, name, mur, start, end):
        self.activity_id = activity_id
        self.name = name
        self.mur = mur
        self.start = start
        self.end = end
        
    def __str__(self):
        return self.activity_id+" "+self.name + " " + self.mur + " " + self.start + " " + self.end

    def to_json():
        activity = {"gym_id": gym_id, "routes_id": routes_id, "description": description, "routes": []}
    
        activity['id'] = self.activity_id
        activity['user_id'] = user_id
        activity['date'] = date
    

        
        
