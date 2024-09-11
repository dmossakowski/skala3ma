
import json



class CalculationStrategy:

    # these results represent the categories in the competition
    # there are three categories for women and three for men
    # this should be improved to be more dynamic
    emptyResults = {"M":{ "0":[], "1":[], "2":[]}, "F":{"0":[], "1":[], "2":[] }}


    calc_type_fsgt0 = 0
    calc_type_fsgt1 = 1

    def recalculate(self, competition):
        raise NotImplementedError("Subclasses should implement this!")


        