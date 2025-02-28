from price_simulator import PriceSimulator
from spin_controller import SpinController
import threading
import queue
import os
from datetime import datetime, timedelta
import pytz
import time
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from influxdb_client import InfluxDBClient, Point
import shutil

class StateNotFoundException(Exception):
    def __init__(self, Exception):
        print(Exception)

class InvalidTransitionException(Exception):
    def __init__(self, Exception):
        print(Exception)
    
class UnresponsiveDeviceException(Exception):
    def __init__(self, Exception):
        print(Exception)
    
def load_states_csv(states_path, labels_path):

    # Read the CSV file into a pandas DataFrame
    states = pd.read_csv(states_path)
    labels = pd.read_csv(labels_path)
    
    states = states.merge(labels, how='left', left_index=True, right_on='state_id')

    print(f'Loaded {len(states)} states from path: {states_path}')
    return states

def load_labels_csv(labels_path):

        # Read the CSV file into a pandas DataFrame
        labels = pd.read_csv(labels_path)

        print(f'Loaded {len(labels)} states from path: {labels_path}')
        return labels

def load_transitions_csv(transitions_path):

    if not os.path.exists(transitions_path):
        print(f"The file '{transitions_path}' does not exist. \n\tProceeding with empty transition file.")    
        transitions = pd.DataFrame(columns=["previous_state", "new_state", "valid"])
    else:
        # Read the CSV file into a pandas DataFrame
        transitions = pd.read_csv(transitions_path)

        print(f'Loaded {len(transitions)} transitions from path: {transitions_path}')
        print(transitions)
    return transitions
    
def generateHydroControlQuery(query_period):
    control_fields_to_query = [
        "Flood_Gate_Valve",
        "Flood_Pump",
        "Sump_Valve",
        "Sump_Pump_1",
        "Sump_Pump_2",
        "Activated_Flood_Control",
        "Gen_A_Status",
        "Gen_B_Status",
        "Return_Water_Supply_Control",
        "Supply_Water_Level",
        "Tag_2",
        "HMI_Return_Feed"
    ]

    # Join fields together before insertion into query
    control_fields_query = ""

    for index in range(len(control_fields_to_query)):
        control_fields_query += f'r["_field"] == "{control_fields_to_query[index]}"'
        if index < len(control_fields_to_query) - 1:
            control_fields_query += ' or '
            
    hydro_control_query = f'from(bucket:"{bucket}") |> range(start: -{query_period}s)' \
            '|> filter(fn: (r) => r["_measurement"] == "HydroControl") ' \
            f'|> filter(fn: (r) => {control_fields_query})' \
            '|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'

    return hydro_control_query

def generateHydroGeneratorQuery(query_period):
    generator_fields_to_query = [
        "Gen_A_Active",
        "Gen_A_Fan",
        "Gen_A_Pump",
        "Gen_A_Valve",
        "Gen_A_Temp",
        "GenA_Temper_Scale",
        "Gen_A_Volt",
        "Gen_A_GreenLED",
        "Gen_A_RedLED",
        "Gen_B_Active",
        "Gen_B_Fan",
        "Gen_B_Pump",
        "Gen_B_Valve",
        "Gen_B_Temp",
        "Gen_B_Temper_Scale",
        "Gen_B_Volt",
        "Gen_B_GreenLED",
        "Gen_B_RedLED",
        "Supply_Water_Level_Round"
    ]

    # Join fields together before insertion into query
    generator_fields_query = ""

    for index in range(len(generator_fields_to_query)):
        generator_fields_query += f'r["_field"] == "{generator_fields_to_query[index]}"'
        if index < len(generator_fields_to_query) - 1:
            generator_fields_query += ' or '
            
    hydro_generator_query = f'from(bucket:"{bucket}") |> range(start: -{query_period}s)' \
            '|> filter(fn: (r) => r["_measurement"] == "HydroGenerator") ' \
            f'|> filter(fn: (r) => {generator_fields_query})' \
            '|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'
            
    return hydro_generator_query
    
