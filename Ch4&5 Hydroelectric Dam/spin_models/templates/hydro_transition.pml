/* Control */
bool Flood_Gate_Valve = 0;
bool Flood_Pump = 0;
bool Sump_Valve = 1, Sump_Pump_1 = 1, Sump_Pump_2 = 1;
bool Activated_Flood_Control = 0;
bool Return_Water_Supply_Control = 0;
bool Gen_A_Status = 0;
bool Tag_2 = 0;
bool HMI_Return_Feed = 1;
bool Control_PLC_MODE;

/* Generator A */
bool Generator_PLC_MODE;
bool Gen_A_Active = 1;
bool Gen_A_Fan = 1;
bool Gen_A_GreenLED = 1;
bool Gen_A_Pump = 1;
bool Gen_A_RedLED = 0;
bool Gen_A_Valve = 1;

/* Generator B */
bool Gen_B_Status = 0;
bool Gen_B_Active = 0;
bool Gen_B_Fan = 0;
bool Gen_B_GreenLED = 0;
bool Gen_B_Pump = 0;
bool Gen_B_RedLED = 1;
bool Gen_B_Valve = 0;

bool OperatorAction = false;

proctype hydro_generator()
{
	/* Dynamic behaviour that occurs without operator interaction goes here */
	/* Update Gen_Status Variables with Gen_Active Variables */
	d_step{
		Gen_A_Status = Gen_A_Active;
		Gen_B_Status = Gen_B_Active;
	}
	/* Note that the gen on, gen off, gen on case is squashede by the operator
	taking their action before the this d_step, and then taking another after it.*/

	/* Check PLC Mode */
	if
	:: Generator_PLC_MODE == false -> goto Stop_Gen
	:: else -> skip
	fi;

	/* Compute new state of generator */
	if
	:: Gen_A_Active == false && Gen_B_Active == true -> goto Gen_B_On 
	:: Gen_A_Active == true && Gen_B_Active == false -> goto Gen_A_On 
	:: Gen_A_Active == true && Gen_B_Active == true -> goto Gen_A_B_On
	:: Gen_A_Active == false && Gen_B_Active == false -> goto Gen_A_B_Off
	fi;

	/* --------------------------------------------------------------------------- */

	Stop_Gen:
	skip;

	/* Turn off both generators */
	d_step {
		/* Generator A */
		Gen_A_Active = false;
		Gen_A_Valve = false; 
		Gen_A_Pump = false; 
		Gen_A_GreenLED = false; 
		Gen_A_Fan = false;
		Gen_A_RedLED = false;

		/* Generator B */
		Gen_B_Active = false;
		Gen_B_Valve = false; 
		Gen_B_Pump = false; 
		Gen_B_GreenLED = false; 
		Gen_B_Fan = false;
		Gen_B_RedLED = false;
	};

	goto end

	/* --------------------------------------------------------------------------- */

	/* Turn on Generator A */
	Gen_A_On: skip

	/* Turn on Generator A */
	d_step {
		Gen_A_Active = true;
		Gen_A_Valve = true; 
		Gen_A_Pump = true; 
		Gen_A_GreenLED = true; 
		Gen_A_Fan = true;
		Gen_A_RedLED = false;

		/* Turn off Generator B */
		Gen_B_Active = false;
		Gen_B_Valve = false; 
		Gen_B_Pump = false; 
		Gen_B_GreenLED = false; 
		Gen_B_Fan = false;
		Gen_B_RedLED = true;
	};

	if
	:: Gen_A_Status = true; Gen_B_Status = false;
	:: Gen_B_Status = false; Gen_A_Status = true;
	fi;

	goto end

	/* --------------------------------------------------------------------------- */

	/* Turn on Generator B */
	Gen_B_On: skip

	d_step {
		/* Turn on Generator B */
		Gen_B_Active = true;
		Gen_B_Valve = true; 
		Gen_B_Pump = true; 
		Gen_B_GreenLED = true; 
		Gen_B_Fan = true;
		Gen_B_RedLED = false;

		/* Turn off Generator A */
		Gen_A_Active = false;
		Gen_A_Valve = false; 
		Gen_A_Pump = false; 
		Gen_A_GreenLED = false; 
		Gen_A_Fan = false;
		Gen_A_RedLED = true;
	};
	
	if
	:: Gen_A_Status = false; Gen_B_Status = true;
	:: Gen_B_Status = true; Gen_A_Status = false;
	fi;

	goto end

	/* --------------------------------------------------------------------------- */

	/* Turn on Both Generators */
	Gen_A_B_On: skip


	d_step {
		/* Turn on Generator A */
		Gen_A_Active = true;
		Gen_A_Valve = true; 
		Gen_A_Pump = true; 
		Gen_A_GreenLED = true; 
		Gen_A_Fan = true;
		Gen_A_RedLED = false;

		/* Turn on Generator B */
		Gen_B_Active = true;
		Gen_B_Valve = true; 
		Gen_B_Pump = true; 
		Gen_B_GreenLED = true; 
		Gen_B_Fan = true;
		Gen_B_RedLED = false;
	};

	if
	:: Gen_A_Status = true; Gen_B_Status = true;
	:: Gen_B_Status = true; Gen_A_Status = true;
	fi;

	goto end

	/* --------------------------------------------------------------------------- */

	/* Turn off Generators */
	Gen_A_B_Off: 
	skip;

	/* Turn off both generators */
	d_step {
		/* Generator A */
		Gen_A_Active = false;
		Gen_A_Valve = false; 
		Gen_A_Pump = false; 
		Gen_A_GreenLED = false; 
		Gen_A_Fan = false;
		Gen_A_RedLED = true;

		/* Generator B */
		Gen_B_Active = false;
		Gen_B_Valve = false; 
		Gen_B_Pump = false; 
		Gen_B_GreenLED = false; 
		Gen_B_Fan = false;
		Gen_B_RedLED = true;
	};

	if
	:: Gen_A_Status = false; Gen_B_Status = false;
	:: Gen_B_Status = false; Gen_A_Status = false;
	fi;

	end:
}

