import gurobipy as gp       # Import Gurobi package for optimization modeling
from gurobipy import GRB    # Import the Gurobi constants
import pandas as pd         # Import Pandas for data manipulation
import numpy as np          # Import NumPy for numerical operations
import matplotlib.pyplot as plt  # Import Matplotlib for plotting

# Initialize the optimization model
m = gp.Model('Nurses Scheduling')

# Read data from CSV files into Pandas DataFrames
activities = pd.read_csv("activities.csv")
nurses = pd.read_csv("nurses.csv")

# Define sets based on the data
I = range(len(activities) + 1) # Tasks index set including a dummy source
K = range(len(nurses)) # Nurses index set
A = I[1:]       # Actual tasks, excluding the dummy source

# Parameters from data
q = list(nurses['maxh'].copy())  # Maximum working hours for each nurse
l = list(nurses['level'].copy())  # Skill level of each nurse
s = list(activities['start_time'].copy())  # Start times for each activity
t = list(activities['end_time'].copy())  # End times for each activity
h = list(activities['hard'].copy())  # Difficulty or skill requirement for each activity
W = 2  # Maximum waiting time between consecutive activities

# Insert dummy source parameters
s.insert(0,0)  # Start time for the source
t.insert(0,0)  # End time for the source
h.insert(0,0)  # Skill level for the source

# Compute backward star for each task
back = [[]]  # Source has an empty set as backward star
for i in I[1:-1]:
    backi = [0]
    for j in I[1:-1]:
        if (s[i] >= t[j] and s[i]-t[j] <= W):
            backi.append(j)
    back.append(backi)
back.append([i for i in I[1:-1]])  # Dummy end task has all other nodes except the source and itself

# Compute forward star for each task
forward = []
forward.append([i for i in I[1:-1]])  # All tasks for the source
for i in I[1:-1]:
    forwardi = [I[-1]]
    for j in I[1:-1]:
        if (s[j] >= t[i] and s[j]-t[i] <= W):
            forwardi.append(j)
    forward.append(forwardi)
forward.append([])  # Empty forward star for the dummy end task

# Generate subsets of nurses based on skill levels
KL = []
KL.append([k for k in K])
for i in A:
    levelok = [k for k in K if l[k] >= h[i]]  # Nurses qualified for task i
    KL.append(levelok)
KL.append([k for k in K])  # All nurses are qualified for the dummy end task

# Generate subsets of activities that each nurse is qualified to perform
AL = []
for k in K:
    levelok = [0] + [i for i in A if l[k] >= h[i]] + [I[-1]]  # Tasks nurse k is qualified for, including dummy tasks
    AL.append(levelok)

# Define decision variables: X[i,j,k] is 1 if nurse k transitions from task i to j
# Only necessary variables are instantiated to reduce model size
variables = []
for i in I:
    for j in I:
        if (s[j] >= t[i] and s[j] <= t[i]+W) or (i == 0 and j != 0) or (i != 0 and j == 0):  # Condition for feasible transitions
            for k in K:
                if h[i] <= l[k] and h[j] <= l[k] and q[k] >= t[i] - s[i] + t[j] - s[j]:  # Nurse k is qualified for both tasks
                    variables.append((i,j,k))
X = m.addVars(variables, vtype=GRB.BINARY, name="x")  # Binary decision variables

# Create a DataFrame to facilitate constraint creation
df = pd.DataFrame(variables, columns = ['I', 'J', 'K'])

# Set objectives: Minimize the number of working nurses and maximize skill utilization
# Primary objective: Minimize the number of nurses starting their schedule (i.e., going from source to first task)
m.setObjectiveN(gp.quicksum(X[(i,j,k)] for (i,j,k) in df[df.I == 0].values), index=0, priority=2, name='number of working nurses')
# Secondary objective: Minimize skill underutilization across all tasks
m.setObjectiveN(gp.quicksum(X[(i,j,k)]*(l[k]-h[i]) for (i,j,k) in df[df.I != 0].values), index=1, priority=1, name="skill not used")
m.ModelSense = gp.GRB.MINIMIZE  # The optimization direction

# Constraints
# Ensure total working hours for each nurse do not exceed their maximum
for k in K:
    m.addConstr(gp.quicksum(X[(i,j,k)]*(t[i]-s[i]) for (i,j,k) in df[(df.K == k)&(df.I!=0)].values) <= q[k], name='maxhours')  

# Ensure each task is assigned to exactly one nurse
for i in A:
    m.addConstr(gp.quicksum(X[(i,j,k)] for (i,j,k) in df[df.I==i].values) == 1, name='Assignment')
    m.addConstr(gp.quicksum(X[(j,i,k)] for (j,i,k) in df[df.J==i].values) == 1, name='Assignment')

# Flow conservation: Each task for each nurse must have equal incoming and outgoing arcs
for i in A:
    for k in set(df[df.I==i].K.values):
        m.addConstr(gp.quicksum(X[(i,j,k)] for (i,j,k) in df[(df.I==i)&(df.K==k)].values) == 
                    gp.quicksum(X[(j,i,k)] for (j,i,k) in df[(df.J==i)&(df.K==k)].values))

# Each nurse starting work (leaving the source) must end their day (arrive at the sink)
for k in K:
    m.addConstr(gp.quicksum(X[(i,j,k)] for (i,j,k) in df[(df.I==0)&(df.K==k)].values) == gp.quicksum(X[(i,j,k)] for (i,j,k) in df[(df.J==0)&(df.K==k)].values))
    m.addConstr(gp.quicksum(X[(i,j,k)] for (i,j,k) in df[(df.I==0)&(df.K==k)].values) <= 1)

m.params.TimeLimit = 300  # Limit the solution time to 300 seconds
m.optimize()  # Solve the model