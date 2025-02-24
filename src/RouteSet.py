import uuid

class RouteSet:
    def __init__(self):
        self.routes = {}
        self.routes['id'] = str(uuid.uuid4().hex)
        self.routes['name'] = "Default"

    def generate_dummy_routes(self, num_routes):
        routesA = []
        
        for i in range(1, num_routes + 1):
            line = (i - 1) // 3 + 1 
            route = {
                'id': str(uuid.uuid4().hex),
                'routenum': str(i),
                'line': str(line),
                'colorfr': 'Vert',
                'color1': '#2E8B57',
                'color2': '',
                'grade': '5b',
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