proctype hydro_control()
{
	/* Transition for turning the PLC into STOP mode */
	if
	:: Control_PLC_MODE == false -> goto Stop_Ctrl
	:: else -> skip
	fi;

	/* List of active states that the PLC may transition into */
	if
	:: HMI_Return_Feed == true -> goto manual_return
	:: else -> goto run_water_control
	fi;

	/* --------------------------------------------------------------------------- */

	Stop_Ctrl: skip

	d_step {
		Sump_Valve = false; 
		Sump_Pump_1 = false; 
		Sump_Pump_2 = false;
		Return_Water_Supply_Control = false;
		HMI_Return_Feed = false;
		Gen_A_Status = false;
		Gen_B_Status = false;
		Flood_Gate_Valve = false;
	 	Flood_Pump = false;
		Activated_Flood_Control = false;
		Return_Water_Supply_Control = false;
		Tag_2 = false;
	};

	goto end

	/* --------------------------------------------------------------------------- */
	
	run_water_control: skip
	
	/* In the model the water return operates on a timer running for a preset amount of time, waiting and then running again */
	/* We abstract this so that the feed may or may not be running while the control is operating, both are valid. */
	if
	:: Return_Water_Supply_Control = false; goto water_return_off
	:: Return_Water_Supply_Control = true; goto water_return_on
	fi;

	/* -------------------------------- */

	water_return_off: skip

	/* Check Tag_2 value, prevents feed turning off */
	/* If true, return to run state */
	if
	:: Tag_2 == true -> goto end
	:: else -> skip
	fi;

	/* Ensure all valves and pumps are off*/
	d_step {
		Sump_Valve = false; 
		Sump_Pump_1 = false; 
		Sump_Pump_2 = false;
	};
	
	/* After waiting the preset amount of time the system begins the transition to turning on */
	/* The completion of this transition is already modelled in the water_return_on sequence */
	Return_Water_Supply_Control = true

	goto end
	
	/* -------------------------------- */

	water_return_on:

	/* Check Tag_2 value, prevents feed turning on */
	/* If true, return to run state */
	if
	:: Tag_2 == true -> goto end
	:: else -> skip
	fi;

	/* turn on all valves and pumps, simultaneously */
	d_step {
		Sump_Valve = true; 
		Sump_Pump_1 = true; 
		Sump_Pump_2 = true;
	};
	
	/* Sump_Valve resets Return_Water_Supply_Control */
	Return_Water_Supply_Control = false;
	
	goto end

	/* --------------------------------------------------------------------------- */
	
	manual_return: skip

	/* turn on all valves and pumps, simultaneously */
	d_step {
		Sump_Valve = true; 
		Sump_Pump_1 = true; 
		Sump_Pump_2 = true;
	};
	
	/* --------------------------------------------------------------------------- */

	end:

}

