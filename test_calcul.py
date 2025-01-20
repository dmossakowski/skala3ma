import random
import re

def calculate_points(climbed_routes, weight_routes=1, weight_grades=1):
    grades = ['?','1', '2', '3', '4a', '4b', '4c', '5a', '5b', '5c', '6a', '6a+', '6b', '6b+', '6c', '6c+', '7a', '7a+', '7b', '7b+', '7c', '7c+', '8a', '8a+', '8b', '8b+', '8c', '8c+', '9a', '9a+', '9b', '9b+', '9c']
    mean = grades.index('7a')
    std_dev = 6 # adjust this to change the spread of the normal distribution

    points = np.zeros(len(climbed_routes))
    for i, route in enumerate(climbed_routes):
        grade_index = grades.index(route)
        grade_points = np.exp(-((grade_index - mean) / std_dev) ** 2 / 2)
        points[i] = grade_points

    # adjust for weight of routes and grades
    total_points = weight_routes * len(points) + weight_grades * sum(points)

    return total_points

def tests():
    # define the mean and standard deviation of the climbers' abilities
    mean_ability = 5
    std_dev_ability = 2

    # define the mean and standard deviation of the number of routes climbed
    mean_routes = 20
    std_dev_routes = 5

    # define the weight factors
    weight_routes = 1
    weight_grades = 1

    # define the list of climbed routes for each hypothetical climber
    climbed_routes_list = []
    for i in range(10):
        num_routes = int(random.normalvariate(mean_routes, std_dev_routes))
        climbed_routes = random.choices(['?','1', '2', '3', '4a', '4b', '4c', '5a', '5b', '5c', '6a', '6a+', '6b', '6b+', '6c', '6c+', '7a', '7a+', '7b', '7b+', '7c', '7c+', '8a', '8a+', '8b', '8b+', '8c', '8c+', '9a', '9a+', '9b', '9b+', '9c'], k=num_routes)
        climbed_routes_list.append(climbed_routes)

    # calculate the points earned by each climber
    points_list = []
    for climbed_routes in climbed_routes_list:
        points = calculate_points(climbed_routes, weight_routes=weight_routes, weight_grades=weight_grades)
        points_list.append(points)
        print(climbed_routes)
        print(points)

    # plot a histogram of the points earned by each climber
    #plt.hist(points_list, bins=10)
    #plt.xlabel('Points')
    #plt.ylabel('Number of Climbers')
    #plt.title('Points Earned by Hypothetical Climbers')
    #plt.show()




"""
calculates fairness
"""

base_completion_rate = 0.8

def calculate_fairness_with_difficulty(routes, num_climbers, competition_time, route_climb_time=5, rest_time=2, base_completion_rate=0.8):
    """
    Calculates the fairness of a climbing competition considering route difficulties.

    Args:
        routes: A list of tuples, where each tuple contains a route name and its French difficulty grade (e.g., ('Route 1', '5a')).
        num_climbers: Number of climbers participating.
        competition_time: Total competition time in minutes.
        route_climb_time: Time taken to climb a single route in minutes (default: 5).
        rest_time: Rest time between routes in minutes (default: 2).
        base_completion_rate: Base completion rate for the easiest route (default: 0.8).

    Returns:
        Fairness score (a value between 0 and 1).
    """

    total_climbable_time = competition_time - (len(routes) * rest_time)
    max_climbs_per_climber = max(0, total_climbable_time // route_climb_time)

    # Calculate completion rates based on difficulty (linear slope)
    def get_completion_rate(grade):
        """
        Calculates the estimated completion rate for a given French grade.

        Assumes a linear decrease in completion rate with increasing difficulty.
        """
        # Example: For a range of 4 to 7c, with 4 having 80% completion rate:
        # slope = (0 - base_completion_rate) / (7.5 - 4)  # 7.5 represents 7c+
        slope = -base_completion_rate / (7.5 - 4) 
        intercept = base_completion_rate - (slope * 4)
        # Extract the numeric part from the grade (e.g., '5a' -> 5)
        try:
            grade_num = float(re.findall(r'(\d+)', grade)[0]) 
        except (IndexError, ValueError):
            grade_num = 4  # Default to easiest grade if parsing fails

        return max(0, intercept + (slope * grade_num))

    # Calculate average completion rate across all routes
    avg_completion_rate = sum(get_completion_rate(route[1]) for route in routes) / len(routes)

    # Adjust number of climbs based on average completion rate
    adjusted_climbs_per_climber = max_climbs_per_climber * avg_completion_rate

    # Calculate average climbers per route considering completion rates
    avg_climbers_per_route = num_climbers * avg_completion_rate / len(routes)

    return (adjusted_climbs_per_climber / len(routes)) * (total_climbable_time / competition_time) * avg_climbers_per_route


