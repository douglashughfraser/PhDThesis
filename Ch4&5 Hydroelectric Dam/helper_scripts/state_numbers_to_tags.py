import csv
import pandas as pd

class FileProcessor:
    def __init__(self, state_columns):
        self.state_columns = state_columns

    def get_state_from_index(self, state_int):
        """
        Convert an integer to a dictionary of boolean values for the given keys names.
        """
        keys = self.state_columns

        # Determine the number of bits needed based on the number of columns
        num_bits = len(keys)
        
        # Convert the integer to a binary string, pad with leading zeros to ensure it has the correct number of bits
        binary_string = format(state_int, f'0{num_bits}b')
        
        # Make state into a dictionary
        state_dict = {keys[i]: int(str_bit) for i, str_bit in enumerate(binary_string)}
        state_dict["state_id"] = state_int
        return state_dict

    def process_transitions(self):
        input_file = "C:/Users/dfraser/Documents/transition errors/states.csv"

        # Read the input CSV and collect all unique state integers
        state_numbers = []
        with open(input_file, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['previous_state']:
                    state_numbers.append(int(row['previous_state']))
                if row['next_state']:
                    state_numbers.append(int(row['next_state']))

        # Convert each state number into a dictionary of boolean values
        state_dicts = [self.get_state_from_index(state) for state in state_numbers]

        # Convert the results into a DataFrame and save to a CSV file
        df = pd.DataFrame(state_dicts)
        output_file = "error_transitions_to_tags.csv"  # Output CSV filename
        df.to_csv(output_file, index=False)

        print(f"State values have been written to {output_file}.")

    def process_states(self):
        input_file = "C:/Users/User/Documents/University/PhD/processing_promela_evaluation/bad_forest_frequencies_chopped.csv"

        # Read the input CSV and collect all unique state integers
        state_numbers = []
        with open(input_file, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['state_id']:
                    state_numbers.append(int(row['state_id']))

        print(len(state_numbers))

        # Convert each state number into a dictionary of boolean values
        state_dicts = [self.get_state_from_index(state) for state in state_numbers]

        # Convert the results into a DataFrame and save to a CSV file
        df = pd.DataFrame(state_dicts)
        output_file = "bad_forest.csv"  # Output CSV filename
        df.to_csv(output_file, index=False)

        print(f"State values have been written to {output_file}.")

# Define the column names
state_columns = ['Flood_Gate_Valve',
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

# Initialize state processor
file_processor = FileProcessor(state_columns)

file_processor.process_states()