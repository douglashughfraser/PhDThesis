import pandas as pd
import os

def process_state_and_transition_files(state_files, transition_files, output_true_states, output_filtered_transitions):
    # Load and merge all state files
    all_states = pd.concat([pd.read_csv(file) for file in state_files], ignore_index=True)
    
    # Identify all true states (assuming the first column contains state values and true/false values)
    true_states = all_states[all_states.iloc[:, 0] == True]
    true_states.to_csv(output_true_states, index=False)
    
    # Load and merge all transition files
    all_transitions = pd.concat([pd.read_csv(file) for file in transition_files], ignore_index=True)
    
    # Filter transitions where previous_state is in true_states and valid == True
    filtered_transitions = all_transitions[
        (all_transitions['previous_state'].isin(true_states.iloc[:, 0])) &
        (all_transitions['valid'] == True)
    ]
    
    # Save the filtered transitions
    filtered_transitions.to_csv(output_filtered_transitions, index=False)
    
    print(f"True states saved to: {output_true_states}")
    print(f"Filtered transitions saved to: {output_filtered_transitions}")

if __name__ == "__main__":
    # Define file paths
    state_files = [
        'test_states_1_step.csv_states.csv',
        'test_states_2_steps.csv_states.csv',
        'test_states_3_steps.csv_states.csv',
        'test_states_4_steps.csv_states.csv'
    ]

    transition_files = [
        'test_transitions_1step_baseline.csv_transitions.csv',
        'test_transitions_2step_baseline.csv_transitions.csv',
        'test_transitions_baseline_1step.csv_transitions.csv',
        'test_transitions_baseline_2step.csv_transitions.csv',
        'test_transitions_false_negative.csv_transitions.csv'
    ]

    output_true_states = 'true_states.csv'
    output_filtered_transitions = 'filtered_transitions.csv'
    
    process_state_and_transition_files(state_files, transition_files, output_true_states, output_filtered_transitions)
