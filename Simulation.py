import matplotlib.pyplot as plt
import numpy as np
import random
import time
from DataStructures2 import Person, Course

"""NETWORK SEIR MODEL DRAFT 1: Updated 7/31/2020"""
# Changes: Moved lots of preprocessing outside of the loop
# Added function to Person class that allows for resetting each iteration

"""MODEL PARAMETERS"""
# Initial Conditions
population = 22051  # simulation population size
initialI = 500  # initial number of infected people
days = 250  # number of time steps to run simulation over

# Simulation Settings
trials = 6  # number of times to run the simulation
falsePos = 0.001
falseNeg = 0.05
quarLength = 20

# Network Parameters
courseCount = 6072  # number of courses
friendDur = 0.125  # base duration of a close friend interaction in days
courseDur = 0.04  # base duration of a course in time steps
deptDur = 0.01  # base duration of a department interaction
gradDur = 0.005  # base duration of a under / grad interaction
networkEdgeList = "Weeden_Cornwell_Full.txt"  # list of edges in network
friendInteract = 4  # average number of friends a person interacts with each day
classInteract = 4  # average number of classmates a person interacts with each day
deptInteract = 4  # average number of department members a person interacts with each day
gradInteract = 4  # average number of under/grad students a person interacts with each day

# Type of Interactions
friendI = False
classI = True
deptI = False
gradI = False

# Infection Parameters
incuMean = 1.621  # mean incubation period for lognormal distribution
incuVar = 0.418  # variance of incubation period for lognormal distribution
infeMean = 10  # mean infectious period of the (currently unknown) distribution
beta = 4  # average number of people infected by infected person per unit time
outsideInfectionRate = 0 / population  # average rate of people who get infected each day from outside



# Centrality-based Testing
# Targeted deterministic rotational testing
cbt = False
centralityData = "CentralityOut.txt"
splitsCBT = 3
groupSizeCBT = int(np.ceil(population / splitsCBT))
testRateArray = [5, 5, 5]

sumA = 0
for i in testRateArray:
    sumA += (1 / i)
numofG = int(np.ceil(len(testRateArray) / sumA))


# Deterministic Rotational Testing
generalTest = True
splitsDRT = numofG  # splits the population into this many groups
testFreq = numofG  # test each person every this many days
groupSizeDRT = int(np.ceil(population / splitsDRT))
testStart = 0


"""MODEL FUNCTIONS"""

# Intervention function that can handle multiple different quarantine, etc. strategies
def intervention(day):
    if day < testStart:
        return 0
    if generalTest:
        dayOfWeek = day % testFreq
        if dayOfWeek >= splitsDRT:  # assumes splitsDRT <= testFreq
            return 0
        beg = dayOfWeek * groupSizeDRT
        end = beg + groupSizeDRT
        if end > population:
            end = population
        sumo = 0
        for b in range(beg, end):  # Test people in range beg to end
            testing(people[b])
            sumo += 1
        return sumo





    # Breaks population into splitsCBT number of groups, then makes subgroups depending
    # on rate of testing of their group. The last group and last subgroup for each group
    # are smaller due to ceiling rounding of group and subgroup size.
    if cbt:
        sumo = 0
        for l in range(splitsCBT):
            subgroupIndex = day % testRateArray[l]
            beg = l * groupSizeCBT + subgroupIndex * int(np.ceil(groupSizeCBT / testRateArray[l]))
            end = beg + int(np.ceil(groupSizeCBT / testRateArray[l]))
            if end > (l + 1) * groupSizeCBT:
                end = (l + 1) * groupSizeCBT
                if end > population:
                    end = population
            for b in range(beg, end):
                testing(people[scsList[b]])
                sumo += 1
        return sumo

# Generic infection function
def infection(dur):
    pr = 1 - np.exp(-beta * dur)
    if np.random.random() < pr:
        return True
    else:
        return False


