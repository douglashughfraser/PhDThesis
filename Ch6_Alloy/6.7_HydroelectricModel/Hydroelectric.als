// This model uses a data signatures that maps Device -> Tag -> Value
// This effectively creates a Data -> Device -> Tag -> Value relation.

open util/boolean

enum Value {
	ON,
	OFF,
	OF,
	H,
	M,
	L,
	UF
}

enum Status {
	Clean,
	Compromised
}

enum Tag {
	Upper_Tank,
	Lower_Tank,
	Generator,
	Sump_Pump,
	Sump_Valve
}

// Each piece of data can now map multiple tags to 
abstract var sig Device {
	var status: one Status,
	knows: Tag -> lone Value,
	learns: Tag -> Value,
	assigned_ip: one IP,
	var address: some IP,
	var port: some Port,
	channel: one Channel,
	stored_logins: User -> Password,
	username: one User,
	password: one Password,

}{
	status = Clean implies address = assigned_ip else address in assigned_ip + Threat.recon[Device] 

	learns = Data.content[this]

	#knows > 0 implies this in PLC

	// Devices share what they know
	some data: Data {
		knows in data.content[this]
	}

	status = Clean implies {
		#address = 1
	}

	status = Compromised implies this in Threat.controls
}

sig IP {
	ipv4: one String
}{
	// List of IP addresses for use in the model
	none != "192.168.3.5" + "192.168.3.7" + "192.168.3.9" + "192.168.3.10" + "192.168.3.11" + "192.168.5.9" + "172.26.6.192" + "172.26.6.186" 
	ipv4 in "192.168.3.5" + "192.168.3.7" + "192.168.3.9" + "192.168.3.10" + "192.168.3.11" + "192.168.5.9" + "172.26.6.192" + "172.26.6.186" 
}

sig Port {
	number: one String
}{
	// List of Port numbers for use in the model
	none !=  "1880" + "3000" + "8086" + "1883" + "102"
	number in "1880" + "3000" + "8086" + "1883" + "102"
}

sig User {}
sig Password {}

abstract sig Message {
	sender: one Device,
	receiver: one Device,
	payload: one Data
}{
	sender not in receiver

    // Messages can only be sent within channels or between channels if a Router connects them
    	sender -> receiver in Topology.connections

	sender -> receiver in payload.transmissions
}

abstract sig IPMessage extends Message{
	sender_ip: one IP,
	receiver_ip: one IP,
}{
	// IP addresses cannot be blocked
	sender_ip -> receiver_ip not in Firewall.block

	// Messages are delivered according to ip addresses.
	eventually sender_ip in sender.address
	eventually receiver_ip in receiver.address

	sender in Threat.controls implies eventually receiver_ip in Threat.recon[receiver]
}

sig TCPMessage extends IPMessage {
	sender_port: one Port,
	receiver_port: one Port,
}{
	// Messages are delivered according to port numbers.
	sender_port in sender.port
	receiver_port in receiver.port

	sender in Threat.controls implies eventually receiver_port in Threat.recon[receiver]
}

sig Data {
	wrapper: 			some Message,
	creator:			one Device,			// The device that created this data
	content: 			Device -> Tag -> Value, 	// Maps the value of the device at each reading 
	transmissions: 		Device -> Device,		// Tracks movement of data between devices
}{
	all device: Device, tag: Tag | #device.content[tag] <= 1

	all device: Device {
		// Data transmission doesn't loop
		device not in device.^transmissions
		// Some sanity constraints on Tag Value associations
		#content[device][Upper_Tank] > 0 implies content[device][Upper_Tank] not in ON + OFF
		#content[device][Lower_Tank] > 0 implies content[device][Lower_Tank] not in ON + OFF
		#content[device][Generator] > 0 implies content[device][Generator] not in OF + H + M + L + UF
		#content[device][Sump_Pump] > 0 implies content[device][Sump_Pump] not in OF + H + M + L + UF
		#content[device][Sump_Valve] > 0 implies content[device][Sump_Valve] not in OF + H + M + L + UF
	}

	all message: Message | this in message.payload iff message in wrapper

	// The clean devices must know some data in order to send it
	(always creator.status = Clean) implies creator.content in creator.knows

	// For every tag value pair that any device knows about
	all device: Device {
		all tag: Tag, value: Value {
			tag -> value in device.content implies { 
				// It either knows it because it's the creator
				(device = creator or
				// Or it was sent it by a device that knows it
				some sender: Device {
					sender -> device in transmissions
					tag -> value in sender.content
				})
			}
		}
	}

	// Tie trasmissions to messages so we can use them to dissemminate it
	all send, receive: Device {
		send -> receive in transmissions implies send in creator.*transmissions
		send -> receive in transmissions iff some message: Message {
			this = message.payload
			send = message.sender
			receive = message.receiver
		}
		send -> receive in transmissions implies #content[send] > 0
		send -> receive in transmissions implies ((always send.status = Clean) implies content[receive] = content[send])
		send -> receive in transmissions implies #content[receive] > 0
		send -> receive in transmissions implies receive.content in receive.learns
	}
}