# Returns a dataframe containing the queried data.
def queryInfluxDB(client, query):
    return client.query_api().query_data_frame(query)

def getPLCData(client, hydro_control_query, hydro_generator_query):
    # Execute the query
    control_result = queryInfluxDB(client, hydro_control_query)
    generator_result = queryInfluxDB(client, hydro_generator_query)
    
    # Gather and parse device data:
    #   - Check if new data received, if no data is received for 10 seconds raise exception.
    #   - Convert string timestamps into datetime objects, record time of most recent result
    #   - Drop "_time" field to prepare for merging datasets
    
    # Check for new device data
    if not control_result.empty:
        # Format and store new data.
        control_result['_time_control'] = pd.to_datetime(control_result['_time']).dt.tz_convert('Europe/London')
        last_control_result = control_result.sort_values(by=['_time_control'], ascending=False).iloc[0]['_time_control']
        control_result.drop('_time', axis=1)
        
        control_data = control_result
    else: 
        control_data = pd.DataFrame()
        print("Missing data for HydroControl PLC.")

    # Check for new device data
    if not generator_result.empty:
        # Format and store new data.
        generator_result['_time_generator'] = pd.to_datetime(generator_result['_time']).dt.tz_convert('Europe/London')
        last_generator_result = generator_result.sort_values(by=['_time_generator'], ascending=False).iloc[0]['_time_generator']
        generator_result.drop('_time', axis=1)
        
        generator_data = generator_result

    else: 
        generator_data = pd.DataFrame()
        print("Missing data for HydroGenerator PLC.")

    return control_data, generator_data

def score(record):
    sync_score = abs(record['_time_control'] - record['_time_generator']).total_seconds()
    
    freshness_score = abs(datetime.now(tz=pytz.timezone('Europe/London')) - min(record['_time_control'], record['_time_generator'])).total_seconds()
    
    return 2 * sync_score + freshness_score
        
def sync_device_results(control, generator):

    # Compare most recent readings from each device, join on older of the two.
    # merge_asof left joins with the nearest reading from the right dataframe.
    if control.iloc[0]["_time_control"] < generator.iloc[0]["_time_generator"]:
            state = pd.merge_asof(control, generator, left_on='_time_control', right_on='_time_generator', direction='nearest')
    else:
            state = pd.merge_asof(generator, control, left_on='_time_generator', right_on='_time_control', direction='nearest')
    
    # Assign each entry from the time interval a score to select the best one to use.
    state['_score'] = state.apply(score, axis=1)

    synchronised_state = state.sort_values(by='_score', ascending=True).iloc[0]

    # Voltage output of the generator defaults to ~65000mV when 
    if synchronised_state["Gen_A_Volt"] > 65000: 
        synchronised_state["Gen_A_Volt"] = 0
    if synchronised_state["Gen_B_Volt"] > 65000: 
        synchronised_state["Gen_B_Volt"] = 0
    
    # Sort the entries by score in descending order, return highest scoring entry.
    return synchronised_state

def identify_state(states, system_state):
    try:
        #print(f'System state: \n{system_state}')
    
        # Build the query for the dataframe of states
        query_conditions = ""
        for col in system_state.index:
            # Only add queries for states in the known state space
            if col in states.columns:
                if query_conditions == "":
                    query_conditions += f'{col} == {system_state[col]}'
                else:
                    query_conditions += f' & {col} == {system_state[col]}'

        # Execute the query
        query_results = states.query(query_conditions)

        identified_state = query_results.iloc[0]["state_id"].astype(int)
        
        # If no or multiple rows are found, raise an exception
        if query_results.empty:
            raise StateNotFoundException(f"State with tags {current_state} not uniquely identified in the DataFrame.")

    except StateNotFoundException as e:
        # Handle the case where no states are found
        raise e

    return identified_state

