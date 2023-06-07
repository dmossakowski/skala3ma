import random

import numpy as np

def calculate_points(climbed_routes, weight_routes=1, weight_grades=1):
    grades = ['1', '2', '3', '4a', '4b', '4c', '5a', '5b', '5c', '6a', '6a+', '6b', '6b+', '6c', '6c+', '7a', '7a+', '7b', '7b+', '7c', '7c+', '8a', '8a+', '8b', '8b+', '8c', '8c+', '9a', '9a+', '9b', '9b+', '9c']
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
    climbed_routes = random.choices(['1', '2', '3', '4a', '4b', '4c', '5a', '5b', '5c', '6a', '6a+', '6b', '6b+', '6c', '6c+', '7a', '7a+', '7b', '7b+', '7c', '7c+', '8a', '8a+', '8b', '8b+', '8c', '8c+', '9a', '9a+', '9b', '9b+', '9c'], k=num_routes)
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