some sig Channel {
	connected: some Device,
	router: some Router
}{
	all device: connected | this in device.channel
}

// Here there be problems.
one sig Topology {
	connections: Device -> Device,
	blocked: IP -> IP
}{
	// All devices must have an indirect mapping to eachother
	all disj d1, d2: Device | d2 in d1.^connections

	// Shows all Firewall blocks
	blocked = Firewall.block

	// Connections are bidirectional
	connections = ~connections

	// Devices cannot be connected to themselves
	all d: Device | d not in d.connections

	// All device -> device connections are manifested through channels and routeres
	all disj d1, d2: Device{
		d1 -> d2 in connections iff 
			some chan1: Channel {
				// connected devices exist in the same channel or
				(d1 + d2 in chan1.connected or (
					some chan2: Channel - chan1 {
						// they exist in seperate channels that are connected by a Router or firewall
						d1 in chan1.connected and
						d2 in chan2.connected and 
						some router: Router | chan1 + chan2 in router.channels
					}
				)	
			)
		}
	}

	// No two identical channels exist
	// Explicitly: the intersection of two channels cannot be equal to their union
	all disj chan1, chan2: Channel | not (chan1.connected & chan2.connected = chan1.connected + chan2.connected)
}

sig Router {
	channels: set Channel
}{
	all channel: Channel {
		this in channel.router iff channel in channels
	}
}

sig Firewall extends Router {
	block: IP -> IP,
}{
	// Self blocks are not allowed
	all ip: IP | ip -> ip not in block

	// Firewalls only block ips they're connected to. 
	// Other ips outside these most direct connections are implicitly blocked.
	all ip1, ip2: IP {
		(ip1 -> ip2) in block implies some d1, d2: channels.connected {
			ip1 = d1.assigned_ip
			ip2 = d2.assigned_ip
		}
	}
}

some abstract sig PLC extends Device {
	process: one Process
}{}

one sig ControlPLC extends PLC {
}{
	assigned_ip.ipv4 = "192.168.3.7"
	status = Clean implies port.number = "102"

	// We assume that the PLC is receiving trustworthy data
	Upper_Tank -> process.state[Upper_Tank] in knows
	Lower_Tank -> process.state[Lower_Tank] in knows
	Sump_Pump -> process.state[Sump_Pump] in knows
	Sump_Valve -> process.state[Sump_Valve] in knows

	// Control PLC doesn't know Generator variables
	knows not in Generator -> Value
}

one sig GeneratorPLC extends PLC {
}{
	assigned_ip.ipv4 = "192.168.3.5"
	status = Clean implies port.number = "102"

	// We assume that the PLC is receiving trustworthy data
	Generator -> process.state[Generator] in knows

	// Generator PLC doesn't know Control variables
	knows not in ((Upper_Tank + Lower_Tank + Sump_Pump + Sump_Valve) -> Value)

	// GeneratorPLC has none of these tags
	all data: Data {
		data.content[GeneratorPLC][Upper_Tank] = none
		data.content[GeneratorPLC][Lower_Tank] = none
		data.content[GeneratorPLC][Sump_Pump] = none
		data.content[GeneratorPLC][Sump_Valve] = none
	}
}

one sig Process {
	state: Tag -> one Value
}{
	state[Upper_Tank] not in ON + OFF
	state[Lower_Tank] not in ON + OFF
	state[Generator] in ON + OFF
	state[Sump_Pump] in ON + OFF
	state[Sump_Valve] in ON + OFF

	state[Upper_Tank] = UF iff state[Lower_Tank] = OF
	state[Upper_Tank] = H iff state[Lower_Tank] = L
	state[Upper_Tank] = M iff state[Lower_Tank] = M
	state[Upper_Tank]  = L iff state[Lower_Tank] = H
	state[Upper_Tank] = OF iff state[Lower_Tank]  = UF
}

one sig NodeRED extends Device{}{
	assigned_ip.ipv4 = "192.168.3.9"
	status = Clean implies port.number = "1880"
}

one sig InfluxDB extends Device{}{
	assigned_ip.ipv4 = "192.168.3.10"
	status = Clean implies port.number = "8086"
}

one sig Grafana extends Device{}{
	assigned_ip.ipv4 = "192.168.3.11"
	status = Clean implies port.number = "3000"
}