# Convert a row of boolean values to an integer, treating each column as a bit in a binary number.
# Takes a row of boolean state data as input and returns an integer representation.
def derive_state_index(system_state):

    # Convert the boolean values to integers (0 or 1), join them into a binary string, then convert to an integer.
    binary_string = ''.join(str(int(val)) for val in system_state[
        ['Flood_Gate_Valve',
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
        'HMI_Return_Feed']
    ].astype(int))
    
    # Convert the binary string to an integer
    return int(binary_string, 2)

def predict_transition(transitions, current_state):
    
    # Look up all transitions that are expected to occur out of the current state.
    expected_transitions = transitions[(transitions['previous_state'] == current_state)]
    
    # Extract the transition states form that list
    future_states = expected_transitions['new_state'].tolist()
    
    #print(f'Expected future states:\t{future_states}')
    
    return future_states

def record_transition(previous_state_index, new_state_index):
    print(transitions)
    if transitions.empty or (transitions.loc[(transitions["previous_state"] == previous_state_index) & (transitions["new_state"] == new_state_index)].empty):
        #if not ((transitions['previous_state'] == previous_state) & transitions['new_state'] == new_state | transitions.isna()).all(axis=1).any():
        print(f'Transition {previous_state_index} -> {new_state_index} recorded.')
        transitions = transitions.append({'previous_state':previous_state_index, 'new_state':new_state_index}, ignore_index=True)
    else:
        print(f'Transition {previous_state_index} -> {new_state_index} already seen.')
        
    print(f'Writing {len(transitions)} transitions to csv.')
    transitions.to_csv('recorded_transitions.csv', index=False)

def validate_transition(transitions, previous_state_index, new_state_index):

    if new_state_index in transitions.query(f'previous_state == {previous_state_index}').loc[:,"new_state"].tolist():
        print(f'Valid transition:\t{previous_state_index} -> {new_state_index}')
        return True
    else:
        raise InvalidTransitionException(f'Invalid transition:\t{previous_state_index} -> {new_state_index}')

def spin_processor(thread_workspace):
    if not os.path.exists(thread_workspace):
        os.makedirs(thread_workspace)

    transition_template_path = "C:/Users/dfraser/Documents/SpinHydro/transition models/updated models/noloop_hydro_cc_template.pml"
    state_template_path = "C:/Users/dfraser/Documents/SpinHydro/state space models/hydro_state_template.pml"


    # Copy over spin model for thread to use locally
    shutil.copy(state_template_path,  f"{thread_workspace}/hydro_state_template.pml")
    shutil.copy(transition_template_path,  f"{thread_workspace}/hydro_transition_template.pml")

    while True:
        try:
            # Get data from the queue, waiting for data to be available
            transition = spin_input.get()
            print("New data received by SPIN worker")
            # Check if it's the stop signal
            if transition is None:
                print("Spin processing thread received stop signal.")
                spin_input.task_done()
                break  # Exit the loop to terminate the thread

            # Process data with SpinController
            prev_state_result = spin_controller.check_state(transition["previous_state"], thread_workspace)
            new_state_result = spin_controller.check_state(transition["next_state"], thread_workspace)
            transition_result = spin_controller.check_transition(transition["previous_state"], transition["next_state"], thread_workspace)

            print(f"\nSPIN Results: {prev_state_result} ---{transition_result}---> {new_state_result}")

        except Exception as e:
            print(f"Error processing data: {e}")

def transition_handler(previous_state, new_state):

    print("Transition handler called")
    if previous_state is None:
        return None
    else:
        if using_spin:
            print("Transition handler using spin")
            if type(previous_state) is pd.DataFrame:
                print("Transition handler converted previous state")
                previous_state = previous_state.to_dict('index').get(0)

            if type(new_state) is pd.DataFrame:
                new_state = new_state.to_dict('index').get(0)

            print("TH Putting data")
            spin_input.put({
                "previous_state": previous_state,
                "next_state": new_state
            })
        else:
            try: 
                validate_transition(transitions, previous_state["state_id"], new_state["state_id"])
            except InvalidTransitionException as e:
                if args.recording:
                    print(f'New Transition!\t\t{previous_state["state_id"]} -> {new_state["state_id"]} Recorded.')
                    record_transition(transitions, previous_state["state_id"], new_state["state_id"])
                else:
                    raise e