proctype hmi()
{
	/* Allow PLCs to compute non-operator transitions first */
	run hydro_generator()
	run hydro_control()

	/* Perform any operator interaction */
	send_instruction:
	atomic {
		if
		/* Turn either generator on, if off */
		:: Gen_A_Active == false -> Gen_A_Active = true
		:: Gen_B_Active == false -> Gen_B_Active = true

		/* Turn either generator off, if on */
		:: Gen_A_Active == true -> Gen_A_Active = false
		:: Gen_B_Active == true -> Gen_B_Active = false

		/* Turn both generator off, if on, or on if off. */
		:: Gen_A_Active == true & Gen_B_Active == true -> Gen_A_Active = false; Gen_B_Active = true
		:: Gen_A_Active == false & Gen_B_Active == false -> Gen_A_Active = true; Gen_B_Active = true

		/* Change the Hydro_Generator PLC into RUN mode, if in STOP mode. */
		:: Generator_PLC_MODE == false -> Generator_PLC_MODE = true

		/* Change the Hydro_Generator PLC into STOP mode, if in RUN mode. */	
		:: Generator_PLC_MODE == true -> Generator_PLC_MODE = false

		/* Change the Hydro_Control PLC into RUN mode, if in STOP mode. */
		:: Control_PLC_MODE == false -> Control_PLC_MODE = true

		/* Change the Hydro_Control PLC into STOP mode, if in RUN mode. */	
		:: Control_PLC_MODE == true -> Control_PLC_MODE = false

		/* Activate the manual return feed on the Hydro_Control PLC, if off. */
		:: HMI_Return_Feed == false -> HMI_Return_Feed = true

		/* Deactivate the manual return feed on the Hydro_Control PLC, if on. */
		:: HMI_Return_Feed == true -> HMI_Return_Feed = false

		/* Operator takes no action */
		:: skip
		fi;
	};
	
	/* If only one action has been taken, optionally take another action */
	if
	:: OperatorAction == false -> OperatorAction = true; goto send_instruction
	:: OperatorAction == true -> skip
	fi;
}

init{
	/* Since we do not have PLC mode data we represent it as a non-deterministic option which state the PLCs are in */
	if
	:: atomic {Generator_PLC_MODE = true; Control_PLC_MODE = true;}
	:: atomic {Generator_PLC_MODE = true; Control_PLC_MODE = false;}
	:: atomic {Generator_PLC_MODE = false; Control_PLC_MODE = true;}
	:: atomic {Generator_PLC_MODE = false; Control_PLC_MODE = false;}
	fi;

	/* Start all of the processes */
	run hmi()
}

ltl reachable_state {
	!<>(
		Flood_Gate_Valve == 0 &&
		Flood_Pump == 0 &&
		Sump_Valve == 1 &&
		Sump_Pump_1 == 1 &&
		Sump_Pump_2 == 1 &&
		Return_Water_Supply_Control == 0 &&
		
		/* Generator A */
		Gen_A_Status == 1 &&
		Gen_A_Active == 1 &&
		Gen_A_Fan == 1 &&
		Gen_A_GreenLED == 1 &&
		Gen_A_RedLED == 0 &&
		Gen_A_Pump == 1 &&
		Gen_A_Valve == 1 &&

		/* Generator B */
		Gen_B_Status == 0 &&
		Gen_B_Active == 0 &&
		Gen_B_Fan == 0 &&
		Gen_B_GreenLED == 0 &&
		Gen_B_RedLED == 1 &&
		Gen_B_Pump == 0 &&
		Gen_B_Valve == 0 &&

		Tag_2 == 0 &&
		HMI_Return_Feed == 1
	)
}