open util/ordering[State]

/*
This version splits the knowledge of a piece of data from the location of that data being transmitted within the network. 

Motivation:
Needed modelling of the modification of data as it moves through the network.

A compromised device cannot be modelled to change a trusted piece of data to a malcious one if all of the devices which have seen
that data will immediately become compromised by changing it's label to malicious.

*/
sig Data {}
sig Device {}

sig State {
	// A device has least one connection
	channel: set Device -> set Device,

	// In each state a piece of data can exist in one location
	// Trying an approach more in line with the stored data and channel approach
	data_at: set Device -> set Data,

	// The set of data that a device retains knowledge about
	stored_data: set Device -> set Data,

	attacker: set Device,
	compromised: set Device,
	malicious: set Data
}{
	all d: Device | d not in d.channel // Devices do not have channels directly to themselves.
	all d, d': Device | d' in d.^channel // Every device has a (indirect) communication channel to every other device.

	no attacker & compromised

	// All devices holding packets, have also stored those packets
	data_at in stored_data
		
/*
	// Data is held by a maximum of one device
	all datum: Data | some d: Device |
		datum in data_at[d]
*/
	// Each piece of data can only exist in one location at a time.
	all datum: Data |
		#data_at :> datum = 1

	// The owners of compromised data are compromised or attackers
	~data_at[malicious] in (compromised + attacker)

	// All data attached to compromised or attacker devices is malicious
	data_at[compromised+attacker] in malicious
}

pred init(s: State) {
	#s.attacker = 1
	#s.compromised = 0
	#s.malicious > 0
	#(Device - s.attacker) > 0


	// Every element in Data is owned by some device
	all datum: Data | one device: Device |
		(device -> datum) in s.data_at

/*
	// A piece of malicious data at a device implies that device is compromised
	all d: Device, datum: s.malicious |
		(d -> datum) in s.data_at implies d in s.compromised
*/
}

pred data_transfer_test(s: State) {

	// Some attacker is connected to an uncompromised device, both devices have data to share.
	// The uncompromised device has a channel to another uncompromised device
	some threat: s.attacker, d, d': Device - (s.compromised + s.attacker), datum: Data - s.malicious, mal_data: s.malicious | 
		(threat -> d) in s.channel && 			//threat has channel to 1st device
		(d -> d') in s.channel && 				//1st device has channel to another (uncompromised) device
		(threat -> d') not in s.channel &&		//threat does not have channel to 2nd device
		mal_data in s.data_at[threat] &&		//threat has malicious data to share
		datum in s.data_at[d]				//1st device has uncompromised data to share
}

fact{
	// Network state remains consistent between states; channels, attackers, compromised machines, malicious data.
	all s: State, s':s.next | 
		s.channel = s'.channel &&
		s.attacker = s'.attacker &&
		s.malicious in s'.malicious &&
		s.compromised in s'.compromised

	// Devices retain previously stored data
	all s: State, s': s.next |
		s.stored_data in s'.stored_data
		
	// Each piece of data at a device will be transferred to another device, if one exists.
	all s: State, s': s.next, sender: Device, datum: s.data_at[sender] | one receiver: s.channel[sender] |
		datum not in s'.data_at[sender] &&
		datum in s'.data_at[receiver]
		
}

// Compromised devices always have malicious data
assert no_nonmalicious_data_at_compromised{
	all s: State, d: s.compromised, datum: s.data_at[d] |
		datum in s.malicious 
}

// Devices with malicious data are always compromised
assert malicious_data_only_at_compromised{
	all s: State, d: Device, datum: s.malicious |
		datum in s.data_at[d] implies d in (s.compromised + s.attacker)
}

assert data_exists_in_one_place{
	all s: State, datum: Data |
		#(s.data_at :> datum) = 1
}

assert some_uncompromised{}

assert compromised_devices_never_recover{
	all s:State, s': s.next, d: Device |
		d in s.compromised implies d in s'.compromised ||
		d in s.attacker implies d in s'.attacker
}

assert data_never_at_rest{
	all s:State, s': s.next,  d: Device, datum: Data |
		(d -> datum) in s.data_at 
			implies (d -> datum) not in s'.data_at
}

run show{
	init[first]
	//data_transfer_test[first]
} for 10

check no_nonmalicious_data_at_compromised for 10

check malicious_data_only_at_compromised for 10

check data_exists_in_one_place for 10

check compromised_devices_never_recover for 10

check data_never_at_rest for 10