def write_to_influx(influx_fields):
    # Empty dictionary is false -> if something has been added, write it to influx
    if influx_fields:

        print(f"Writing data to influx: {influx_fields}")

        influx_dictionary = {
            "measurement": "DT",
            "tags": {},
            "fields": influx_fields,
            "time": 1
        }
        
        # Note that utcnow is being used rather than the simulator time.
        # To allow grafana to synchronise the times as the PLCs are writing data using utc now too.
        flux_point = Point.from_dict(flux_dictionary).time(datetime.utcnow())

        # Write the computed results back to InfluxDB
        client.write_api().write(bucket=bucket, org=org, record=flux_point, data_frame_measurement_name="DT_Output")
        
    influx_fields = None

def main():
    print("------------------- Entering Simulation Loop  -------------------")

    last_control_result = datetime.now()
    last_generator_result = datetime.now()

    if energy_sim:
        production_data = pd.DataFrame()
        sim_start_time = price_simulator.start_simulation()
        sim_time = price_simulator.get_sim_time()
        sim_price = price_simulator.get_sim_price(sim_time)
        sim_end_time = sim_start_time + timedelta(hours=args.duration)
        failed_queries = 0
    else:
        sim_start_time = datetime.now()
        sim_time = datetime.now()
        sim_end_time = sim_start_time - timedelta(hours=1)

    loops = 0
    failed_queries = 0
    previous_state = None
    influx_fields = {}
    first_state = True

    try:
        while (sim_time < sim_end_time or args.loop_sim) or (not energy_sim and loops < 200):

            print("-----------------------------------------------------------------")
            control_data, generator_data = getPLCData(client, hydro_control_query, hydro_generator_query)
            
            # Check that data has been received, either now or previously, from both devices before proceeding.
            if not (control_data.empty or generator_data.empty):
                failed_queries = 0
                print("New data received from both PLCs.")
            elif failed_queries > 10:
                if control_data.empty:
                    raise UnresponsiveDeviceException("Lost connection to HydroControl PLC.")
                if generator_data.empty:
                    raise UnresponsiveDeviceException("Lost connection to HydroGenerator PLC.")

            # Check if either control or generator data is empty then we have never recieved data from those devices.
            # Therefore we must skip the rest of processing part of the loop and attempt to return to the query step.
            if control_data.empty or generator_data.empty:
                
                # Flip first state after first pass
                if first_state:
                    first_state = False

                # Wait.
                time.sleep(time_interval)
                
                if energy_sim:
                    # Retrieve simulation time to determine if another loop is needed
                    sim_time = price_simulator.get_sim_time()
                else:
                    loops+=1
                continue

            # Synchronises the states of the devices, ranks them according to freshness and synchronicity and chooses the best.
            # System state is returned as a row from that dataframe consisting of data from both devices along with timestamps.
            
            system_state = sync_device_results(control_data, generator_data)

            # --- Processing system state starts here---

            # Identify state index from valuation of variables
            identified_state = derive_state_index(system_state)
            system_state["state_id"] = identified_state
                
            # Find the label for the current state and store it in frame too
            if not labels.loc[labels["state_id"] == identified_state]["label"].empty:
                system_state["label"] = labels.loc[labels["state_id"] == identified_state]["label"].iloc[0]
            else:
                system_state["label"] = "No label known."
            
            print(
                f"System state:\t\t{system_state['state_id']}\t{system_state['label']}\n"
                f"System variables:\n\tGen_A_Temp: {system_state['Gen_A_Temp']}\n"
                f"\tGenA_Temper_Scale: {system_state['GenA_Temper_Scale']}\n"
                f"\tSupply_Water_Level: {system_state['Supply_Water_Level']}\n"
                f"\tSupply_Water_Level_Round: {system_state['Supply_Water_Level_Round']}"
            )

            # If monitoring system transitions pass previous and current state to be processed.
            # From there they will either be checked against a recognised transition table or
            # if using Spin, passed to a thread to be checked in the Spin model checker.
            transition_handler(previous_state, system_state)
                
            if energy_sim:
                sim_price = price_simulator.get_sim_price(sim_time)
                system_state["sim_time"] = sim_time
                print(f'Simulation Time:\t{sim_time}')
                print(f'Simulation Price:\t{sim_price}p/kWh')

                # Initialise production values
                Energy_Generated = 0.0
                Energy_Usage = 0.0
                Production_Costs = 0.0
                Production_Income = 0.0

                
                # Run energy calculations if simulating usage
                if energy_sim and not previous_state is None:
                    # If the generator is running in this state and was running in the last state, calculate how much energy has been generated during that time.
                    # Formula is: sim_window_length in hours * (average of two generator voltage readings /1000 to convert mV reading to V) / 1000 to convert to kWh * Amperage of the generator (220mA) / 1000 to convert Wh to kWh
                    if system_state["Gen_A_Active"] == 1.0 and previous_state["Gen_A_Active"] == 1.0:
                        Energy_Generated = float((((system_state["sim_time"] - previous_state["sim_time"]).seconds/3600) * (((previous_state["Gen_A_Volt"] + system_state["Gen_A_Volt"])/1000)/2)*0.22)/1000)
                        Production_Income = Energy_Generated * sim_price
                        print(f'Energy_Generated: {Energy_Generated} = {(system_state["sim_time"] - previous_state["sim_time"]).seconds/3600} * ((({previous_state["Gen_A_Volt"]} + {system_state["Gen_A_Volt"]})/1000)/2) * 0.22 / 1000')
                        
                    # If the sump pumps have been running for a whole cycle, calculate how much energy has been used during that time.
                    # Formula is: sim_window_length in hours * (sum of two pump wattage readings) / 1000 to convert to kWh
                    if (system_state["Sump_Pump_1"] == 1.0 and previous_state["Sump_Pump_1"] == 1.0) and (system_state["Sump_Pump_2"] == 1.0 and previous_state["Sump_Pump_2"] == 1.0):
                        Energy_Usage = float((system_state["sim_time"] - previous_state["sim_time"]).seconds/3600) * (Sump_Pump_1_Wattage + Sump_Pump_2_Wattage)/1000
                        print(f'Energy Usage: {Energy_Usage} = {(system_state["sim_time"] - previous_state["sim_time"]).seconds/3600} * ({Sump_Pump_1_Wattage} + {Sump_Pump_2_Wattage})/1000')
                        Production_Costs = Energy_Usage * sim_price
                    
                    production_data = production_data.append({  "Time": system_state["sim_time"],
                                                        "Energy_Generated": Energy_Generated,
                                                        "Energy_Usage": Energy_Usage,
                                                        "Electric_Price": sim_price,
                                                        "Production_Income": Production_Income,
                                                        "Production_Costs": Production_Costs}, ignore_index=True)

            # Predictions for future states and outcomes
            # Skip if transition file is not complete
            if not args.recording:
                future_states = predict_transition(transitions, system_state["state_id"])

                if len(future_states) > 0:
                    print('Expected futures states:')
                    for i, state in enumerate(future_states):
                        print(f'\t\t\t{state}:\t\t{states.iloc[state]["label"]}')
                        
                        # Add data to flux datapoint, appears in format future_state_<index>
                        influx_fields[f'future_state_{i}'] = state

                                    # Write data if data has been added to the output point
           
            # Write any flux_field data to influx database           
            write_to_influx(influx_fields)

            # End loop, save state for next cycle.
            previous_state = system_state
            
            # Wait.
            time.sleep(time_interval)
            
            if energy_sim:
                # Retrieve simulation time to determine if another loop is needed
                sim_time = price_simulator.get_sim_time()
            else:
                loops+=1

    except KeyboardInterrupt:
        print("\n-----------------------------------------------------------------\n\nMain method received exit signal. Terminating...")

    finally:
        # Send stop signal to the consumer thread
        print(f"\n-----------------------------------------------------------------")
        print(f"|                     - Execution Summary -                     |")
        print(f"-----------------------------------------------------------------")


        if using_spin:
            spin_input.put(None)  # Use None as a stop signal
            spin_input.put(None)  # Use None as a stop signal
            spin_input.put(None)  # Use None as a stop signal
            spin_input.put(None)  # Use None as a stop signal

            # Wait for the spin threads to finish
            spin_thread_1.join()
            spin_thread_2.join()
            spin_thread_3.join()
            spin_thread_4.join()

            spin_controller.generate_state_space_diagram()
            print(f"\nStates:\n\t{len(spin_controller.states)-spin_controller.state_errors}/{len(spin_controller.states)} recognised states. \n\t{spin_controller.state_errors}/{len(spin_controller.states)} state errors.")
            print(f"{spin_controller.states}")
            print(f"\nTransitions:\n\t{len(spin_controller.transitions)-spin_controller.transition_errors}/{len(spin_controller.transitions)} valid transitions. \n\t{spin_controller.transition_errors}/{len(spin_controller.transitions)} transition errors.")
            print(f"{spin_controller.transitions}")
            spin_controller.print_problems()


        print("Main method and spin thread have terminated.")

    print("Operation complete.")
    print(f'Writing {len(transitions)} transitions to csv.')
    transitions.to_csv('recorded_transitions.csv', index=False)
    if energy_sim:
        production_data.to_csv('production_data.csv', index=False)
        print(f'Production stats:\n {production_data}')
        print(f'Production Report: \n\tTotal Generated:\t {production_data["Energy_Generated"].sum()}kWh\n\tTotal Income:\t£{production_data["Production_Income"].sum()}\n\tTotal Usage:\t {production_data["Energy_Usage"].sum()}kWh\n\tTotal Costs:\t£{production_data["Production_Costs"].sum()}')

    print('Write successful.')


    if energy_sim:
        fig, (energy_graph, income_graph) = plt.subplots(2, 1, figsize=(10, 8))

        # Plot energy usage and energy generation over time on the first graph
        energy_graph.plot(production_data['Time'], production_data['Energy_Usage'], label='Energy Usage', color='b')
        energy_graph.plot(production_data['Time'], production_data['Energy_Generated'], label='Energy Generated', color='g')
        energy_graph.set_xlabel('Time')
        energy_graph.set_ylabel('Energy (kWh)')
        energy_graph.set_title('Energy Generated and Used Through Production Over Time')
        energy_graph.legend()  # Show the legend for the plot

        # Plot production costs and production income over time on the second graph
        income_graph.plot(production_data['Time'], production_data['Electric_Price'], label='Wholesale Electric Price', color='c')
        income_graph.plot(production_data['Time'], production_data['Production_Costs'], label='Production Costs', color='r')
        income_graph.plot(production_data['Time'], production_data['Production_Income'], label='Production Income', color='g')
        income_graph.set_xlabel('Time')
        income_graph.set_ylabel('Cost/Income (£/h)')
        income_graph.set_title('Production Income and Costs Over Time')
        income_graph.legend()  # Show the legend for the plot

        # Ensure the layout is adjusted to avoid overlapping titles or labels
        plt.tight_layout()

        # Show the plots
        plt.show()

