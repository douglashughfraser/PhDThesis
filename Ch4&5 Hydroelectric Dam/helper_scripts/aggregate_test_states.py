import os
import re
import pandas as pd

directory = './evaluation_files/models'

# List to store the tag-value dictionaries for each file
data = []

# Iterate over all files in the specified directory
for filename in os.listdir(directory):
    if (not re.search("reachable", filename) is None) & (re.search("unreachable", filename) is None) & filename.endswith('.pml'):
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r') as file:
            content = file.read()

            #Regular expression to extract the block within 'ltl reachable_state { }'
            pattern = r'ltl reachable_state\s*{\s*(.*?)\s*}'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                block = match.group(1).strip()

                # Remove '!<>(' at the start and ')' at the end of the block
                if block.startswith('!<>(') and block.endswith(')'):
                    block = block[4:-1].strip()
                else:
                    print(f"Unexpected block format in {filename}")
                    continue

                # Clean up the block by removing newlines and extra spaces
                block = block.replace('\n', '').replace('\t', '').strip()

                # Split the block into individual expressions using '&&' as the separator
                expressions = block.split('&&')
                tag_values = {}

                # Process each expression to extract tag-value pairs
                for expr in expressions:
                    expr = expr.strip()
                    if expr.startswith('(') and expr.endswith(')'):
                        expr = expr[1:-1].strip()
                    else:
                        print(f"Unexpected expression format in {filename}: {expr}")
                        continue

                    if '==' in expr:
                        tag, value = expr.split('==')
                        tag = tag.strip()
                        value = value.strip()
                        tag_values[tag] = value
                    else:
                        print(f"No '==' in expression in {filename}: {expr}")
                        continue

                # Add the filename to the tag-values dictionary
                tag_values['Filename'] = filename
                data.append(tag_values)
            else:
                print(f"No matching block found in {filename}")
                continue

# Create a DataFrame from the collected data
df = pd.DataFrame(data)

# Optionally reorder columns to place 'Filename' at the front
cols = df.columns.tolist()
if 'Filename' in cols:
    cols.insert(0, cols.pop(cols.index('Filename')))
    df = df[cols]

# Write the DataFrame to a CSV file
df.to_csv('output.csv', index=False)

print("Data extraction complete. The results are saved in 'output.csv'.")
