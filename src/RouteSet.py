import uuid
import random

class RouteSet:
    def __init__(self):
        self.routes = {}
        self.routes['id'] = str(uuid.uuid4().hex)
        self.routes['name'] = "Default"

    def generate_dummy_routes(self, num_routes):
        routesA = []

        colors = ['#53be6b', '#FF4500','#558afe','#a07821','#efdd41','#d33f2a','#333333']
        grades = ['4a', '4b', '4c', '5a', '5b', '5c', '6a', '6b', '6c', '7a', '7b', '7c', '8a', '8b', '8c']
        color_modifier = ['solid', 'marble']
        
        for i in range(1, num_routes + 1):
            line = (i - 1) // 3 + 1 
            route = {
                'id': str(uuid.uuid4().hex),
                'routenum': str(i),
                'line': str(line),
                'colorfr': 'Vert',
                'color1': random.choice(colors),
                'color2': '',
                'grade': random.choice(grades),
                'color_modifier': random.choice(color_modifier),
                'name': 'Route '+str(i),
                'openedby': '',
                'opendate': '',
                'notes': ''
            }
            routesA.append(route)
        self.routes['routes'] = routesA
        
        return self.routes


    def get_routes(self):
        return self.routes

    def get_id(self):
        return self.routes['id']

# Example usage
if __name__ == "__main__":
    route_set = RouteSet()
    route_set.generate_dummy_routes(5)
    
    for route in route_set.get_routes():
        print(route)