parser = argparse.ArgumentParser("Hydroelectric Digital Twin")
parser.add_argument("--refresh_rate", dest='time_interval', help="Float(in seconds) duration between DT state refreshes.", default=0.5, type=float)
parser.add_argument("--duration", dest='duration', help="An integer number of hours to simulate price data for.", choices=range(12, 49, 12), default=24, type=int)
parser.add_argument("--transitions_file", dest='transitions_file', help="Location of transition .csv file relative to the local directory.", default='recorded_transitions.csv', type=str)
#parser.add_argument("--states_file", dest='states', help="Location of states .csv file relative to local directory.", default='comprehensive_states.csv', type=str)
parser.add_argument("--labels_file", dest='labels', help="Location of state labels .csv file relative to local directory.", default='state_labels.csv', type=str)
parser.add_argument("--loop", dest='loop_sim', action='store_true', help="Loop simulation prices over the same duration for continuous operation.")
parser.add_argument("--nosim", dest='energy_sim', action='store_false', help="Deactivate energy simulation components.")
parser.add_argument("--recording", dest='recording', action='store_true', help="For recording a new transition file.")
parser.add_argument("--nospin", dest='spin', action='store_false', help="Use Spin model checker.")
args = parser.parse_args()

# Enforce minimum refresh rate
if args.time_interval < 0.3:
    print(f"Refresh_rate of {args.time_interval} too low, instead set to minumum value of 0.3s.")
    time_interval = 0.3
