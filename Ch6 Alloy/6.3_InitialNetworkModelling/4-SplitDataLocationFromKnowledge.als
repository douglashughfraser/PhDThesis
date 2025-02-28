open util/ordering[State]

sig Data {}
sig Device {}

sig State {
	// A device has least one connection
	channel: set Device -> set Device,

	// In each state a piece of data can exist in one location
	data_location: set Data -> one Device,

	// The set of data that a device retains knowledge about
	stored_data: set Device -> set Data,

	//compromised: set Device,
	//malicious: set Data
}{
	all d: Device | d not in d.channel // Devices do not have channels directly to themselves.
	all d, d': Device | d' in d.^channel // Every device has a (indirect) communication channel to every other device.

	~(data_location) in stored_data
}

pred data_transfer_test(s: State) {
/*
	// Some attacker is connected to an uncompromised device, both devices have data to share.
	// The uncompromised device has a channel to another uncompromised device
	some attacker: s.compromised, d, d': Device - s.compromised, datum, malicious: Data | 
		(attacker -> d) in s.channel &&
		(d -> d') in s.channel &&
		(d -> attacker) not in s.channel &&
		(s -> attacker) in malicious.location &&
		(s -> d) in datum.location &&
		#s.channel[d] > 0
*/
	// Every element in Data is connected to a device
	all datum: Data | one device: Device |
		(datum -> device) in s.data_location
}

fact{
	// Network state remains consistent between states; channels, compromised machines, malicious data.
	all s: State, s':s.next | 
		s.channel = s'.channel

	// Devices retain previously stored data
	all s: State, s': s.next |
		s.stored_data in s'.stored_data

	// Data may be transferred from one connected device to another between states
	all s: State, s': s.next, datum: Data |
		s'.data_location[datum] in (s.channel[s.data_location[datum]] + s.data_location[datum])

	// Some state exists where a device recieves data it already knew about
	some s:State, s': s.next, datum: Data, d:Device |
		(d -> datum) in s.stored_data &&
		(datum -> d) in s'.data_location &&
		(datum -> d) not in s.data_location
}

run test_data_transfer{
	data_transfer_test[first]
	
} for exactly 1 Data, exactly 3 Device, exactly 5 State
