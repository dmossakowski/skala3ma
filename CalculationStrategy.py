
import json



class CalculationStrategy:
    emptyResults = {"M":{ "0":[], "1":[], "2":[]}, "F":{"0":[], "1":[], "2":[] }}


    calc_type_fsgt0 = 0
    calc_type_fsgt1 = 1

    def recalculate(self, competition):
        raise NotImplementedError("Subclasses should implement this!")


        