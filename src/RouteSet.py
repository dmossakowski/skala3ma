import uuid
import random
from typing import List, Dict, Any
from .Route import Route

class RouteSet:
    def __init__(self):
        self.routes = {}
        self.routes['id'] = str(uuid.uuid4().hex)
        self.routes['name'] = "Default"

    def generate_dummy_routes(self, num_routes: int) -> Dict[str, Any]:
        """Generate dummy routes using the Route dataclass.

        Returns the internal structure preserving legacy shape: {'id':..., 'name':..., 'routes':[dict,...]}
        """
        routes_list: List[Route] = []
        colors = ['#53be6b', '#FF4500','#558afe','#a07821','#efdd41','#d33f2a','#333333']
        grades = ['4a', '4b', '4c', '5a', '5b', '5c', '6a', '6b', '6c', '7a', '7b', '7c', '8a', '8b', '8c']
        modifiers = ['solid', 'marble']
        for i in range(1, num_routes + 1):
            line = (i - 1) // 3 + 1
            r = Route.create_dummy(
                index=i,
                line=line,
                color=random.choice(colors),
                grade=random.choice(grades),
                modifier=random.choice(modifiers)
            )
            routes_list.append(r)
        # Store dict representations for compatibility elsewhere
        self.routes['routes'] = [r.as_dict() for r in routes_list]
        return self.routes


    def get_routes(self) -> Dict[str, Any]:
        return self.routes

    def get_id(self):
        return self.routes['id']

# Example usage
if __name__ == "__main__":
    route_set = RouteSet()
    data = route_set.generate_dummy_routes(5)
    for route_dict in data['routes']:
        print(route_dict)