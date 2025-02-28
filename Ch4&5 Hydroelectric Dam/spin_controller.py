import pandas as pd
import os
import re
from subprocess import run, SubprocessError, PIPE
import generate_dot
import shutil
import argparse
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path

class SpinController:

    def __init__(self):

        # Initialize lock for thread synchronization
        self.lock = threading.Lock()
        self.stop_threads = threading.Event()

        self.transition_template_path = "spin_models/templates/branch_template.pml"
        self.state_template_path = "spin_models/templates/trunk_template.pml"

        if not os.path.exists(self.transition_template_path):
            print(f"Error: The file '{self.transition_template_path}' does not exist.")

        if not os.path.exists(self.state_template_path):
            print(f"Error: The file '{self.state_template_path}' does not exist.")    

        self.non_threaded_workspace = "spin_models"
        self.transition_promela_path = "spin_models/hydro_transition.pml"
        self.state_promela_path = "spin_models/hydro_state.pml"
        self.transitions = pd.DataFrame(columns=["previous_state", "next_state", "valid"])
        self.states = pd.DataFrame(columns=["state", "reachable"])
        self.labels = pd.DataFrame(columns=["state_id", "label"])
        self.state_errors = 0
        self.transition_errors = 0

        self.state_columns = [
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

    def load_states_csv(self, states_path, labels_path):

        # Read the CSV file into a pandas DataFrame
        states = pd.read_csv(states_path)
        labels = pd.read_csv(labels_path)
        
        states = states.merge(labels, how='left', left_index=True, right_on='state_id')

        print(f'Loaded {len(states)} states from path: {states_path}')
        return states

    def load_csv(file_path):
        """Load CSV into a DataFrame."""
        return pd.read_csv(file_path)

    def load_labels_csv(self, labels_path):

        # Read the CSV file into a pandas DataFrame
        labels = pd.read_csv(labels_path)

        print(f'Loaded {len(labels)} states from path: {labels_path}')
        return labels


    def load_transitions_csv(self, transition_path):
        # Read the CSV file into a pandas DataFrame
        transitions = pd.read_csv(transition_path)

        print(f'Loaded {len(transitions)} transitions from path: {transition_path}')
        return transitions

    # Convert an integer to a dictionary of boolean values for the given keys names.
    def get_state_from_index(self, state_int):

        keys = self.state_columns

        # Determine the number of bits needed based on the number of columns
        num_bits = len(keys)
        
        # Convert the integer to a binary string, pad with leading zeros to ensure it has the correct number of bits
        binary_string = format(state_int, f'0{num_bits}b')
        
        # Make state into a dictionary, convert to dataframe
        state_dict = {keys[i]: bool(int(str_bit)) for i, str_bit in enumerate(binary_string)}
        state_dict["state_id"] = state_int
        return state_dict

    # Constructs dictionary of state values associated with the placeholders in the Promela model
    def generate_transition_dictionary(self, start_state, end_state):
        
        # Helper function
        def get_value(state, key):
            value = state.get(key)

            if type(value) == bool or (isinstance(value, float) and value in {0.0, 1.0}):
                return int(value)
            if value == None:
                return "VALUE NOT FOUND"

        # Create the dictionary
        return {
            # START values
            # Control
            "START_Flood_Gate_Valve" : get_value(start_state, "Flood_Gate_Valve"),
            "START_Flood_Pump" : get_value(start_state, "Flood_Pump"),
            "START_Sump_Valve" : get_value(start_state, "Sump_Valve"),
            "START_Sump_Pump_1" : get_value(start_state, "Sump_Pump_1"),
            "START_Sump_Pump_2" : get_value(start_state, "Sump_Pump_2"),
            "START_Activated_Flood_Control" : get_value(start_state, "Activated_Flood_Control"),
            "START_Return_Water_Supply_Control" : get_value(start_state, "Return_Water_Supply_Control"),
            "START_Gen_A_Status" : get_value(start_state, "Gen_A_Status"),
            "START_Gen_B_Status" : get_value(start_state, "Gen_B_Status"),
            "START_Tag_2" : get_value(start_state, "Tag_2"),
            "START_HMI_Return_Feed" : get_value(start_state, "HMI_Return_Feed"),
            
            # Generator
            "START_Gen_A_Active" : get_value(start_state, "Gen_A_Active"),
            "START_Gen_A_Fan" : get_value(start_state, "Gen_A_Fan"),
            "START_Gen_A_GreenLED" : get_value(start_state, "Gen_A_GreenLED"),
            "START_Gen_A_Pump" : get_value(start_state, "Gen_A_Pump"),
            "START_Gen_A_RedLED" : get_value(start_state, "Gen_A_RedLED"),
            "START_Gen_A_Valve" : get_value(start_state, "Gen_A_Valve"),

            "START_Gen_B_Active" : get_value(start_state, "Gen_B_Active"),
            "START_Gen_B_Fan" : get_value(start_state, "Gen_B_Fan"),
            "START_Gen_B_GreenLED" : get_value(start_state, "Gen_B_GreenLED"),
            "START_Gen_B_Pump" : get_value(start_state, "Gen_B_Pump"),
            "START_Gen_B_RedLED" : get_value(start_state, "Gen_B_RedLED"),
            "START_Gen_B_Valve" : get_value(start_state, "Gen_B_Valve"),

            # END values
            # Control
            "END_Flood_Gate_Valve" : get_value(end_state, "Flood_Gate_Valve"),
            "END_Flood_Pump" : get_value(end_state, "Flood_Pump"),
            "END_Sump_Valve" : get_value(end_state, "Sump_Valve"),
            "END_Sump_Pump_1" : get_value(end_state, "Sump_Pump_1"),
            "END_Sump_Pump_2" : get_value(end_state, "Sump_Pump_2"),
            "END_Activated_Flood_Control" : get_value(end_state, "Activated_Flood_Control"),
            "END_Return_Water_Supply_Control" : get_value(end_state, "Return_Water_Supply_Control"),
            "END_Gen_A_Status" : get_value(end_state, "Gen_A_Status"),
            "END_Gen_B_Status" : get_value(end_state, "Gen_B_Status"),
            "END_Tag_2" : get_value(end_state, "Tag_2"),
            "END_HMI_Return_Feed" : get_value(end_state, "HMI_Return_Feed"),
            
            # Generator
            "END_Gen_A_Active" : get_value(end_state, "Gen_A_Active"),
            "END_Gen_A_Fan" : get_value(end_state, "Gen_A_Fan"),
            "END_Gen_A_GreenLED" : get_value(end_state, "Gen_A_GreenLED"),
            "END_Gen_A_Pump" : get_value(end_state, "Gen_A_Pump"),
            "END_Gen_A_RedLED" : get_value(end_state, "Gen_A_RedLED"),
            "END_Gen_A_Valve" : get_value(end_state, "Gen_A_Valve"),
        
            "END_Gen_B_Active" : get_value(end_state, "Gen_B_Active"),
            "END_Gen_B_Fan" : get_value(end_state, "Gen_B_Fan"),
            "END_Gen_B_GreenLED" : get_value(end_state, "Gen_B_GreenLED"),
            "END_Gen_B_Pump" : get_value(end_state, "Gen_B_Pump"),
            "END_Gen_B_RedLED" : get_value(end_state, "Gen_B_RedLED"),
            "END_Gen_B_Valve" : get_value(end_state, "Gen_B_Valve")
            
        }

    # Constructs dictionary of state values associated with the placeholders in the Promela model
    def generate_reachable_dictionary(self, state):
        
        # Helper function
        def get_value(state, key):
            value = state.get(key)

            if type(value) == bool or (isinstance(value, float) and value in {0.0, 1.0}):
                return int(value)
            if value == None:
                return "VALUE NOT FOUND"

        # Create the dictionary
        dictionary = {
            # Reachable values
            # Control
            "REACHABLE_Flood_Gate_Valve" : get_value(state, "Flood_Gate_Valve"),
            "REACHABLE_Flood_Pump" : get_value(state, "Flood_Pump"),
            "REACHABLE_Sump_Valve" : get_value(state, "Sump_Valve"),
            "REACHABLE_Sump_Pump_1" : get_value(state, "Sump_Pump_1"),
            "REACHABLE_Sump_Pump_2" : get_value(state, "Sump_Pump_2"),
            "REACHABLE_Activated_Flood_Control" : get_value(state, "Activated_Flood_Control"),
            "REACHABLE_Return_Water_Supply_Control" : get_value(state, "Return_Water_Supply_Control"),
            "REACHABLE_Gen_A_Status" : get_value(state, "Gen_A_Status"),
            "REACHABLE_Gen_B_Status" : get_value(state, "Gen_B_Status"),
            "REACHABLE_Tag_2" : get_value(state, "Tag_2"),
            "REACHABLE_HMI_Return_Feed" : get_value(state, "HMI_Return_Feed"),
            
            # Generator
            "REACHABLE_Gen_A_Active" : get_value(state, "Gen_A_Active"),
            "REACHABLE_Gen_A_Fan" : get_value(state, "Gen_A_Fan"),
            "REACHABLE_Gen_A_GreenLED" : get_value(state, "Gen_A_GreenLED"),
            "REACHABLE_Gen_A_Pump" : get_value(state, "Gen_A_Pump"),
            "REACHABLE_Gen_A_RedLED" : get_value(state, "Gen_A_RedLED"),
            "REACHABLE_Gen_A_Valve" : get_value(state, "Gen_A_Valve"),

            "REACHABLE_Gen_B_Active" : get_value(state, "Gen_B_Active"),
            "REACHABLE_Gen_B_Fan" : get_value(state, "Gen_B_Fan"),
            "REACHABLE_Gen_B_GreenLED" : get_value(state, "Gen_B_GreenLED"),
            "REACHABLE_Gen_B_Pump" : get_value(state, "Gen_B_Pump"),
            "REACHABLE_Gen_B_RedLED" : get_value(state, "Gen_B_RedLED"),
            "REACHABLE_Gen_B_Valve" : get_value(state, "Gen_B_Valve")
        }
        return dictionary

    def replace_values(self, filedata, dictionary):

        # For every value in the dictionary, replace the key with the associated value
        for key in dictionary:

            filedata = filedata.replace(key, str(dictionary[key]))

        return filedata

    def adjust_transition_template(self, start_state, end_state, thread_workspace):

        output_file = f"{thread_workspace}/hydro_transition.pml"

        try:
            with open(f"{thread_workspace}/hydro_transition_template.pml", 'r') as input_file:
                filedata = input_file.read()

            # Create dictionary of values to replace
            replacement_dict = self.generate_transition_dictionary(start_state, end_state)

            # Insert new values into promela model text
            adjusted_model = self.replace_values(filedata, replacement_dict)

            with open(output_file, 'w') as output:
                output.write(adjusted_model)

        except Exception as e:
                print(f"An error occurred while generating updated transition model: {e}")

    def adjust_state_template(self, state, thread_workspace):

        output_file = f"{thread_workspace}/hydro_state.pml"

        try:
            with open(f"{thread_workspace}/hydro_state_template.pml", 'r') as input_file:
                filedata = input_file.read()

            # Create dictionary of values to replace
            replacement_dict = self.generate_reachable_dictionary(state)

            # Insert new values into promela model text
            adjusted_model = self.replace_values(filedata, replacement_dict)

            with open(output_file, 'w') as output:
                output.write(adjusted_model)

        except Exception as e:
                print(f"An error occurred while generating updated state model: {e}")

    # Executes promela file at given path using SPIN through the command line.
    # Matches output using regex to determine if transition is valid.
    # Returns: True if transition is valid, False if not.
    def run_spin(self, file, thread_workspace):

        if not os.path.exists(os.path.join(thread_workspace, file)):
            print(f"Error: The file '{file}' does not exist.")

        # Run subprocess command to execute SPIN from the command line
        try:
            # Generate PAN verifier from promela specification
            pan_gen = run(["spin", "-a", file], cwd=thread_workspace, capture_output=True) 

            # Compile PAN verifier
            pan_comp = run(["gcc", "-DMEMLIM=4096", "-O2", "-w", "-o", "pan", "pan.c"], cwd=thread_workspace) 
            # Run PAN verifier with options for max search depth, weak fairness and set memory limit.
            pan_search = run(["pan", "-m100000"], capture_output=True, shell=True, text=True, cwd=thread_workspace) 
            # Check if pan subprocess was successful
            if pan_search.returncode != 0:
                print(f"Error running PAN: {pan_search.stderr}")
                return
            else:
                # Search SPIN output for the absence of error trails
                # SPIN generates an error (the counterexample that we want) if the state was reached
                result = re.search("errors: 1", pan_search.stdout)
                #print(pan_search.stdout)

                # Therefore if an error is found then the transition is valid
                if result:
                    return True
                else:
                    return False

        except SubprocessError as e:
            print(e.stderr)

    # Saves copy of transition promela file using transition indexes
    def save_transition_model(self, prefix, previous_state, next_state, thread_workspace):
    
        saving_path = os.path.join(os.getcwd(), "spin_models", "generated_models", f"_{prefix}_{previous_state.get('state_id')}--{next_state.get('state_id')}.pml")

        # Check if Promela file exists
        if not os.path.exists(self.transition_promela_path):
            print(f"Error: The file '{self.transition_promela_path}' does not exist.")
        else:
            # No need to check if saving_path exists as we are creating a new file
            try:
                shutil.copy(f"{thread_workspace}/hydro_transition.pml", saving_path)

                print(f"\tModel instance copied to '{saving_path}' for analysis.")

            except Exception as e:
                print(f"Error during file copy: {e}")

    # Saves copy of states promela file using state index
    def save_state_model(self, prefix, state, thread_workspace):
    
        saving_path = os.path.join(os.getcwd(), "spin_models", "generated_models", f"_{prefix}_{state.get('state_id')}.pml")

        # Check if Promela file exists
        if not os.path.exists(f"{thread_workspace}/hydro_state.pml"):
            print(f"Error: The file '{self.state_promela_path}' does not exist.")
        else:
            try:
                shutil.copy(f"{thread_workspace}/hydro_state.pml", saving_path)

                print(f"\tFull model instance copied to '{saving_path}' for analysis.")
            except Exception as e:
                print(f"An error occurred while saving model: {e}")

    # Outputs transition state in console
    def print_transition_state(self, previous_state, next_state):
        transition_states = pd.DataFrame()

        transition_states = transition_states.append(previous_state, ignore_index=True)
        transition_states = transition_states.append(next_state, ignore_index=True)

        with pd.option_context('display.max_rows', None, 'display.max_columns', None):
            print(transition_states)

    # Outputs state in console
    def print_state(self, state):
        with pd.option_context('display.max_rows', None, 'display.max_columns', None):
            print(state)

    # Sequence code that creates a Promela file that checks transitions between one state and another and runs it through SPIN
    def spin_verify_transition(self, prev_state, next_state, thread_workspace):
        # If not previously checked, then generate a new model file and run SPIN to verify the transition
        self.adjust_transition_template(prev_state, next_state, thread_workspace)

        # If threading is used, the file will be in a seperate thread workspace
        if thread_workspace is None:
            valid_transition = self.run_spin(self.transition_promela_path, thread_workspace)
        else:
            valid_transition = self.run_spin(f"hydro_transition.pml", thread_workspace)

        # If the transition is valid
        if valid_transition:
            print(f"\n--------------------------------------------------------------------------------\nChecked transition: {prev_state.get('state_id')} -> {next_state.get('state_id')}\n\t\t State transition validated by Promela model.")
            # Save a copy of the model
            self.save_transition_model("valid", prev_state, next_state, thread_workspace)
        # Invalid transition
        else:
            print(f"\n--------------------------------------------------------------------------------\nChecked transition: {prev_state.get('state_id')} -> {next_state.get('state_id')}\n\t\t WARNING: State transition NOT valid.")
            self.transition_errors += 1
            #self.print_transition_state(prev_state, next_state)
            self.save_transition_model("error", prev_state, next_state, thread_workspace)

        # Check if the transition already exists in the table
        with self.lock:
            matching_transitions = (
                (self.transitions['previous_state'] == prev_state.get('state_id')) & 
                (self.transitions['next_state'] == next_state.get('state_id'))
            )

            if matching_transitions.any():
                # If a match is found, update the existing row
                self.transitions.loc[matching_transitions, 'valid'] = valid_transition
                #print(f"\t\t Updated existing transition in the table.")
            else:
                # If no match is found, append a new row
                new_row = pd.DataFrame([{
                    "previous_state": prev_state.get('state_id'),
                    "next_state": next_state.get('state_id'),
                    "valid": valid_transition
                }])
                self.transitions = pd.concat([self.transitions, new_row], ignore_index=True)
        
        return valid_transition

    # Sequence code that creates a Promela file that checks if a state is reachable and runs it through SPIN
    def spin_verify_state(self, state, thread_workspace):
        # If not previously checked, then generate a new model file and run SPIN to verify the transition
        self.adjust_state_template(state, thread_workspace)
        
        # If threading is used, the file will be in a seperate thread workspace
        if thread_workspace is None:
            state_reachable = self.run_spin(self.state_promela_path, thread_workspace)
        else:
            state_reachable = self.run_spin(f"hydro_state.pml", thread_workspace)

        # Reachable state
        if state_reachable:
            print(f"\n--------------------------------------------------------------------------------\nChecked reachability of state: {state.get('state_id')}\n\t\t State recognised by Promela model.")
            # Save a copy of the model
            self.save_state_model("reachable", state, thread_workspace)
        # Unreachable state
        else:
            print(f"\n--------------------------------------------------------------------------------\nChecked reachability of state: {state.get('state_id')}\n\t\t WARNING: State not recognised by SPIN.")
            self.state_errors += 1
            #self.print_state(state)
            self.save_state_model("unreachable", state, thread_workspace)

        # Check if state is located in memoisation table
        with self.lock:

            matching_state = (self.states['state'] == state.get('state_id'))

            if matching_state.any():
                # If a match is found, update the existing row
                self.states.loc[matching_state, 'reachable'] = state_reachable
                print(f"\t\t Updated existing state entry in the table.")
            else:
                # If no match is found, append a new row
                self.states = self.states.append({
                    "state": state.get('state_id'),
                    "reachable": state_reachable
                }, ignore_index=True)
                print(f"\t\t Added new state entry to the table.")

        print(self.states)
        return state_reachable

    # Takes two states as dictionaries and checks if that transition is already recognised, or has already been checked
    # If unrecognised, it passes the states to a method that checks them in SPIN
    # True means it was recognised, false means it was not.
    def check_transition(self, prev_state, next_state, thread_workspace):

        matching_transitions = ((self.transitions['previous_state'] == prev_state.get('state_id')) & 
                                (self.transitions['next_state'] == next_state.get('state_id')))

        # If transition is located in memoisation table
        if matching_transitions.any():
            # Get listed value of transition
            transition_value = self.transitions.loc[matching_transitions, 'valid']

            # If transition is in table but hasn't been checked, check it
            if transition_value.isna().any() or transition_value.empty:
                return self.spin_verify_transition(prev_state, next_state, thread_workspace)

            else:
                # Pull result from memoisation table
                return transition_value.values[0]
                
        else: 
            # If transition hasn't been verified previously, check it in SPIN
            return self.spin_verify_transition(prev_state, next_state, thread_workspace)

    # Returns true if a new state is searched */
    def check_state(self, state, thread_workspace):
        matching_state = (self.states['state'] == state.get('state_id'))

        # Check if state is located in memoisation table
        if matching_state.any():
            state_reachable = self.states.loc[matching_state, 'reachable']

            # If state is in table but hasn't been checked, check it
            if state_reachable.isna().any() or state_reachable.empty:
                return self.spin_verify_state(state, thread_workspace)
            else:
                # Pull result from memoisation table
                return state_reachable.values[0]

        else:
            # If state hasn't been verified previously, check it in SPIN
            return self.spin_verify_state(state, thread_workspace)


    # Outputs transitions state space using a set of labels
    # labels in dataframe of format: state(int),label(str)
    def generate_state_space_diagram(self):

        generate_dot.make_graph(self.transitions, self.states, self.labels)

    def print_problems(self):
        if self.state_errors > 0:
            print(f"Problem states:")
            for row in self.states.itertuples():
                if not row.reachable:
                    print(f"{row.state}:")
                    self.print_state(self.get_state_from_index(row.state))

        if self.transition_errors > 0:
            print(f"Problem transitions:")
            for row in self.transitions.itertuples():
                if not row.valid:
                    print("-----------------------------------------------------------------")
                    print(f"{row.previous_state} -> {row.next_state}")
                    print(f"{row.previous_state}:")
                    self.print_state(self.get_state_from_index(row.previous_state))
                    print(f"{row.next_state}:")
                    self.print_state(self.get_state_from_index(row.next_state))

    def spin_processor(self, thread_workspace):

        if not os.path.exists(thread_workspace):
            os.makedirs(thread_workspace)

        # Copy over spin model for thread to use locally
        shutil.copy(self.state_template_path,  f"{thread_workspace}/hydro_state_template.pml")
        shutil.copy(self.transition_template_path,  f"{thread_workspace}/hydro_transition_template.pml")

        if thread_workspace == "spin_models/thread_working_directory/thread_1":
            start_time = datetime.utcnow()
            total_jobs = spin_input.qsize()

        while not self.stop_threads.is_set():
            try:
                # Get data from the queue, waiting for data to be available
                task = spin_input.get()
                
                if thread_workspace == "spin_models/thread_working_directory/thread_1":
                    remaining_jobs = spin_input.qsize()
                    elapsed_time = datetime.utcnow() - start_time
                    jobs_completed = total_jobs - remaining_jobs
                    
                    # Calculate average job time
                    avg_job_time = elapsed_time / jobs_completed if jobs_completed > 0 else timedelta(0)

                    # Project the end time of the batch
                    projected_end_time = datetime.utcnow() + avg_job_time * remaining_jobs
                    
                    print(f"Thread 1 here! Me and my boys are averaging {avg_job_time.total_seconds()} seconds per job.")
                    print(f"I'm projecting that this batch will be done around {projected_end_time}. \nRemember: You've got this, you're ready!")
                    print(f"{spin_input.qsize()} processings remaining for task.")
                else:
                    print("Thread got data")
                    print(f"{spin_input.qsize()} tasks remaining for processing.")

                if task is None:
                    print("Spin processing thread received stop signal.")
                    spin_input.task_done()
                    break  # Exit the loop to terminate the thread
                else:
                    if task[0] == "state":
                        state = task[1]
                        state_result = self.check_state(self.get_state_from_index(state), thread_workspace)
                    elif task[0] == "both":
                        previous_state = task[1]
                        next_state = task[2]
                        prev_state_result = self.check_state(self.get_state_from_index(previous_state), thread_workspace)
                        new_state_result = self.check_state(self.get_state_from_index(next_state), thread_workspace)
                        transition_result = self.check_transition(self.get_state_from_index(previous_state), self.get_state_from_index(next_state), thread_workspace)
                    elif task[0] == "transition":
                        previous_state = task[1]
                        next_state = task[2]
                        transition_result = self.check_transition(self.get_state_from_index(previous_state), self.get_state_from_index(next_state), thread_workspace)
                    else:
                        print(f"Unrecognised task: {task[0]}")
                #print(f"SPIN Results: {state_result}")

            except Exception as e:
                print(f"Error processing data: {e}")

    # Test function
    def run(self, check_transitions, check_states, test_states, test_transitions):
        #states = self.load_states_csv("comprehensive_states.csv", "state_labels.csv")
        #self.labels = self.load_labels_csv("state_labels.csv")
        

        pd.set_option('display.max_colwidth', None)
        if check_transitions or check_states:

            self.transitions = self.load_transitions_csv("recorded_transitions_A&B.csv")

            spin_models_dir = Path.cwd() / "spin_models"
            # Copy over spin model for thread to use locally
            shutil.copy(self.state_template_path,  f"spin_models/hydro_state_template.pml")
            shutil.copy(self.transition_template_path,  f"spin_models/hydro_transition_template.pml")

            for transition in self.transitions.itertuples():
                if transition.previous_state == -1:
                    continue


                if check_transitions:
                    update = self.check_transition(self.get_state_from_index(transition.previous_state), self.get_state_from_index(transition.next_state), spin_models_dir)
                    if update:
                        print(self.transitions)
                if check_states:
                    check_state_1 = self.check_state(self.get_state_from_index(transition.previous_state), spin_models_dir)
                    check_state_2 = self.check_state(self.get_state_from_index(transition.next_state), spin_models_dir)
                    
                    if check_state_1 or check_state_2:
                        print(self.states)

            self.generate_state_space_diagram()
            print(f"\n\n--------------------------------------------------------------------------------\nSummary")
            print(f"\nStates:\n\t{len(self.states)-self.state_errors}/{len(self.states)} recognised states. \n\t{self.state_errors}/{len(self.states)} state errors.")
            print(f"{self.states}")
            print(f"\nTransitions:\n\t{len(self.transitions)-self.transition_errors}/{len(self.transitions)} valid transitions. \n\t{self.transition_errors}/{len(self.transitions)} transition errors.")
            print(f"{self.transitions}")
            self.print_problems()
    
        if test_states:
            files = ["evaluation_files/datasets/baseline_states.csv"]#,"test_states_1_step.csv", "test_states_2_steps.csv", "test_states_3_steps.csv", "test_states_4_steps.csv"]
            for file in files:
                spin_input.queue.clear()
                test_start = datetime.utcnow()

                # Create a set of states that are valid
                baseline_states = set()
                for transition in self.transitions.itertuples():
                    baseline_states.add(transition.previous_state)
                    baseline_states.add(transition.next_state)
                print(f'# Baseline states = {len(baseline_states)}')

                # Load set of test states from csv
                test_states = pd.read_csv(file)

                # Remove states that already appear in baseline states
                test_states_set = set(test_states["state"])
                remaining_states = test_states_set - baseline_states

                for state in remaining_states:
                    spin_input.put(("state", state))

                print(f'# Test states = {len(test_states)}')
                print(f'# Remaining states = {len(remaining_states)}')

                # Reinitialise states and transitions
                self.transitions = pd.DataFrame(columns=["previous_state", "next_state", "valid"])
                self.states = pd.DataFrame(columns=["state", "reachable"])

                #for index, row in test_states.iterrows():
                #    print(f'Checking #{index}/{len(test_states)}:')
                #    test_state = self.get_state_from_index(row["state"])
                #    # Check if test state to see if it is reachable, store result in table
                #    test_states.at[index, "reachable"] = self.check_state(test_state)

                # Set up worker threads
                spin_thread_1 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_1",), name="Thread 1")
                spin_thread_1.daemon = True  # Daemonize thread to close with main program

                spin_thread_2 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_2",), name="Thread 2")
                spin_thread_2.daemon = True  # Daemonize thread to close with main program

                spin_thread_3 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_3",), name="Thread 3")
                spin_thread_3.daemon = True  # Daemonize thread to close with main program

                spin_thread_4 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_4",), name="Thread 4")
                spin_thread_4.daemon = True  # Daemonize thread to close with main program

                spin_thread_5 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_5",), name="Thread 5")
                spin_thread_5.daemon = True  # Daemonize thread to close with main program

                spin_thread_6 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_6",), name="Thread 6")
                spin_thread_6.daemon = True  # Daemonize thread to close with main program

                threads = [spin_thread_1, spin_thread_2, spin_thread_3, spin_thread_4, spin_thread_5, spin_thread_6]
                # For each thread started add a terminating None to the processing list
                for t in threads:
                    t.start()
                    spin_input.put(None)

                try:
                    # Waits for threads to finish
                    for t in threads:
                        t.join()
                except KeyboardInterrupt:
                    print("\nInterrupt Recieved, shutting down threads...")
                    # Set the event to notify threads to stop
                    self.stop_threads.set()

                    # Ensure all threads have been stopped
                    for t in threads:
                        t.join()

                test_finish = datetime.utcnow()

                with open(f"{file}_results.txt", 'w') as output:
                    reachable_count = self.states["reachable"].sum()
                    content = f"Results: {reachable_count}/{len(self.states)} states tested were reachable.\nTest finished at {test_start}\nTest finished at {test_finish}\nTest took {test_finish-test_start}"
                    output.write(content)

                self.states.to_csv(f"{file}_states.csv", index=False)

                print(f"Evaluation of {file} complete.\n\n--------------------------------------------------------------------------------\n")

        if test_transitions:
            files = ["fn_2step.csv", "fn_1step.csv"]#["test_transitions_baseline_1step.csv", "test_transitions_1step_baseline.csv", "test_transitions_baseline_2step.csv", "test_transitions_2step_baseline.csv"]
            for file in files:
                spin_input.queue.clear()
                # Load set of test states from csv
                test_transitions = pd.read_csv(file)
                # Iterate over each row in the DataFrame
                for _, transition in test_transitions.iterrows():
                    # Access previous_state and next_state columns
                    spin_input.put(("transition", transition["previous_state"], transition["next_state"]))

                print(f"Queue size: {spin_input.qsize()}")
                test_start = datetime.utcnow()
                print(f'# Test transitions = {len(test_transitions)}')

                # Reinitialise states and transitions
                self.transitions = pd.DataFrame(columns=["previous_state", "next_state", "valid"])
                self.states = pd.DataFrame(columns=["state", "reachable"])

                #for index, row in test_states.iterrows():
                #    print(f'Checking #{index}/{len(test_states)}:')
                #    test_state = self.get_state_from_index(row["state"])
                #    # Check if test state to see if it is reachable, store result in table
                #    test_states.at[index, "reachable"] = self.check_state(test_state)

                # Set up worker threads
                spin_thread_1 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_1",), name="Thread 1")
                spin_thread_1.daemon = True  # Daemonize thread to close with main program

                spin_thread_2 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_2",), name="Thread 2")
                spin_thread_2.daemon = True  # Daemonize thread to close with main program

                spin_thread_3 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_3",), name="Thread 3")
                spin_thread_3.daemon = True  # Daemonize thread to close with main program

                spin_thread_4 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_4",), name="Thread 4")
                spin_thread_4.daemon = True  # Daemonize thread to close with main program

                spin_thread_5 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_5",), name="Thread 5")
                spin_thread_5.daemon = True  # Daemonize thread to close with main program

                spin_thread_6 = threading.Thread(target=self.spin_processor, args=("spin_models/thread_working_directory/thread_6",), name="Thread 6")
                spin_thread_6.daemon = True  # Daemonize thread to close with main program


                threads = [spin_thread_1, spin_thread_2, spin_thread_3, spin_thread_4, spin_thread_5, spin_thread_6]
                # For each thread started add a terminating None to the processing list
                for t in threads:
                    t.start()
                    spin_input.put(None)
                try:
                    # Waits for threads to finish
                    for t in threads:
                        t.join()
                except KeyboardInterrupt:
                    print("\nInterrupt Recieved, shutting down threads...")
                    # Set the event to notify threads to stop
                    self.stop_threads.set()

                    # Ensure all threads have been stopped
                    for t in threads:
                        t.join()

                test_finish = datetime.utcnow()

                with open(f"{file}_results.txt", 'w') as output:
                    valid_count = self.transitions["valid"].sum()
                    content = f"Results: {valid_count}/{len(self.transitions)} transitions tested were valid.\nTest finished at {test_start}\nTest finished at {test_finish}\nTest took {test_finish-test_start}"
                    output.write(content)

                self.transitions.to_csv(f"{file}_transitions.csv", index=False)

                print(f"Evaluation of {file} complete.\n\n--------------------------------------------------------------------------------\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser("SPIN Controller.")
    parser.add_argument("--check_transitions", dest='check_transitions', action='store_true', help="Run SPIN model to check transitions in 'recorded_transitions.csv' file.")
    parser.add_argument("--check_states", dest='check_states', action='store_true', help="Run SPIN model to check states in 'recorded_transitions.csv' file.")
    parser.add_argument("--test_states", dest='test_states', action='store_true', help="Check test_states.csv for false negatives")
    parser.add_argument("--test_transitions", dest="test_transitions", action="store_true", help="Check a list of transitions using multithreading")
    args = parser.parse_args()

    if args.test_states or args.test_transitions:
        spin_input = queue.Queue(maxsize=180000)

    controller = SpinController()
    controller.run(args.check_transitions, args.check_states, args.test_states, args.test_transitions)
