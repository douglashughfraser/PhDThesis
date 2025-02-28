import pandas as pd
import itertools

def load_csv(file_path):
    """Load transitions CSV into a DataFrame."""
    return pd.read_csv(file_path)

def get_state_from_index(index):
        keys = [
            'Flood_Gate_Valve',
            'Flood_Pump',
            'Sump_Valve',
            'Sump_Pump_1',
            'Sump_Pump_2',
            'Activated_Flood_Control',
            'Return_Water_Supply_Control',
            'Gen_A_Status',
            'Gen_B_Status',
            'Gen_A_Active',
            'Gen_A_Fan',
            'Gen_A_Pump',
            'Gen_A_Valve',
            'Gen_A_RedLED',
            'Gen_A_GreenLED',
            'Gen_B_Active',
            'Gen_B_Fan',
            'Gen_B_Pump',
            'Gen_B_Valve',
            'Gen_B_RedLED',
            'Gen_B_GreenLED',
            'Tag_2',
            'HMI_Return_Feed'
        ]

        # Determine the number of bits needed based on the number of columns
        num_bits = len(keys)
        
        # Convert the integer to a binary string, pad with leading zeros to ensure it has the correct number of bits
        binary_string = format(index, f'0{num_bits}b')
        
        # Make state into a dictionary, convert to dataframe
        state_dict = {keys[i]: int(str_bit) for i, str_bit in enumerate(binary_string)}
        state_dict["state_id"] = index
        return state_dict

def fuzz_state(state):
    """
    Generate all variations of a binary state by flipping each variable.
    A binary state is represented as a dictionary of variables and their values.
    """
    variations = []
    for tag in state.keys():
        # Create a copy of the state to modify
        modified_state = state.copy()
        # Flip the binary value (0->1 or 1->0)
        modified_state[tag] = 1 - modified_state[tag]
        variations.append(modified_state)
    return variations

def state_to_integer(state):
    """
    Convert a binary state (dictionary of variables) to an integer.
    Binary variables are treated as a binary number.
    """

    state.pop('state_id')
    binary_string = ''.join(str(state[key]) for key in sorted(state.keys()))
    return int(binary_string, 2)

def read_states(inputfile):
    states = []
    for row in inputfile.itertuples():
        #print(f"{row.state}")
        #new_state = get_state_from_index(row.state)
        new_state = row.state
        if new_state not in states:
            states.append(new_state)

    return states
    

# Function to generate all pairs from two sets of states
def generate_pairs(list1, list2):
    # Using list comprehension to generate all pairs
    return [(a, b) for a in list1 for b in list2]

if __name__ == '__main__':
    # Load transitions CSV
    negatives_csv = load_csv("evaluation_files/datasets/state_false_negatives_afc_removed.csv")
    step1_csv = load_csv("evaluation_files/datasets/test_states_2_steps.csv")
    output_file = "evaluation_files/datasets/fn_2step.csv"
 
    # Extract all unique states from the input
    step1 = read_states(step1_csv)
    negatives = read_states(negatives_csv)

    # Generate all pairs of states within a group
    #pairs = list(itertools.product(states, repeat=2))

    # Generate all pairs of states between two groups

    pairs = generate_pairs(negatives, step1) 

    # Save pairs to a CSV
    transitions_df = pd.DataFrame(pairs, columns=["previous_state", "next_state"])
    transitions_df.to_csv(output_file, index=False)

    print(f"Generated test transition CSV: {output_file}")