else:
    time_interval = args.time_interval

print("------------------- Initialising Digital Twin -------------------")
#states = load_states_csv(args.states, args.labels)
labels = load_labels_csv(args.labels)
transitions = load_transitions_csv(args.transitions_file)
using_spin = args.spin
energy_sim = args.energy_sim

query_period = 1 # Age of data to query for (seconds)
Sump_Pump_1_Wattage = 22
Sump_Pump_2_Wattage = 26.4

# InfluxDB parameters
org = "GreensInc."
bucket = "GreensTestBed"
# InfluxDB connection settings
url = "http://localhost:8086"
#token = "0IWY99dmmbbfPJvreFJPKOndNzNdejg5ggTxawTsXZSyqXO-QJvzoMdTd6TnnNHvPG_xksZ4oV24OhTExd_6vQ==" #MAC
token = "lXje00JvzVczuk9ExcMXNBSb75_QA-lFYQ4X0eYyYNQIxxJFletfet0jTaPReXL5b0qJTmNeBjyVc_qeP5pkBQ==" #ICS

hydro_control_query = generateHydroControlQuery(query_period)
hydro_generator_query = generateHydroGeneratorQuery(query_period)

# Initialize InfluxDB client
client = InfluxDBClient(url=url, token=token, org=org)

print("Connected to InfluxDB")

