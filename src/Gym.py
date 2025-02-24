import logging

class Gym:
    def __init__(self, gymid, routesid, name, added_by, logo_img_id, homepage, address, organization, routesA):
        self.gymjson = {
            'id': gymid,
            'routesid': routesid,
            'name': name,
            'logo_img_id': logo_img_id,
            'homepage': homepage,
            'address': address,
            'organization': organization,
            'added_by': added_by,
            'routes': routesA,
            'status': 0
        }
    
    @classmethod
    def from_basic_info(cls, name, logo_img_id, homepage, address):
        return cls(
            gymid=None,
            routesid=None,
            name=name,
            added_by=None,
            logo_img_id=logo_img_id,
            homepage=homepage,
            address=address,
            organization=None,
            routesA=[]
        )

    def get_gym_json(self):
        return self.gymjson

    def update_gym_coordinates(self, lat, lon):
        # Ensure that lat and lon are valid numbers
        if lat is None or lon is None:
            return self.gymjson
        
        # Test lat and lon to be valid numbers 
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            logging.info('lat or lon are not valid numbers lat=' + str(lat) + ' lon=' + str(lon))
            return self.gymjson

        self.gymjson['lat'] = lat
        self.gymjson['lon'] = lon
        return self.gymjson

    def update_gym_status(self, status):
        if status is None:
            return self.gymjson
        self.gymjson['status'] = status
        return self.gymjson
    

    def set_ref_id(self, ref_id):
        self.gymjson['ref_id'] = ref_id


# Example usage
if __name__ == "__main__":
    gym = Gym(
        gymid="gym1",
        routesid="route1",
        name="Example Gym",
        added_by="admin",
        logo_img_id="logo1",
        homepage="http://example.com",
        address="123 Example St",
        organization="Example Org",
        routesA=["route1", "route2"]
    )

    print(gym.get_gym_json())
    gym.update_gym_coordinates(40.7128, -74.0060)
    print(gym.get_gym_json())
    gym.update_gym_status("open")
    print(gym.get_gym_json())