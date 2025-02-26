# Chapter 6: Alloy Models
This folder contains the Alloy models from Chapter 6.

## 6.3_InitialNetworkModelling
Contains models intended to be run in Alloy 5. They document the progression of the initial models used to develop the modelling approaches used in the later sections:

0. A simple introduction: devices connected with channels.
1. Data added to the devices.
2. Introduction of compromised devices. They start with some malicious data that they share through the network to compromise other devices.
3. Expansion of device compromise rules. Compromised devices tamper with other data that they interact with. This created a motivation to refine data representation to modify this behaviour.
4. Refinement of data representation. The Data signature has a location relation, separate from devices that have interacted with it, to document the device in the network that is currently interacting with that data.
5. Reintegrating the compromised devices and malicious data from 2 and 3 to confirm that the added features of 4 behaviour as intended.

These models won't run in Alloy 6 due to their usage of s' signifying "the next state in the ordering". This practice was officially integrated into the Alloy language in Alloy 6, making it a reserved character and causing an error.

## 6.4_StateTransitionModel
Two files containing the same underlying model with different properties and initial constraints to demonstrate the two attacks presented in 6.4. These models are a direct result of reimplementing the techniques developed in *6.3_InitialNetworkModelling* within Alloy 6. In addition, extra features for Device signatures were added, specifically; Attacker, PLC, Switch, DigitalTwin, Packet and Topology. Note that Packet was later renamed to Message for consistency with 6.7.

## 6.7_HydroelectricModel
Written in Alloy 6 this model expands numerous aspects of the model to examine how an attacker can interfere with the the values of Data being moved across the digital thread in a hydroelectric dam testbed. Data contains tag-value pairs that represent data association that each device along the digital thread receives. Instances of each signature are shown to represent the different components within the developed hydroelectric dam and its connected digital twin infrastructure. A threat model is shown that models an attacker that is able to perform a sequence of Actions to infiltrate the network and undermine it. This extensible action framework is implemented with NetworkScan and ExploitUserCredentials actions to demonstrate the approach. 

The different attacks were identified by modifying the configuration of the *threat_model* predicate (line 629) to vary the starting information that the Threat actor has, it does not constrain the set of reachable states. It is often best to start with a restrictive number of Actions and increase it in order to find the most realistic attack sequences. 

Additionally security measures are integrated through predicates that can be used. The DMZ and Segmentation predicates specify the different types of network segmentation that were specified in the chapter (lines 566 and 596 respectively). The password management restrictions are also shown (on line 607). To use these simply add or remove them from the *configuration* fact on line 655 then check *disrupt_thread* (under "Execute" in the toolbar) to search for instances where the attacker is able to interfere with the transmission of data between the PLCs and DT model. 

The *performance_eval* check that was used to assess the search times of the model is also provided. It constains a target of all of the devices in the network being taken control of by the attacker. Since this is unachievable without a very large number of actions Alloy searches the whole state spaces before terminating. These searches were executed with an instantiable Device signature to allow extra devices to be added to the network.