one sig Model extends Device{
	state: Tag -> Value
}{
	state[Upper_Tank] not in ON + OFF
	state[Lower_Tank] not in ON + OFF
	state[Generator] in ON + OFF
	state[Sump_Pump] in ON + OFF
	state[Sump_Valve] in ON + OFF

	assigned_ip.ipv4 = "192.168.5.9"
	status = Clean implies port.number = "1883"

	state in learns
}

one sig Workstation extends Device {}{
	assigned_ip.ipv4 = "172.26.6.186"
	status = Clean implies port.number = "3000"
}

lone var sig Threat{
	var controls: set Device,
	var recon: Device -> (Port+IP),
	var users: set User,
	var pwds: set Password,
	var current_actions: set Action,
	var actions: set Action,
}{
	all action: actions{
		once action in current_actions
		action in actions'
		action not in current_actions'
	}

	// Gathered data is the sum of all data learned through recon actions
	recon' = recon + actions.learn

	all device: Device | some ip:IP, p: Port {
		device -> ip in recon implies ip in device.address
		device -> p in recon implies p in device.port
	}

	// Passwords and usernames found on controlled machines are known.
	users' -> pwds' = (controls.username -> controls.password) + controls.stored_logins

	// Only compromised devices can be controlled
	controls.status = Compromised

	// Compromised devices can use any known address or port number
	all controlled: controls {
		controlled.address in controlled.assigned_ip + recon[Device]
		controlled.port in recon[Device]
	}

	controls in controls'

	all device: controls {
		// All controlled devices have either always been controlled
		(historically device in controls) or {
			// Or some action has brought them under control
			some action: LateralMovement & actions {
				device = action.target
			}
		}
	}
}

abstract sig Action {
	origin: one Device,
	target: some Device,
}{
	// Conditions that must be satisfied to use this action
	this in Threat.current_actions implies {
		// Attacks can only be launched from controlled devices
		origin in Threat.controls
		this in Threat.actions'
	}

	// Can only target reachable devices that are not blocked
	target in Topology.connections[origin]
	
	// Attacker must have some unblocked path to attacker.
	some addr: origin.address {
		(addr -> target.address) not in Firewall.block
	}
}

// Recon actions give the threat information
abstract sig Recon extends Action {
	learn: Device -> (Port+IP)
}

sig NetworkScan extends Recon {
}{
	// Network scans yield target ip addresses
	all device: Device, ip: IP {
		device -> ip in learn iff (device in target and ip in device.assigned_ip)
	}
	// Network scans extended to include port scanning
	all device: Device, p: Port {
		device -> p in learn iff (device in target and p in device.port)
	}

	// Can't run network scans from PLCs
	origin not in PLC
}

// Lateral movement actions allow the threat to leverage content to propagate through the network
abstract sig LateralMovement extends Action {
	requires: Device -> (IP + Port) // A set of data required about the target to execute this action
}{
	// Requirements are related to the target
	requires in target -> (IP+Port)

	// LateralMovement actions can only be launched against a known ip and port
	all device: target {
		some addr: device.address | device -> addr in requires
		some p: device.port | device -> p in requires
	}

	// If this action has been taken then 
	this in Threat.current_actions implies {
		requires in Threat.recon
		target in Threat.controls
	}
}

// The attacker can exploit known usernames and password to access other devices
sig ExploitUserAccount extends LateralMovement{
}{
	this in Threat.current_actions implies {
		target.username in Threat.users and target.password in Threat.pwds
	}
}

/*
// Viable signature for Port Scanning actions, removed to reduce trace length.
// Functionality incorporated into NetworkScan
sig PortScan extends Recon {
}{
	// Port scans yield only ports
	learn in Device -> Port

	// Port scans yield only target ports
	all device: Device, p: Port {
		device -> p in learn iff (device in target and p in device.port)
	}

	this in Threat.current_actions implies {
		target -> target.address in Threat.recon
	}

	// Can't run port scans from PLCs
	origin not in PLC
}
*/

