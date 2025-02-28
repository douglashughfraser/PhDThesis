import os
import re
import csv
import pandas as pd
from collections import defaultdict

# Define directories containing the mixed files
directories = ["evaluation_files/transition_models/all"]#"evaluation_files/transition_models/2s_baseline_and_baseline_2s", "evaluation_files/transition_models/false_neg_and_1s_baseline"]

# Regex patterns for variable extraction
start_pattern = re.compile(r'bool\s+([\w_]+)\s*=\s*(\d|false|true);')
end_pattern = re.compile(r'(\w+)\s*==\s*(\d|false|true)')

# Function to extract variables from file content
def extract_variables(file_path, start_pattern, end_pattern):
    with open(file_path, 'r') as file:
        content = file.read()
    return dict(start_pattern.findall(content)), dict(end_pattern.findall(content))

def extract_filename_info(filename):
    filename_pattern = re.compile(r'_(valid|error)_(\d+)--(\d+)')
    match = filename_pattern.match(filename)
    if match:
        result, start_state_id, end_state_id = match.groups()
        return {
            "result": result,
            "start_id": int(start_state_id),
            "end_id": int(end_state_id)
        }
    else:
        return None

# Function to process files and classify based on valid/error filenames
def process_files(directories, baseline_states):
    start_data = defaultdict(lambda: {"valid": 0, "error": 0})
    end_data = defaultdict(lambda: {"valid": 0, "error": 0})

    count = 0

    # Track state transitions
    transition_counts = [
        defaultdict(lambda: {"valid": [0, 0, 0, 0], "error": [0, 0, 0, 0]}),
        defaultdict(lambda: {"valid": [0, 0, 0, 0], "error": [0, 0, 0, 0]}),
        defaultdict(lambda: {"valid": [0, 0, 0, 0], "error": [0, 0, 0, 0]}),
        defaultdict(lambda: {"valid": [0, 0, 0, 0], "error": [0, 0, 0, 0]})
    ]

    false_positives = []
    base_fab = []
    fab_base = []

    for directory in directories:
        for filename in os.listdir(directory):
            count += 1
            if count % 1000 == 0: 
                print(f"Processed {count} files: processing {filename}")

            transition =  extract_filename_info(filename)

            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                # Determine category based on filename
                category = "valid" if "valid" in filename.lower() else "error"

                # Extract start and end variables
                start_variables, end_variables = extract_variables(file_path, start_pattern, end_pattern)

                for var, value in start_variables.items():
                    start_data[f"{var}={value}"][category] += 1

                for var, value in end_variables.items():
                    end_data[f"{var}={value}"][category] += 1

                # Analyze state changes
                for var in start_variables.keys():
                    start_val = start_variables.get(var, "0")
                    end_val = end_variables.get(var, "0")

                    if start_val == "false": 
                        start_val = "0"
                    
                    if end_val == "false": 
                        end_val = "0"
                    
                    if transition is not None:
                        if (transition["end_id"] not in baseline_states) and (transition["start_id"] not in baseline_states):
                            transition_type = 0
                            if var == "Flood_Pump":
                                false_positives.append({
                                    "previous_state": transition["start_id"],
                                    "new_state": transition["end_id"]
                                })
                                # Collect false positive transition details
                        elif (transition["end_id"] in baseline_states) and (transition["start_id"] in baseline_states):
                            transition_type = 3
                        elif (transition["start_id"] in baseline_states) and (transition["end_id"] not in baseline_states):
                            transition_type = 1
                            if var == "Flood_Pump":
                                base_fab.append({
                                    "previous_state": transition["start_id"],
                                    "new_state": transition["end_id"]
                                })
                        elif (transition["end_id"] in baseline_states) and (transition["start_id"] not in baseline_states):
                            transition_type = 2
                            if var == "Flood_Pump":
                                fab_base.append({
                                    "previous_state": transition["start_id"],
                                    "new_state": transition["end_id"]
                                })
                        
                    # Determine transition index based on (start, end) values
                    if start_val == "0" and end_val == "0":
                        idx = 0  # 0 -> 0
                    elif start_val == "0" and end_val == "1":
                        idx = 1  # 0 -> 1
                    elif start_val == "1" and end_val == "0":
                        idx = 2  # 1 -> 0
                    elif start_val == "1" and end_val == "1":
                        idx = 3  # 1 -> 1

                    transition_counts[transition_type][var][category][idx] += 1

    return start_data, end_data, transition_counts, false_positives, base_fab, fab_base

