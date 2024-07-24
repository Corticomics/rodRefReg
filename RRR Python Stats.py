import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats

# Data
data = {
    'Trial': range(1, 31),
    'Pump 1': [1374, 1307, 1297, 1284, 1273, 1254, 1222, 1262, 1216, 1168, 1205, 1344, 1319, 1312, 1305, 1202, 1342, 1341, 1309, 1304, 1307, 1348, 1343, 1335, 1362, 1339, 1317, 1368, 1313, 1300],
    'Pump 2': [1229, 1189, 1173, 1170, 1227, 1218, 1222, 1193, 1245, 1216, 1228, 1121, 1095, 1141, 1134, 1137, 1101, 1107, 1095, 1088, 1045, 1071, 1071, 1135, 1125, 1068, 1132, 1153, 1142, 1220],
    'Pump 3': [1468, 1298, 1271, 1268, 1250, 1238, 1247, 1332, 1299, 1297, 1416, 1285, 1262, 1303, 1297, 1287, 1281, 1268, 1249, 1244, 1211, 1220, 1186, 1293, 1288, 1241, 1280, 1321, 1304, 1356],
    'Pump 4': [1202, 1119, 1108, 1106, 1106, 1077, 1058, 1075, 1075, 1083, 1112, 1184, 1159, 1158, 1132, 1105, 1177, 1308, 1284, 1258, 1288, 1296, 1286, 1281, 1312, 1319, 1315, 1304, 1304, 1260]
}

# Creating a DataFrame
df = pd.DataFrame(data)

# Function for bootstrapping and calculating variance
def bootstrap_variance(data, num_trials, num_bootstrap=1000):
    bootstrapped_variances = {pump: [] for pump in data.columns if pump != 'Trial'}
    for _ in range(num_bootstrap):
        sample = data.sample(n=num_trials, replace=True)
        for pump in bootstrapped_variances.keys():
            bootstrapped_variances[pump].append(sample[pump].var())
    return {pump: np.mean(variances) for pump, variances in bootstrapped_variances.items()}

# Bootstrap up to 1000 trials
trial_numbers = [30, 100, 300, 500, 1000]
variances = {num_trials: bootstrap_variance(df, num_trials) for num_trials in trial_numbers}

# For plotting
variance_df = pd.DataFrame(variances).T

# Displaying the calculated variances
print("Bootstrapped Variances for Different Trial Numbers:")
print(variance_df)

# Plotting the variance scaling
plt.figure(figsize=(12, 8))
for pump in variance_df.columns:
    plt.plot(variance_df.index, variance_df[pump], marker='o', label=pump)
plt.title('Variance Scaling Across Different Numbers of Trials')
plt.xlabel('Number of Trials')
plt.ylabel('Variance in Water Weight (mg²)')

plt.yticks([2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000])
plt.xticks([30, 100, 300, 500, 1000])  # More increments on x-axis
plt.legend()
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.show()

# Descriptive stats
stats_summary = df.describe()
print("Basic Statistics:")
print(stats_summary)

# Coefficient of Variation
cv = df.std() / df.mean()
print("\nCoefficient of Variation:")
print(cv)

# Correlation matrix
correlation_matrix = df.corr()
print("\nCorrelation Matrix:")
print(correlation_matrix)

# ANOVA test (one-way)
anova_result = stats.f_oneway(df['Pump 1'], df['Pump 2'], df['Pump 3'], df['Pump 4'])
print("\nANOVA Result:")
print(anova_result)

# Box plot
plt.figure(figsize=(10, 6))
sns.boxplot(data=df.drop('Trial', axis=1))
plt.title('Box Plot of Water Weights by Pump')
plt.ylabel('Water Weight (mg)')
plt.yticks(np.arange(1000, 1501, 50))  # More increments on y-axis
plt.grid(True)
plt.show()

# Pair plot
pair_plot = sns.pairplot(df.drop('Trial', axis=1))
for ax in pair_plot.axes.flatten():
    ax.grid(True)  # Adding grid lines to each subplot
plt.suptitle('Pair Plot of Water Weights by Pump (mg)', y=1.02)
plt.show()

# Line graph
plt.figure(figsize=(12, 8))
for column in df.columns[1:]:
    plt.plot(df['Trial'], df[column], marker='o', label=column)
plt.title('Water Weights for Each Pump Over Trials')
plt.xlabel('Trial Number')
plt.ylabel('Water Weight (mg)')
plt.xticks(df['Trial'])  # Ensure x-axis increments for every trial
plt.yticks(np.arange(1000, 1501, 25))  # More increments on y-axis
plt.legend()
plt.grid(True)
plt.show()