if energy_sim:
    print("Loading price simulation data.")

    price_simulator = PriceSimulator("electric_prices_26_3_2024.csv", 1400, args.duration, args.loop_sim)

if using_spin:
    # Queue of data to be processed by spin
    spin_input = queue.Queue(maxsize=100)
    spin_controller = SpinController()
else:
    spin_controller = None 

print("------------------- Initialisation Complete   -------------------")

# Start the consumer threads
spin_thread_1 = threading.Thread(target=spin_processor, name="Thread 1", kwargs={"thread_workspace":"spin_models/thread_working_directory/thread_1"})
spin_thread_1.daemon = True  # Daemonize thread to close with main program

spin_thread_2 = threading.Thread(target=spin_processor, name="Thread 2", kwargs={"thread_workspace":"spin_models/thread_working_directory/thread_2"})
spin_thread_2.daemon = True  # Daemonize thread to close with main program

spin_thread_3 = threading.Thread(target=spin_processor, name="Thread 3", kwargs={"thread_workspace":"spin_models/thread_working_directory/thread_3"})
spin_thread_3.daemon = True  # Daemonize thread to close with main program

spin_thread_4 = threading.Thread(target=spin_processor, name="Thread 4", kwargs={"thread_workspace":"spin_models/thread_working_directory/thread_4"})
spin_thread_4.daemon = True  # Daemonize thread to close with main program


spin_thread_1.start()
spin_thread_2.start()
spin_thread_3.start()
spin_thread_4.start()

if __name__ == "__main__":
    main()