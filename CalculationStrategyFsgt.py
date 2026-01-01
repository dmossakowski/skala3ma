# CalculationStrategyFsgt0.py

from datetime import datetime, date, timedelta
import json
import copy
from CalculationStrategy import CalculationStrategy


class CalculationStrategyFsgt0(CalculationStrategy):

    def recalculate(self, comp):    
        comp['results'] = copy.deepcopy(CalculationStrategy.emptyResults)
        for climberId in comp['climbers']:
            comp = self._calculatePointsPerClimber(climberId, comp)

        #rank climbers
        for climberId in comp['climbers']:
            try:
                climbersex = comp['climbers'][climberId]['sex']
                climbercat = str(comp['climbers'][climberId]['category'])

                comp['climbers'][climberId]['rank'] = comp['results'][climbersex][climbercat].index(comp['climbers'][climberId]['score'])+1
            except ValueError:
                comp['climbers'][climberId]['rank'] = -1

        results = comp['results']
        for sex in results:
            for cat in results[sex]:
                pointsA = results[sex][cat]
                if len(pointsA) == 0:
                    continue
                #pointsA.sort()
                #pointsA = results[sex][cat].sort()
                #results[sex][cat] = pointsA.sort()
        
        
        return comp

        
            
    # for a climber it takes routes climbed array, regenerates points for route repeats
    #
    def _calculatePointsPerClimber(self, climberId, comp):
        routesClimbed = comp['climbers'][climberId]['routesClimbed']
        pointsEarned = []
        sex = comp['climbers'][climberId]['sex']

        if sex == "M":
            routeRepeats = self._getRouteRepeats("M", comp)
        elif sex == "F":
            routeRepeats = self._getRouteRepeats("F", comp)
        else:
            #logging.error(f"Invalid sex value found during calculation of points per climber: {sex}")  
            return None
        points = 0

        # route climbed is an index into routeRepeats points calculated earlier
        for i, v in enumerate(routesClimbed):
            points += routeRepeats[v]
            pointsEarned.append(routeRepeats[v])
            #logging.info(str(climberId) + " route="+str(v) + " - route points=" + str(routeRepeats[v]) + " total points=" + str(points))

        comp['climbers'][climberId]['points_earned'] = pointsEarned
        points = round(points)
        comp['climbers'][climberId]['score'] = points
        climbersex = comp['climbers'][climberId]['sex']
        climbercat = str(comp['climbers'][climberId]['category'])
        pointsA = comp['results'][climbersex][climbercat]
        pointsA.append(points)
        pointsA.sort(reverse=True)
        comp['climbers'][climberId]['rank'] = pointsA.index(points)
        #(comp['results'][climbersex][climbercat]).append(points)

        #logging.info("results " + str(climbersex)+str(climbercat)+ " add "+str(points))
        return comp



            
    # calculates points per route per sex
    # first loop counts how many times the route was climbed
    # second loop iterates over this same list but then does 1000/times the route was climbed
    # limited to 200 routes returned in an array
    def _getRouteRepeats(self, sex, comp):
        pointsPerRoute = [0 for i in range(200)]
        for climber in comp['climbers']:
            if comp['climbers'][climber]['sex'] != sex:
                continue
            #print(climber)
            routesClimbed = comp['climbers'][climber]['routesClimbed']
            #print(comp['climbers'][climber]['sex'])
            #print(routesClimbed)
            for r in routesClimbed:
                pointsPerRoute[r]=pointsPerRoute[r]+1

        #logging.info("route repeats: ")
        #logging.info(pointsPerRoute)

        for i, r in enumerate(pointsPerRoute):
            if r == 0 :
                pointsPerRoute[i]=1000
            else:
                pointsPerRoute[i]=1000/r
        #logging.info("points per route: ")
        #logging.info(pointsPerRoute)

        return pointsPerRoute




class CalculationStrategyFsgt1(CalculationStrategyFsgt0):
    def _getRouteRepeats(self, sex, comp):
        pointsPerRoute = [0 for i in range(200)]
        for climber in comp['climbers']:
            #print(climber)
            routesClimbed = comp['climbers'][climber]['routesClimbed']
            #print(comp['climbers'][climber]['sex'])
            #print(routesClimbed)
            for r in routesClimbed:
                pointsPerRoute[r]=pointsPerRoute[r]+1

        #logging.info("route repeats: ")
        #logging.info(pointsPerRoute)

        for i, r in enumerate(pointsPerRoute):
            if r == 0 :
                pointsPerRoute[i]=1000
            else:
                pointsPerRoute[i]=1000/r
        #logging.info("points per route: ")
        #logging.info(pointsPerRoute)

        return pointsPerRoute

    # End class CalculationStrategyFsgt1

    
class CalculationStrategyFsgt2(CalculationStrategyFsgt1):
    # Override age categories: 18-39 -> 0, 40-49 -> 1, 50+ -> 2
    def get_category_from_dob(dob):
        if dob is None:
            return -1
        dob_dt = datetime.strptime(dob, "%Y-%m-%d")
        today = datetime.today()
        age = today.year - dob_dt.year - ((today.month, today.day) < (dob_dt.month, dob_dt.day))

        if 18 <= age <= 39:
            return 0
        elif 40 <= age <= 49:
            return 1
        elif age >= 50:
            return 2
        elif 12 <= age <= 13:
            return 0
        elif 14 <= age <= 15:
            return 1
        elif 16 <= age <= 17:
            return 2
        else:
            return -1

# Register strategies with human-readable labels
CalculationStrategy.register('fsgt0', CalculationStrategyFsgt0, label='FSGT: sex-separated route repeats')
CalculationStrategy.register('fsgt1', CalculationStrategyFsgt1, label='FSGT: all climbers combined route repeats')
CalculationStrategy.register('fsgt2', CalculationStrategyFsgt2, label='FSGT2: age 18–39 / 40–49 / 50+')

