open util/ordering[State]

sig Data {}
sig Device {}

sig State {
	data: set Device -> set Data,
	channel: set Device -> set Device, // A device has least one connection

	compromised: set Device,
	malicious: set Data
}{
	all d: Device | d not in d.channel // Devices do not have channels directly to themselves.
	all d, d': Device | d' in d.^channel // Every device has a (indirect) communication channel to every other device.

	// Devices that have access malicious data are compromised
	all d: Device, datum: data[d] | 
		datum in malicious implies d in compromised

	all datum: Data | some device: Device |
		datum in data[device]

	// This last fact makes everything get really compromised really quick...
	all d: compromised, datum: data[d] |
		datum in malicious 
}

// Must be more than x devices in the initial state, and at least y data connections
pred init(s: State) {
	#s.data > 0
	#s.malicious = 1

	not s.compromised = Device
}

pred basic_example(s: State) {
	#s.data = 1
	#s.compromised = 1

	all comp: s.compromised, datum: Data |
		comp -> datum not in s.data
}


// The "good" device immediately becomes compromised, despite never having received data from a compromised device. 
// Its "good" data becomes malicious when it is received by the compromised system and this tracks back to label the "good" sender as compromised.
// This isn't something that can be fixed by this approach without a different way of modelling the data.
// The "data" relation is effectively how "stored_data" is modelled in future models.
pred design_flaw(s: State) {
	#s.malicious = 1
	#s.compromised = 1

	// There is some uncompromised device
	not s.compromised = Device

	some good, bad: Device, datum: Data |
		good not in s.compromised &&
		bad in s.compromised &&
		(good -> bad) in s.channel &&
		(bad -> good) not in s.channel && // Needed because compromised systems need to share their -required- malicious data
		(good -> datum) in s.data
}

fact{
	// Network state remains consistent between states; channels, compromised machines, malicious data.
	all s: State, s':s.next | 
		s.channel = s'.channel
	
	// Compromised states are retained in future states.
	// Lesson learned: "=" means that state transitions cannot add to set of compromised devices
	all s: State, s':s.next |
		s.compromised in s'.compromised &&
		s.malicious in s'.malicious

	// Previously known data is a subset of currently known data
	// i.e. data known by data in previous states is retained in future states
	all s: State, s': s.next, device: Device |
		s.data[device] in s'.data[device]

	// Devices share all data that they have on all connections between states
	all s: State, s': s.next, sender: Device, receiver: s.channel[sender] |
		s'.data[receiver] = s.data[receiver] + s.data[sender]
}

run show {
	init[first]
} for 3 but 5 State

run show_basic_design_flaw {
	basic_example[first]
} for 5
