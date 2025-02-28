sig Device {
	channel: some Device // A device has least one connection
} {
	this not in channel // Devices cannot be directly connected to themselves
}

run show {
	#Device > 5
} for 6 Device