with open("evaluation_files/datasets/baseline_states.csv", 'r') as file:
    baseline_states = set()
    reader = csv.reader(file)
    for row in reader:
        if row and row[0].strip().isdigit():  # Ensure valid numeric data
            baseline_states.add(int(row[0].strip()))  # Add clean integer values

# Process directories and collect data
start_data, end_data, transition_counts, false_positives, base_fab, fab_base = process_files(directories, baseline_states)

# Convert data to DataFrame for analysis
start_df = pd.DataFrame.from_dict(start_data, orient="index")
end_df = pd.DataFrame.from_dict(end_data, orient="index")
start_df.fillna(0, inplace=True)  # Replace missing values with 0
end_df.fillna(0, inplace=True)  # Replace missing values with 0

# Calculate the valid and error ratios
start_df["valid_ratio"] = start_df["valid"] / (start_df["valid"] + start_df["error"] + 1e-6)  # Avoid division by zero
start_df["error_ratio"] = start_df["error"] / (start_df["valid"] + start_df["error"] + 1e-6)

end_df["valid_ratio"] = end_df["valid"] / (end_df["valid"] + end_df["error"] + 1e-6)  # Avoid division by zero
end_df["error_ratio"] = end_df["error"] / (end_df["valid"] + end_df["error"] + 1e-6)

# Find variables that change across files
start_df["difference"] = abs(start_df["valid"] - start_df["error"])
end_df["difference"] = abs(end_df["valid"] - end_df["error"])

# Sort by highest difference in occurrences
start_df_sorted = start_df.sort_values(by=["difference", "valid_ratio"], ascending=[False, False])
end_df_sorted = end_df.sort_values(by=["difference", "valid_ratio"], ascending=[False, False])

print(transition_counts)

# Convert transition counts to DataFrame, factoring in transition types
transition_data = []
for transition_type_index, transition_type in enumerate(transition_counts):
    for var, counts in transition_type.items():
        row = [transition_type_index, var] + counts["valid"] + counts["error"]
        transition_data.append(row)

# Define column names to include transition type
columns = ["Transition_Type", "Variable", 
           "valid_0_to_0", "valid_0_to_1", "valid_1_to_0", "valid_1_to_1",
           "error_0_to_0", "error_0_to_1", "error_1_to_0", "error_1_to_1"]

# Create DataFrame with transition types
transition_df = pd.DataFrame(transition_data, columns=columns)

# Replace NaN values with 0 to avoid empty cells
transition_df.fillna(0, inplace=True)

# Save transition data to CSV
transition_df.to_csv('variable_transitions_analysis.csv', index=False)

# Write false positive transitions to a CSV file
false_positive_df = pd.DataFrame(false_positives)
false_positive_df.to_csv('false_positive_transitions.csv', index=False)

base_fab_df = pd.DataFrame(base_fab)
base_fab_df.to_csv('base_fab_transitions.csv', index=False)

fab_base_df = pd.DataFrame(fab_base)
fab_base_df.to_csv('fab_base_transitions.csv', index=False)

print(f"False positive transitions saved to 'false_positive_transitions.csv'.")

# Print a summary of transition data grouped by transition type
print("Transition data breakdown by type:")
print(transition_df.groupby("Transition_Type").sum())

print("\nTop 20 transitions with highest impact:")
print(transition_df.sort_values(by=["valid_0_to_1", "error_0_to_1"], ascending=[False, False]).head(20))