# Testing probability function
def testing(person):
    if person.quarantine != 0:  # can't test quarantined people
        return
    else:
        if person.identity == 'S' or person.identity == 'R':  # case for healthy
            if np.random.random() < falsePos:
                person.quarantine = quarLength  # false positive
        else:
            if np.random.random() > falseNeg:
                person.quarantine = quarLength  # false negative
    return


"""PREPROCESSING (this stays constant each trial)"""


# Create a list of all people in the network, along with counters for SEIR
preProStartTime = time.perf_counter()
people = []
r0 = 0  # just for R_0 calculations...
for i in range(population):  # Initialize entire population
    people.append(Person('S', np.random.lognormal(incuMean, incuVar), infeMean))

registrar = []  # Array of all courses. Courses are indexed 1, 2, ...
masterSchedule = []  # List of all schedules of students
departmentLists = [[] for i in range(6)]  # List of all students in each department
gradLists = [[] for i in range(2)]  # List of students by undergrad or grad status

# Generate random meeting days and durations for courses in the schedule
# Initialize courses (with random durations)
for i in range(courseCount):

    tempCourse = Course()
    # tempCourse.duration = np.random.choice(range(4)[1:3]) * courseDur  # duration is .04, .08
    tempCourse.duration = random.choice(range(4)[1:3]) * courseDur
    # Randomly choose the days of the week in which a course meets
    rand = np.random.random()
    if rand < 0.2:
        tempCourse.days = [True, False, True, False, False, False, False]  # M W (0.2)
    elif rand < 0.6:
        tempCourse.days = [False, True, False, True, False, False, False]  # T Th (0.4)
    else:
        tempCourse.days = [True, False, True, False, True, False, False]  # M W F (0.4)
    registrar.append(tempCourse)

# Closeness centrality of each course
centralOut = open(centralityData, "r").readlines()
centralArray = []
for i in centralOut:
    temp = i.split()
    centralArray.append(float(temp[1]))

# Read in Cornell or other data to make connections between students and courses
# Set schedule, dept, and isGrad for all students
allTxt = open(networkEdgeList, "r").readlines()
i = 1
tempSchedule = []

# Set dept and isGrad for first student
tempDept = int(allTxt[0].split()[2])
people[0].dept = tempDept
departmentLists[tempDept].append(0)
tempIsGrad = int(allTxt[0].split()[3])
people[0].isGrad = tempIsGrad
gradLists[tempIsGrad].append(0)

studentCentrality = {}  # array that keeps track of student centrality score
tempScore = 0

studentCentrality[0] = 0  # Insert first student into dictionary

for edge in allTxt:
    temp = edge.split()
    courseID = int(temp[1]) - 1
    if int(temp[0]) == i:  # if corresponds to student i
        studentCentrality[i - 1] += centralArray[courseID]  # Update student centrality score
        tempSchedule.append(registrar[courseID])
        registrar[courseID].students.append(people[i - 1])
    else:  # adds tempSchedule to master, increments i for next student
        masterSchedule.append(tempSchedule)
        tempSchedule = []
        tempScore = 0
        i += 1

        # Set departments
        tempDept = int(temp[2])
        people[i - 1].dept = tempDept
        departmentLists[tempDept].append(i - 1)

        # Set isGrad
        tempIsGrad = int(temp[3])
        people[i - 1].isGrad = tempIsGrad
        gradLists[tempIsGrad].append(i - 1)

        # Insert new student to dict and add score of first class
        studentCentrality[i - 1] = centralArray[courseID]

        # Set schedule
        tempSchedule.append(registrar[courseID])  # adds course to schedule of student
        registrar[courseID].students.append(people[i - 1])  # adds student to course
masterSchedule.append(tempSchedule)

# Sort student centrality scores
studentCentralitySorted = sorted(studentCentrality.items(), key=lambda x: x[1], reverse=True)
scsList = []
for i in studentCentralitySorted:
    scsList.append(i[0])

print(len(scsList))
# for i in studentCentralitySorted[:100]:
#
#     print(i[0], i[1])
#     print(studentCentralitySorted[i])