fact behaviours {

	// No overlapping datasets
	//all disj datum1, datum2: Data | no datum1.content & datum2.content

	all disj device, other: Device {

		// If neither device is compromised
		other.status = Clean and device.status = Clean implies {
			// They should use different ports or addresses
			device.port != other.port or device.address != other.address
		}
	}

	// Message sending behaviours under normal conditions
	all m: Message {
		(always m.sender.status = Clean) implies {
			m.sender in GeneratorPLC implies m.receiver in NodeRED
			m.sender in ControlPLC implies m.receiver in NodeRED
			m.sender in NodeRED implies m.receiver in InfluxDB
			m.sender in InfluxDB implies m.receiver in Grafana + Model
			m.sender not in Grafana
			m.sender in Model implies m.receiver in InfluxDB
		}
	}

	// 
	all m: IPMessage {
		m.receiver in NodeRED implies m.sender_ip in PLC.assigned_ip
		m.receiver in InfluxDB implies m.sender_ip in NodeRED.assigned_ip
		m.receiver in Grafana implies m.sender_ip in InfluxDB.assigned_ip
		m.receiver in Model implies m.sender_ip in InfluxDB.assigned_ip
	}

	// The model and grafana are constantly updated with new data
	all tag: Tag {
		#Model.state[tag] > 0
		//#Grafana.learns[tag] > 0
	}
}

fact initialising_rules {

	// No two identical channels exist
	all disj chan1, chan2: Channel {
		not chan1.connected = chan2.connected
	}

	// No two routers share two channels
	all disj r1, r2: Router {
		no disj chan1, chan2: Channel {
			(chan1 + chan2) in r1.channels
			(chan1 + chan2) in r2.channels
		}
	}

	// Eliminate duplicate ports and ips for each device
	all device: Device {
		all disj ip1, ip2: device.address | not ip1.ipv4 = ip2.ipv4
		all disj p1, p2: device.port | not p1.number = p2.number
	}

	// No duplicate actions
	all disj a1, a2: ExploitUserAccount {
		not (a1.target = a2.target and a1.origin = a2.origin)
		not (a1.target = a2.origin and a1.origin = a2.target)
	}

	// Each tag is initially only known by one device which knows one value for it.
	all tag: Tag | one device:Device | #device.knows[tag] > 0

	all action: Action | eventually action in Threat.current_actions

	all user: User, pwd: Password {
		user -> pwd in Device.stored_logins implies some device: Device {
			device.username = user
			device.password = pwd
		}
	}
}

pred DMZ {
	#Router = 3
	one fw: Firewall {
		some disj chan1, chan2: Channel {
			fw.channels = chan1 + chan2
			PLC in chan1.connected
			NodeRED + InfluxDB + Grafana in chan2.connected
		}
	}

	one fw: Firewall {
		some disj chan1, chan2: Channel {
			fw.channels = chan1 + chan2
			chan1.connected = NodeRED + InfluxDB + Grafana
			chan2.connected = Model
		}
	}


	one fw: Firewall {
		some disj chan1, chan2: Channel {
			fw.channels = chan1 + chan2
			chan1.connected = Model
			chan2.connected = Workstation
		}
	}
	
	#Topology.blocked = 0 //Workstation.assigned_ip -> (InfluxDB+NodeRED+Grafana+PLC).assigned_ip
}

pred Segmentation {
	#Router = 1
	one fw: Firewall {
		some disj chan1, chan2: Channel {
			fw.channels = chan1 + chan2
			PLC = chan1.connected
			fw.block = Workstation.assigned_ip -> PLC.assigned_ip
		}
	}
}

pred password_management {
	// Username and password combinations are different
	all disj d1, d2: Device {
		not (d1.username = d2.username and d1.password = d2.password)
		//not d1.username = d2.username
		//not d1.password = d2.password
	}

	all device: Device {
		no device.stored_logins
	}

	// Restrictive passwords on Clean devices
	all device: Device - Threat.controls {
		device.status = Clean implies {
			#device.stored_logins = 0
			//device.username not in Threat.users
			//device.password not in Threat.pwds
		}
	}
}

pred threat_model {

	#Threat.controls = 1

	#Workstation.stored_logins < 3

	// Attacker starts knowing only what is available on it's starting device.
	Threat.recon = (Threat.controls -> (Threat.controls.assigned_ip + Threat.controls.port))

	// The starting device contains only it's own login details.
	Threat.users -> Threat.pwds = (Threat.controls.username -> Threat.controls.password) + Threat.controls.stored_logins

	

	// Some examples of useful attack constraints to examine specific vulnerabilities
	//#ExploitUserAccount < 2
	//#NetworkScan < 2
	//eventually some plc: PLC | plc in Threat.controls
	//eventually InfluxDB in Threat.controls
	//all action: Action | action.target in Model + InfluxDB
	//always #Threat.controls < 3
}

fact configuration {

	threat_model[] 
	password_management[]
	//Segmentation[]
	DMZ[]

}

check disrupt_thread {
	Process.state = Model.state
}for 9 but 8 Device, 4 Channel, 3 Router, 5 Action, 10 Message, 1..5 steps 

check performance_eval {
	threat_model[]

	not eventually Threat.controls = Device

} for 10 but 15 Device, 10 Channel, 10 Action, 1..10 steps
