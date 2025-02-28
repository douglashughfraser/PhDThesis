open util/ordering[State]

sig Data {}
sig Device {}

sig State {
	data: set Device -> set Data,
	channel: set Device -> set Device // A device has least one connection
}{
	all d: Device | d not in d.channel // Devices do not have channels directly to themselves.
	all d, d': Device | d' in d.^channel // Every device has a (indirect) communication channel to every other device.	
}

fact{
	// Network channels remain consistent between states
	all s: State, s':s.next | 
		s.channel = s'.channel

	// Previously known data is a subset of currently known data
	// i.e. data known by data in previous states is retained in future states
	all s: State, s': s.next, device: Device |
		s.data[device] in s'.data[device]

	// Devices share all data that they have on all connections between states
	all s: State, s': s.next, sender: Device, receiver: s.channel[sender] |
		s'.data[receiver] = s.data[receiver] + s.data[sender]
}


// Must be more than x devices in the initial state, and at least y data connections
pred init(s: State) {
	#s.data = 1
}

run show {
	init[first]
} for 5 but 5 State, exactly 1 Data
