import numpy as np
import scipy.stats


class Person:
    def __init__(self, ide, icp, ifp):
        self.identity = ide
        self.incuPeriod = icp
        self.infePeriod = ifp
        self.infectionDay = None
        self.quarantine = 0
        self.infectCount = 0
        self.friends = []
        self.classmates = []
        self.isGrad = -1
        self.dept = -1

    def reset(self, ide, icp, ifp):
        self.identity = ide
        self.incuPeriod = icp
        self.infePeriod = ifp
        self.infectionDay = None
        self.quarantine = 0
        self.infectCount = 0
        self.friends = []  # random
        # do not change classmates, grad, or dept as this is deterministic

# A course of people
class Course:
    def __init__(self):
        self.duration = 0
        self.students = []
        self.days = []
        self.iCount = 0  # number of infected individuals ATTENDING a course (not counting quarantined)
        self.tempCount = 0

    def randomInfectedStudent(self):
        temp = []
        for i in self.students:
            if i.quarantine == 0 and i.identity == 'I':
                temp.append(i)
        if len(temp) > 0:
            np.random.choice(temp).infectCount += 1