import plotly.figure_factory as ff
from datetime import date
# Function to extract routes from the optimization solution
def getRoutes(X):
    x = []
    keys = []
    for (i,j,k) in X:
        if X[(i,j,k)].x == 1:  # If the decision variable is set to 1 (task assigned)
            x.append((i,j,k))
            if k not in keys:
                keys.append(k)  # Keep track of nurses involved

    routes = {}  # Dictionary to store routes by nurse
    for key in keys: 
        n = 0
        routes[key] = []
        while 0 not in routes[key]:  # Loop until reaching the source task (0)
            for (i,j,k) in x:
                if k == key and i == n:
                    routes[key].append(j)
                    n = j  # Move to the next task
    return(routes)

# Use the function to get routes from the optimization solution
routes = getRoutes(X)

# Preparation for Gantt chart visualization
today = date.today().strftime("%Y-%m-%d")
gantt = []

# Mapping skill levels to labels
required_level = ["None", "Beginner", "Intermediate", "Advanced"]       
nurse_level = ["None", "Beginner", "Intermediate", "Advanced"]

# Preparing start and end times for tasks
start = ["None"] + [f"{hour}:00:00" for hour in s[1:]]
end = ["None"] + [f"{hour}:00:00" if hour != 24 else "23:59:59" for hour in t[1:]]

# Constructing data for the Gantt chart
for i in routes:
    for j in routes[i][:-1]:
        task_info = {
            "Task": f"Nurse {i} ({nurse_level[l[i]]})",
            "Start": f"{today} {start[j]}",
            "Finish": f"{today} {end[j]}",
            "Required_Level": required_level[h[j]],
            "task_names": str(j)
        }
        gantt.append(task_info)

# Define colors for different skill levels
colors = {
    "Advanced": 'rgb(114, 44, 121)',
    "Intermediate": 'rgb(198, 47, 105)',
    "Beginner": 'rgb(46, 137, 205)'
}

# Creating the Gantt chart using Plotly
fig = ff.create_gantt(gantt, colors=colors, index_col='Required_Level', title='Daily Schedule',
                      show_colorbar=True, height=500, showgrid_x=True, showgrid_y=True, group_tasks=True, task_names=task_names)

fig.show()  # Display the Gantt chart
