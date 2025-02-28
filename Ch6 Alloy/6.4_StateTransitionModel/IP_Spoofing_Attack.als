enum Status {
	Clean,
	Compromised
}

some var abstract sig Device {
	var status: Status,
	identity: Device,
	created: set Data,
	var accepted: set Data,
	var packets: set Packet
}{

	// If a device is compromised the device is an attacker or it has accepted some compromised data or was compromised in the previous state
	status = Compromised iff {
		this in Attacker
		or some data: accepted | before data.status = Compromised //before because clean/clean can become compromised/compromised during a transition
		or before status = Compromised
	}

	// Non-attacker devices have their own identity
	this not in Attacker implies identity = this

	// If a piece of data is accepted, it has previously been acquired from a packet that was intended for this device
	// and it was not created at this device
	all data: accepted | some packet: Packet {
		packet.payload = data 
		and once packet.location = this
		data not in created
	}
	
	// If device is clean it has never been compromised.
	status = Clean implies historically status = Clean

	all packet: packets {
		// Binds device.packets to packet.location
		packet.location = this
	}

	// accepted data is retained between states
	accepted in accepted'

	// All devices are connected to at least one channel
	some chan: Channel | this in chan.connected

	// If two channels intersect on a device then the device must be a switch
	all disj chan1, chan2: Channel {
		this in chan1.connected & chan2.connected implies this in Switch
	}
}
sig Switch extends Device {}{

	// Switches only exist between channels
	some disj chan1, chan2: Channel {
		this in chan1.connected and this in chan2.connected
	}

	no created
}
var sig Attacker extends Device {}{
	
	// Attacker devices are always considered compromised
	status = Compromised

	// The attacker must be in the same channel as the device it is pretending to be
	some channel: Channel |
		identity + this in channel.connected
}

sig PLC extends Device {}
sig DigitalTwin extends Device{}

some sig Data {
	var status: Status
}{
	// If the data is compromised it remains compromised (should be reduntant due to packet facts)
	status = Compromised implies status' = Compromised

	status = Compromised iff {
		before status = Compromised
		or some packet: Packet | this in packet.payload and packet.location.status = Compromised
		or some device: Device | this in device.accepted and device.status = Compromised
	}

	// Data is clean if it's always been clean and it's not interacted with any compromised devices
	status = Clean implies historically status = Clean

	// All data must be created by one device, this data shares the same status as that device
	one device: Device {
		this in device.created
	}
}

// Packets carry data across the network
some var sig Packet {
	source: one Device,
	destination: one Device,
	signature: one Device,
	payload: one Data,
	var location: one Device,
}{

	// Packets actually have to go somewhere.
	not source = destination

	// Switches don't send packets
	source not in Switch

	// No packets intentionally sent to the attacker
	destination not in Attacker

	// Payload data is only compromised if the packet is at a compromised location or if it was compromised in the previous state.
	payload.status = Compromised iff location.status = Compromised or before payload.status = Compromised

	// Packets always move until they reach their destination
	// Once there they remain there and their payload is accepted by the device
	location.identity = destination implies {
		payload in location.accepted
		location' = location
	}	else not location' = location

	// All packets eventually reach a valid destination
	eventually location.identity = destination

	// Switches can't be destinations
	destination not in Switch

	// Packets must move along channels unless they're at their destination
	all network: Topology | location -> location' in network.connections or location.identity = destination
}

some sig Channel {
	connected: some Device
}{
	// Channels need more than one device
	#connected > 1
}

one sig Topology {
	connections: Device -> Device
}{
	// All devices must have an indirect mapping to eachother
	all disj d1, d2: Device | d2 in d1.^connections

	// Connections are bidirectional
	connections = ~connections

	// Devices cannot be connected to themselves
	all d: Device | d not in connections[d]

	// Remove extraneous switches (no two switches have exactly the same connectivity
	all disj sw1, sw2: Switch | not connections[sw1] = connections[sw2]

	// All devices device connections must exist in at least one channel
	all disj d1, d2: Device | some chan: Channel {
		d1 -> d2 in connections iff d1 + d2 in chan.connected
	}

	// No two identical channels exist
	// Explicitly: the intersection of two channels cannot be equal to their union
	all disj chan1, chan2: Channel | not (chan1.connected & chan2.connected = chan1.connected + chan2.connected)

}

fact PacketInitialSetup {
	// Initial packet set up
	all packet: Packet {
		// Packets cannot start at their destination
		packet.location not in packet.destination
		packet.location.identity not in packet.destination

		// Packet sources are the same as the sender's public identity
		packet.source = packet.location.identity
		packet.signature = packet.location

		// Packet payloads were created by their initial location
		packet.payload in packet.location.created

		// No two packets have the same payload
		no other: Packet-packet | packet.payload = other.payload

		// Packets stop moving once at their destination
		//once packet.location.identity = packet.destination implies packet.location' = packet.location
	}
}

fact DeviceSetup {	

	// Devices remain constant
	//always Device = Device'

	all device: Device {
		// No device has accepted data initally
		no device.accepted

		// All data created by a device has the same status as that device
		all data: device.created | data.status = device.status

		// Initially all non-attacker devices are clean
		device not in Attacker implies device.status = Clean
	}

	digitaltwin_scenario[]

}

pred digitaltwin_scenario{

	#Attacker = 1
	#DigitalTwin = 1
	#PLC = 1
	#Switch = 1

	// All devices have data to share
	all plc: PLC | #plc.created > 0

	// Digital twins and PLCs do not share channels
	all channel: Channel, dt: DigitalTwin, plc: PLC  | dt + plc not in channel.connected
}

pred no_spoofed_receiver{

	all packet: Packet | eventually packet.location = packet.destination
}

pred no_attacker_created_data_accepted{

	// No non-attacker device accepts data that was created by an attacker
	always all device: Device-Attacker, data: device.accepted {
		no attacker: Attacker | data in attacker.created
	}
}

pred no_compromised_data_accepted{

	always all device: Device - Attacker, accepted: device.accepted | 
		accepted.status not in Compromised 
		
}

fact no_spoofed_plc {

	some packet: Packet {
		packet.source in PLC 
		eventually packet.location in DigitalTwin
	}
}

pred no_spoofed_plc{
	
	always all dt: DigitalTwin, accepted_data: dt.accepted | accepted_data.status = Clean
}

check no_spoofed_plc {

	no_spoofed_plc[]

} for 8 but 1 Packet, 3 Data, 1..10 steps

pred clean_data_transfer {

	eventually some packet: Packet {
		packet.source in PLC
		packet.destination in DigitalTwin
		packet.location = packet.destination
	} before some packet: Packet {
		packet.source in DigitalTwin
		packet.destination in PLC
		packet.location = packet.destination
	}
	
	all packet: Packet | always not packet.location in Attacker
}

check no_attacker_created_data_accepted {

	no_attacker_created_data_accepted[]

} for 6 but 1 Packet, 1..10 steps

check no_spoofed_receiver {

	no_spoofed_receiver[]

} for 8 but 1 Packet, 3 Data, 1..10 steps

check no_compromised_data_accepted{
	
	no_compromised_data_accepted[]

} for 5 but 1 Packet, 3 Data, 1..10 steps

run show{
	//no_spoofed_plc[]

	some attacker: Attacker {
		attacker.identity in PLC
		some packet: Packet | packet.location = attacker
	}
	//digitaltwin_scenario[]
	
	//all packet: Packet | eventually always packet.location = packet.location'

} for 10 but 1 Packet, 4 Data, 1..7 steps