# Loop that creates lists of classmates (deterministically)
for i in range(population):
    for day in range(5):
        temp = []  # array of double pairs...
        for c in masterSchedule[i]:  # go through all courses for each student
            if c.days[day]:
                temp2 = c.students.copy()
                temp2.remove(people[i])
                for j in range(len(temp2)):
                    temp2[j] = [temp2[j], c.duration]  # double pair: person, duration
                temp += temp2
        people[i].classmates.append(temp)  # student.classmates is now a list of lists

preProEndTime = time.perf_counter()
preProDelta = preProEndTime - preProStartTime  # pre-processing timer

# Cumulates all data created in the trials
cumS, cumE, cumI, cumR = [], [], [], []

""""OUTER SIMULATION LOOP FOR TRIALS"""
startTime = time.perf_counter()
for t in range(trials):
    # trial switcher
    if t < trials / 2:
        generalTest = True
        cbt = False
    else:
        generalTest = False
        cbt = True

    testss = []

    # Counters for SEIR
    numS, numE, numI, numR = population, 0, 0, 0

    # Arrays used for tracking & graphing compartment sizes over time
    Susceptible, Exposed, Infected, Recovered = [], [], [], []

    # Reset population
    for i in range(population):
        people[i].reset('S', np.random.lognormal(incuMean, incuVar), infeMean)
    # Randomly infect "initialI" people
    infectedIndices = list(np.random.choice(range(population), initialI, replace=False))
    for i in infectedIndices:
        people[i].identity = 'I'
        people[i].infectionDay = 0
        numI += 1
        numS -= 1

    # Loop that creates RANDOM friend connections
    for c in registrar:
        size = (len(c.students))
        k = int(np.sqrt(size))
        if size < 5:
            k = size
        studentsCopy = c.students.copy()
        np.random.shuffle(studentsCopy)  # shuffles the order of students
        split = [studentsCopy[i * k:(i + 1) * k] for i in range((size + k - 1) // k)]
        for group in split:
            for stud in group:
                stud.friends += group
                stud.friends.remove(stud)

    print(t, numS, numE, numI, numR)
    Susceptible.append(numS)
    Exposed.append(numE)
    Infected.append(numI)
    Recovered.append(numR)

    """Runs the simulation for "days" time steps"""
    for a in range(days):
        dayMod = a % 7  # for use below

        testss.append(intervention(a))  # Run intervention function

        # Decrement E and I periods by 1, change E -> I or I -> R if needed
        shuffled = list(range(population))
        random.shuffle(shuffled)
        for i in shuffled:  # goes through indices of people in simulation RANDOMLY
            # for each S person in the population
            if people[i].identity == 'S' and people[i].quarantine == 0:
                if np.random.random() < outsideInfectionRate:  # outside infection chance for the day
                    people[i].identity = 'E'
                    people[i].infectionDay = a
                    numS -= 1
                    numE += 1

            elif people[i].identity == 'E' and people[i].infectionDay != a:
                people[i].incuPeriod -= 1
                if people[i].incuPeriod <= 0:
                    people[i].identity = 'I'
                    numE -= 1
                    numI += 1

            elif people[i].identity == 'I':
                people[i].infePeriod -= 1
                if people[i].quarantine == 0:

                    # Friend interactions go here
                    if friendI:
                        length = len(people[i].friends)
                        poisson = np.random.poisson(friendInteract)
                        if length < poisson:
                            poisson = length
                        # pick from their friend array
                        interactions = random.sample(range(length), poisson)
                        for p in interactions:
                            if people[i].friends[p].identity == 'S' and people[i].friends[p].quarantine == 0 \
                                    and infection(friendDur):
                                people[i].friends[p].identity = 'E'  # infect person p
                                people[i].friends[p].infectionDay = a
                                people[i].infectCount += 1  # update person i's body count
                                numS -= 1
                                numE += 1

                    # Class interactions go here
                    if classI:
                        if dayMod < 5:
                            length = len(people[i].classmates[dayMod])  # length of peoples classmates array for day
                        else:
                            length = 0
                        if length != 0:
                            poisson = np.random.poisson(classInteract)
                            if length < poisson:
                                poisson = length
                            interactions = random.sample(range(length), poisson)
                            for p in interactions:
                                duration = people[i].classmates[dayMod][p][1]
                                if people[i].classmates[dayMod][p][0].identity == 'S' and \
                                        people[i].classmates[dayMod][p][0].quarantine == 0 and infection(duration):
                                    people[i].classmates[dayMod][p][0].identity = 'E'  # infect person p
                                    people[i].classmates[dayMod][p][0].infectionDay = a
                                    people[i].infectCount += 1  # update person i's body count
                                    numS -= 1
                                    numE += 1

                    # Department interactions go here
                    if deptI:
                        dep = people[i].dept
                        length = len(departmentLists[dep])
                        poisson = np.random.poisson(deptInteract)
                        interactions = random.sample(range(length), poisson)
                        for p in interactions:
                            if people[departmentLists[dep][p]].identity == 'S' \
                                    and people[departmentLists[dep][p]].quarantine == 0 and infection(deptDur):
                                people[departmentLists[dep][p]].identity = 'E'  # infect person p
                                people[departmentLists[dep][p]].infectionDay = a
                                people[i].infectCount += 1  # update person i's body count
                                numS -= 1
                                numE += 1

                    # Inter-graduate interactions go here
                    if gradI:
                        grad = people[i].isGrad
                        length = len(gradLists[grad])
                        poisson = np.random.poisson(gradInteract)
                        interactions = random.sample(range(length), poisson)
                        for p in interactions:
                            if people[gradLists[grad][p]].identity == 'S' and people[gradLists[grad][p]].quarantine \
                                    == 0 and infection(gradDur):
                                people[gradLists[grad][p]].identity = 'E'  # infect person p
                                people[gradLists[grad][p]].infectionDay = a
                                people[i].infectCount += 1  # update person i's body count
                                numS -= 1
                                numE += 1

                if people[i].infePeriod <= 0:
                    people[i].identity = 'R'
                    numI -= 1
                    numR += 1

            if people[i].quarantine != 0:  # if in quarantine, decrement by 1
                people[i].quarantine -= 1

        Susceptible.append(numS)
        Exposed.append(numE)
        Infected.append(numI)
        Recovered.append(numR)
        print(t, numS, numE, numI, numR, testss[a])

    # Save copies of output data
    cumS.append(Susceptible)
    cumE.append(Exposed)
    cumI.append(Infected)
    cumR.append(Recovered)

    # Stuff for calculating R0
    infSum = 0
    for i in range(population):
        if people[i].identity == 'R':
            infSum += people[i].infectCount
    infSum = infSum / numR
    print('R_0 of trial ' + ' ' + str(t) + ' = ' + str(infSum))
    r0 += infSum

print('Avg R_0 =' + str(r0/trials))

# Plot lines

for i in range(trials):
    if i < trials / 2:
        plt.plot(cumS[i], color='b', linewidth=1)
        plt.plot(cumE[i], color='b', linewidth=1)
        plt.plot(cumI[i], color='b', linewidth=1)
        plt.plot(cumR[i], color='b', linewidth=1)
    else:
        plt.plot(cumS[i], color='r', linewidth=1)
        plt.plot(cumE[i], color='r', linewidth=1)
        plt.plot(cumI[i], color='r', linewidth=1)
        plt.plot(cumR[i], color='r', linewidth=1)


plt.xlabel('Time')
plt.ylabel('Population')
plt.title(str(__file__) + ' Network SEIR Simulation: ' + str(trials) + ' Trials | ' + str(days) + ' Days')
endTime = time.perf_counter()
print('Preprocessing: ' + str(preProDelta) + ' s')
print('Runtime: ' + str(endTime - startTime) + ' s')
plt.show()

