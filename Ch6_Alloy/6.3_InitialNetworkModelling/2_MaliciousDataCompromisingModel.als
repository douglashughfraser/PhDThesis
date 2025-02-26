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
	// All compromised devices have accessed some malicious data
	all comp: compromised | some datum: data[comp] |
		datum in malicious
}

// Must be more than x devices in the initial state, and at least y data connections
pred init(s: State) {
	#s.data > 0
	#s.malicious = 1

	not s.compromised = Device

	all datum: Data | some device: Device |
		datum in s.data[device]
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
} for 4 but 5 State, exactly 2 Data
