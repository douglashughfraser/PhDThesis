import pandas as pd

# Convert an integer to a dictionary of boolean values for the given keys names.
def get_state_from_index(state_int):

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
    binary_string = format(state_int, f'0{num_bits}b')
    
    # Make state into a dictionary, convert to dataframe
    state_dict = {keys[i]: bool(int(str_bit)) for i, str_bit in enumerate(binary_string)}
    state_dict["state_id"] = state_int
    return state_dict

def generate_label(d):

    # Helper function
    def get_value(state, key):
        value = state.get(key)

        if type(value) == bool:
            return int(value)
        if value == None:
            return "VALUE NOT FOUND"

    label = (f"Generator A:(Active:{get_value(d, 'Gen_A_Active')}; Status:{get_value(d, 'Gen_A_Status')})\n"
             f"Generator B:(Active:{get_value(d, 'Gen_B_Active')}; Status:{get_value(d, 'Gen_B_Status')})\n"
             f"Return feed: {get_value(d, 'Sump_Valve')}  Manual Return: {get_value(d, 'HMI_Return_Feed')}")

    return label

def create_states(states, labels):
    graph_nodes = []

    for row in states.itertuples():
        matched_label_entry = (labels['state_id'] == row.state)

        label = generate_label(get_state_from_index(row.state))

        if label=="":
            if row.reachable:
                graph_nodes.append(f"\ts{row.state} [color = \"green\", label=\"{row.state}\"]")
            else:
                graph_nodes.append(f"\ts{row.state} [color = \"red\", label=\"{row.state}\"]")
        else:
            if row.reachable:
                graph_nodes.append(f"\ts{row.state} [color = \"green\", label=\"{row.state}\n{label}\"]")
            else:
                graph_nodes.append(f"\ts{row.state} [color = \"red\", label=\"{row.state}\n{label}\"]")

    return graph_nodes

def process_transition(transition):
    str = f"\ts{transition.previous_state} -> s{transition.next_state}"
    print(transition)
    if transition.valid:
        str += "[color = \"green\"]"
    else:
        str += "[color = \"red\"]"

    return str

def create_transitions(transitions):
    transitions_write = []

    for transition in transitions.itertuples():
        transitions_write.append(process_transition(transition))

    return transitions_write

def make_graph(transitions, state_reachabilities, labels):
    file_output = "dot_graph.dot"

    file_data = "digraph G {\n\t  node [shape=rectangle];\n"

    states = create_states(state_reachabilities, labels)
    transitions_data = create_transitions(transitions)

    # Add states and transitions to graph and close graph
    file_data += "\n".join(states) + "\n" + "\n".join(transitions_data) + "\n}"

    with open(file_output, 'w') as file:
        file.write(file_data)