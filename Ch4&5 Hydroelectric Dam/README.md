# Hydroelectric Dam Case Study

This folder contains the files required to connect with the InfluxDB historian, synchronise that data and perform anomaly detection using SPIN.

*main.py* performs the main operation loop. It establishes the connection to InfluxDB and repeatedly loops pulling that data. Within it it performs all of the synchronising of state data into a state identifier that encodes all of the state data. This state id, and the state id of the previous state are pushed to a queue of worker threads for processing using the code in *spin_controller.py*. Note that this file also contains additional functionality to approximate the running costs and production profits of the dam during execution, this is the reason for the inclusion of the *electric_prices_26_3_2024.csv* and *price_simulator.py* files.

*spin_controller* contains all the code used to embed the observed state data into the Promela model templates to create instances of the Promela model that can be analysed by SPIN. It also contains all of the code used to perform the iterative evaluation of the test states and test transitions.

*generator_dot.py* is used to generate a dot graph of the different observed states and the transitions between them at the end of a spin_controller evaluation.

*recorded_transitions_A&B.csv* contains the IDs of the states and transitions observed during normal operation of the dam. It was used to construct our evaluation baseline.

*/evaluation_files* contains the different datasets that were used to perform the evaluation, along with the results of performing that evaluation.

*/helper_scripts* is a set of scripts used to fascillitate the analysis of the evaluation results.

*/spin_models* contains all the models created in Chapter 5. Within the templates folder are the trunk and branch model templates along with examples of instantiated models of both. */thread_working_directory* contains examples of the working directories for the six worker threads where the instantiated models are created and analysed before their output is returned to *main.py*.
