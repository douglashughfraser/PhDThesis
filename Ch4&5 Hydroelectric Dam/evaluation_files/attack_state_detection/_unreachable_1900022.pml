/* Generator variables for turbines A and B */
/* No template values as this is always the start state for the dam */
bool Generator_PLC_MODE = false;
bool Gen_A_Active = false;
bool Gen_A_Fan = false;
bool Gen_A_GreenLED = false;
bool Gen_A_Pump = false;
bool Gen_A_RedLED = false;
bool Gen_A_Valve = false;

bool Gen_B_Active = false;
bool Gen_B_Fan = false;
bool Gen_B_GreenLED = false;
bool Gen_B_Pump = false;
bool Gen_B_RedLED = false;
bool Gen_B_Valve = false;

// Control variables
bool Control_PLC_MODE = false;
bool Gen_A_Status = false;
bool Gen_B_Status = false;
bool Flood_Gate_Valve = false;
bool Flood_Pump = false;
bool Sump_Valve = false, Sump_Pump_1 = false, Sump_Pump_2 = false;
bool Activated_Flood_Control = false;
bool Return_Water_Supply_Control = false;
bool HMI_Return_Feed = false;
bool Tag_2 = false;
int IEC_Counter_0_DB = 0;
int IEC_Timer_0_DB = 0;

active proctype hydro_generator()
{
	id_gen_state:
	if
	:: Generator_PLC_MODE == true -> skip
	:: Generator_PLC_MODE == false -> goto STOP_GEN
	fi;
	
	if
	:: Gen_A_Active == true & Gen_B_Active == true -> goto Generator_A_B_Control
	:: Gen_A_Active == true & Gen_B_Active == false -> goto Generator_A_Control
	:: Gen_A_Active == false & Gen_B_Active == true -> goto Generator_B_Control
	:: Gen_A_Active == false & Gen_B_Active == false -> goto Generator_A_B_Off
	fi;
	
	/* if no state identified, return to start. */
	goto id_gen_state
	
	/* ---------------------------------------------------------------------------*/
	STOP_GEN: skip
	d_step {
		Gen_A_Active = false;
		Gen_A_Valve = false; 
		Gen_A_Pump = false; 
		Gen_A_GreenLED = false; 
		Gen_A_Fan = false; 
		Gen_A_RedLED = false;

		Gen_B_Active = false;
		Gen_B_Valve = false; 
		Gen_B_Pump = false; 
		Gen_B_GreenLED = false; 
		Gen_B_Fan = false; 
		Gen_B_RedLED = false;
	};
	
	d_step{
		Gen_A_Status = false;
		Gen_B_Status = false;
	};
	
	/*end_gen:*/
	/* Wait until turned back on */
	if
	:: Generator_PLC_MODE == true -> goto id_gen_state
	fi;

	/* ---------------------------------------------------------------------------*/
	Generator_A_Control: skip
	/* turn on generator A, turn off generator B. */
	d_step {
		Gen_A_Active = true;
		Gen_A_Valve = true; 
		Gen_A_Pump = true; 
		Gen_A_GreenLED = true; 
		Gen_A_Fan = true; 
		Gen_A_RedLED = false;
		
		Gen_B_Active = false;
		Gen_B_Valve = false; 
		Gen_B_Pump = false; 
		Gen_B_GreenLED = false; 
		Gen_B_Fan = false; 
		Gen_B_RedLED = true;
	};

	d_step{
		Gen_A_Status = true;
		Gen_B_Status = false;
	}

	/* Explicitly state transitions out of this state. */
	if
	:: Gen_A_Active == false -> goto id_gen_state
	:: Gen_B_Active == true -> goto id_gen_state
	:: Generator_PLC_MODE == false -> goto id_gen_state
	fi;

	/* ---------------------------------------------------------------------------*/
	Generator_B_Control: skip
	/* turn on generator B, turn off generator A. */
	d_step {
		Gen_A_Active = false;
		Gen_A_Valve = false; 
		Gen_A_Pump = false; 
		Gen_A_GreenLED = false; 
		Gen_A_Fan = false; 
		Gen_A_RedLED = true;
		
		Gen_B_Active = true;
		Gen_B_Valve = true; 
		Gen_B_Pump = true; 
		Gen_B_GreenLED = true; 
		Gen_B_Fan = true; 
		Gen_B_RedLED = false;
	};

	d_step{
		Gen_A_Status = false;
		Gen_B_Status = true;
	}

	/* Explicitly state transitions out of this state. */
	if
	:: Gen_B_Active == false -> goto id_gen_state
	:: Gen_A_Active == true -> goto id_gen_state
	:: Generator_PLC_MODE == false -> goto id_gen_state
	fi;
	
	/* ---------------------------------------------------------------------------*/
	Generator_A_B_Control: skip
	/* Turn on generator A and B */
	d_step {
		Gen_A_Active = true;
		Gen_A_Valve = true; 
		Gen_A_Pump = true; 
		Gen_A_GreenLED = true; 
		Gen_A_Fan = true; 
		Gen_A_RedLED = false;
		
		Gen_B_Active = true;
		Gen_B_Valve = true; 
		Gen_B_Pump = true; 
		Gen_B_GreenLED = true; 
		Gen_B_Fan = true; 
		Gen_B_RedLED = false;
	};
	
	d_step{
		Gen_A_Status = true;
		Gen_B_Status = true;
	}

	/* Explicitly state transitions out of this state. */
	if
	:: Gen_B_Active == false -> goto id_gen_state
	:: Gen_A_Active == false -> goto id_gen_state
	:: Generator_PLC_MODE == false -> goto id_gen_state
	fi;
	
	/* ---------------------------------------------------------------------------*/
	Generator_A_B_Off: skip
	/* turn off generators */
	d_step {
		Gen_A_Active = false;
		Gen_A_Valve = false; 
		Gen_A_Pump = false; 
		Gen_A_GreenLED = false; 
		Gen_A_Fan = false; 
		Gen_A_RedLED = true;
		
		Gen_B_Active = false;
		Gen_B_Valve = false; 
		Gen_B_Pump = false; 
		Gen_B_GreenLED = false; 
		Gen_B_Fan = false; 
		Gen_B_RedLED = true;
	};

	d_step{
		Gen_A_Status = false;
		Gen_B_Status = false;
	}

	/* Explicitly state transitions out of this state. */
	if
	:: Gen_A_Active == true -> goto id_gen_state
	:: Gen_B_Active == true -> goto id_gen_state
	:: Generator_PLC_MODE == false -> goto id_gen_state
	fi;
	/* ---------------------------------------------------------------------------*/
}

active proctype hydro_control()
{
	id_ctrl_state:
	/* Check PLC active */
	if
	:: Control_PLC_MODE == true -> skip
	:: Control_PLC_MODE == false -> goto STOP_CTRL
	fi;
	
	/* Check function block trigger conditions */
	if
	:: HMI_Return_Feed == false & Gen_A_Status == false & Gen_B_Status == false -> goto Off_Gen
	:: HMI_Return_Feed == false & Gen_A_Status == true & Gen_B_Status == false -> goto Water_Return_Single_Gen_A
	:: HMI_Return_Feed == false & Gen_A_Status == false & Gen_B_Status == true -> goto  Water_Return_Single_Gen_B
	:: HMI_Return_Feed == false & Gen_A_Status == true & Gen_B_Status == true -> goto  Water_Return_Both_Gen
	:: HMI_Return_Feed == true -> goto ON_MANUAL_FEED
	fi;

	/* ---------------------------------------------------------------------------*/	
	/* PLC Turned off, all values reset to 0. */
	STOP_CTRL: skip
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
	
	/*end_ctrl:*/
	/* Wait until turned on */
	if
	:: Control_PLC_MODE == true -> goto id_ctrl_state
	fi;
	
	/* --------------------------------------------------------------------------- */
	/* Both generators off, no manual return, only works if Tag_2 is false */
	Off_Gen: skip
	
	if
	:: Tag_2 == true -> skip;
	:: else -> d_step {
		Sump_Valve = false; 
		Sump_Pump_1 = false; 
		Sump_Pump_2 = false;
	};
	fi;
	
	/* Exit conditions for this state */
	if
	:: Control_PLC_MODE == false -> goto id_ctrl_state
	:: Gen_A_Status == true | Gen_B_Status == true -> goto id_ctrl_state
	:: Gen_B_Status == true -> goto id_ctrl_state
	:: HMI_Return_Feed == true -> goto id_ctrl_state
	fi;

	/* --------------------------------------------------------------------------- */
	/* Generator A on, run water control */
	Water_Return_Single_Gen_A: skip
	Return_Water_Supply_Control = false;

	/* Turn off all valves and pumps while waiting to activate */
	d_step {
		Sump_Valve = false; 
		Sump_Pump_1 = false; 
		Sump_Pump_2 = false;
	};

	/* Check for exit triggers */
	if
	:: Control_PLC_MODE == false -> goto id_ctrl_state
	:: Gen_A_Status == false -> goto id_ctrl_state
	:: Gen_B_Status == true -> goto id_ctrl_state
	:: HMI_Return_Feed == true -> goto id_ctrl_state
	:: else -> skip
	fi;

	/* Wait 20 seconds before turning on return feed. */
	/* Counter does not increase if Tag_2 is true */
	if
	/* Counter increases by 10 instead of 1 to reduce state space. */
	:: IEC_Counter_0_DB < 20 & Tag_2 == false -> IEC_Counter_0_DB = IEC_Counter_0_DB + 10
	:: IEC_Counter_0_DB == 20 & Tag_2 == false -> IEC_Counter_0_DB = IEC_Counter_0_DB + 10 ; Return_Water_Supply_Control = true
	:: Tag_2 == true -> skip
	fi;
	

	/* Loop or activate water return */
	if 
	:: Return_Water_Supply_Control == false -> goto Water_Return_Single_Gen_A
	:: else -> skip
	fi;
	
	/* turn on valve and pumps if Tag_2 is false */
	/* Neither water return or Timer will activate if Tag_2 is false, so skip to end*/
	if
	:: Tag_2 == true -> goto Water_Return_Single_Gen_A_END
	:: else -> d_step {
		Sump_Valve = true; 
		Sump_Pump_1 = true; 
		Sump_Pump_2 = true;
	};
	fi;

	atomic{
		Return_Water_Supply_Control = false;
		IEC_Counter_0_DB = 0;
	};

	Water_Return_Single_Gen_A_Active:

	/* Check for triggers for alternative functions that will overrule this function */
	if
	:: Control_PLC_MODE == false -> goto id_ctrl_state
	:: Gen_A_Status == false -> goto id_ctrl_state
	:: Gen_B_Status == true -> goto id_ctrl_state
	:: HMI_Return_Feed == true -> goto id_ctrl_state
	:: else -> skip
	fi;

	/* Check timer condition, loop until satisfied */
	if
	/* Timer increased by 10 instead of 1 to reduce state space */
	:: IEC_Timer_0_DB < 30 -> IEC_Timer_0_DB = IEC_Timer_0_DB + 10; goto Water_Return_Single_Gen_A_Active
	:: IEC_Timer_0_DB == 30 -> IEC_Timer_0_DB = 0; skip
	fi;

	/* turn off valve and pumps */
	d_step {
		Sump_Valve = false; 
		Sump_Pump_1 = false; 
		Sump_Pump_2 = false;
	};
	
	Water_Return_Single_Gen_A_END:

	/* Sequence complete, return to id to start again if appropriate.*/
	goto id_ctrl_state

	/* --------------------------------------------------------------------------- */
	/* Generator B on, run water control */
	Water_Return_Single_Gen_B: skip
	Return_Water_Supply_Control = false;

	/* Turn off all valves and pumps while waiting to activate */
	d_step {
		Sump_Valve = false; 
		Sump_Pump_1 = false; 
		Sump_Pump_2 = false;
	};

	/* Check for triggers for alternative functions that will overrule this function */
	if
	:: Control_PLC_MODE == false -> goto id_ctrl_state
	:: Gen_A_Status == true -> goto id_ctrl_state
	:: Gen_B_Status == false -> goto id_ctrl_state
	:: HMI_Return_Feed == true -> goto id_ctrl_state
	:: else -> skip
	fi;

	/* Wait 10 seconds before turning on return feed. */
	/* Counter does not increase if Tag_2 is true */
	if
	/* Counter increases by 5 instead of 1 to reduce state space. */
	:: IEC_Counter_0_DB < 20 & Tag_2 == false -> IEC_Counter_0_DB = IEC_Counter_0_DB + 10
	:: IEC_Counter_0_DB == 20 & Tag_2 == false -> IEC_Counter_0_DB = IEC_Counter_0_DB + 10; Return_Water_Supply_Control = true
	:: Tag_2 == true -> skip
	fi;
	
	/* Loop or activate water return */
	if 
	:: Return_Water_Supply_Control == false -> goto Water_Return_Single_Gen_B
	:: else -> skip
	fi;
	
	/* turn on valve and pumps if Tag_2 is false */
	/* Neither water return or Timer will activate if Tag_2 is false, so skip to end*/
	if
	:: Tag_2 == true -> goto Water_Return_Single_Gen_B_END
	:: else -> d_step {
		Sump_Valve = true; 
		Sump_Pump_1 = true; 
		Sump_Pump_2 = true;
	};
	fi;

	atomic{
		Return_Water_Supply_Control = false;
		IEC_Counter_0_DB = 0;
	};

	Water_Return_Single_Gen_B_Active:

	/* Check for triggers for alternative functions that will overrule this function */
	if
	:: Control_PLC_MODE == false -> goto id_ctrl_state
	:: Gen_A_Status == true -> goto id_ctrl_state
	:: Gen_B_Status == false -> goto id_ctrl_state
	:: HMI_Return_Feed == true -> goto id_ctrl_state
	:: else -> skip
	fi;

	/* Check timer condition, loop until satisfied */
	if
	/* Timer increased by 10 instead of 1 to reduce state space */
	:: IEC_Timer_0_DB < 30 -> IEC_Timer_0_DB = IEC_Timer_0_DB + 10; goto Water_Return_Single_Gen_B_Active
	:: IEC_Timer_0_DB == 30 -> IEC_Timer_0_DB = 0; skip
	fi;

	/* turn off valve and pumps */
	d_step {
		Sump_Valve = false; 
		Sump_Pump_1 = false; 
		Sump_Pump_2 = false;
	};

	Water_Return_Single_Gen_B_END:

	/* Sequence complete, return to id to start again if appropriate.*/
	goto id_ctrl_state

	/* --------------------------------------------------------------------------- */
	/* Generator A and B on, run water control */
	Water_Return_Both_Gen: skip
	Return_Water_Supply_Control = false;

	/* Turn off all valves and pumps while waiting to activate */
	d_step {
		Sump_Valve = false; 
		Sump_Pump_1 = false; 
		Sump_Pump_2 = false;
	};

	/* Check for exit triggers */
	if
	:: Control_PLC_MODE == false -> goto id_ctrl_state
	:: Gen_A_Status == false -> goto id_ctrl_state
	:: Gen_B_Status == false -> goto id_ctrl_state
	:: HMI_Return_Feed == true -> goto id_ctrl_state
	:: else -> skip
	fi;

	/* Wait 10 seconds before turning on return feed. */
	/* Counter does not increase if Tag_2 is true */
	if
	/* Counter increases by 5 instead of 1 to reduce state space. */
	/* Shorter wait time when both generators are active */
	:: IEC_Counter_0_DB < 10 & Tag_2 == false -> IEC_Counter_0_DB = IEC_Counter_0_DB + 10
	:: IEC_Counter_0_DB == 10 & Tag_2 == false -> IEC_Counter_0_DB = IEC_Counter_0_DB + 10; Return_Water_Supply_Control = true
	:: Tag_2 == true -> skip
	fi;

	/* Loop or activate water return */
	if 
	:: Return_Water_Supply_Control == false -> goto Water_Return_Both_Gen
	:: else -> skip
	fi;
	
	/* turn on valve and pumps if Tag_2 is false */
	/* Neither water return or Timer will activate if Tag_2 is false, so skip to end*/
	if
	:: Tag_2 == true -> goto Water_Return_Both_Gen_END
	:: else -> d_step {
		Sump_Valve = true; 
		Sump_Pump_1 = true; 
		Sump_Pump_2 = true;
	};
	fi;

	atomic{
		Return_Water_Supply_Control = false;
		IEC_Counter_0_DB = 0;
	};

	Water_Return_Both_Gen_Active:

	/* Check for exit triggers */
	if
	:: Control_PLC_MODE == false -> goto id_ctrl_state
	:: Gen_A_Status == false -> goto id_ctrl_state
	:: Gen_B_Status == false -> goto id_ctrl_state
	:: HMI_Return_Feed == true -> goto id_ctrl_state
	:: else -> skip
	fi;

	/* Check timer condition, loop until satisfied */
	if
	/* Timer increased by 10 instead of 1 to reduce state space */
	:: IEC_Timer_0_DB < 30 -> IEC_Timer_0_DB = IEC_Timer_0_DB + 10; goto Water_Return_Both_Gen_Active
	:: IEC_Timer_0_DB == 30 -> IEC_Timer_0_DB = 0; skip
	fi;

	/* turn off valve and pumps */
	d_step {
		Sump_Valve = false; 
		Sump_Pump_1 = false; 
		Sump_Pump_2 = false;
	};
	
	Water_Return_Both_Gen_END:

	/* Sequence complete, return to id to start again if appropriate.*/
	goto id_ctrl_state

	/* --------------------------------------------------------------------------- */
	ON_MANUAL_FEED: skip
	/* turn on valve and pumps */
	d_step {
		Sump_Valve = true; 
		Sump_Pump_1 = true; 
		Sump_Pump_2 = true;
	};
	
	/* Exit condition if manual return turned off */
	if
	:: HMI_Return_Feed == false -> goto id_ctrl_state
	fi;
	/* --------------------------------------------------------------------------- */
}

active proctype hmi()
{
	/* Operator instructions are abstracted to random choice */
	/* Send a random instruction from those that meet the requirements */
	send_instruction:
	atomic {
		if
		/* Turn either generator on, if off */
		:: Gen_A_Active == false -> Gen_A_Active = true
		:: Gen_B_Active == false -> Gen_B_Active = true

		/* Turn either generator off, if on */
		:: Gen_A_Active == true -> Gen_A_Active = false
		:: Gen_B_Active == true -> Gen_B_Active = false

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
		fi;
	};

	/* End if both generators are off and Hydro_Control is in STOP mode */
	/* Otherwise, send another instruction */
	if
	:: Gen_A_Active == false & Gen_B_Active == false & Control_PLC_MODE == false -> skip
	:: else -> goto send_instruction
	fi;
}

ltl reachable_state {
	!<>(
		Flood_Gate_Valve == 0 &&
		Flood_Pump == 0 &&
		Sump_Valve == 1 &&
		Sump_Pump_1 == 1 &&
		Sump_Pump_2 == 1 &&
		Return_Water_Supply_Control == 0 &&
		HMI_Return_Feed == 0 &&
		Gen_A_Status == 1 &&
		Gen_A_Active == 1 &&
		Gen_A_Fan == 1 &&
		Gen_A_GreenLED == 1 &&
		Gen_A_RedLED == 0 &&
		Gen_A_Pump == 1 &&
		Gen_A_Valve == 1 &&
		Gen_B_Status == 1 &&
		Gen_B_Active == 1 &&
		Gen_B_Fan == 1 &&
		Gen_B_GreenLED == 1 &&
		Gen_B_RedLED == 0 &&
		Gen_B_Pump == 1 &&
		Gen_B_Valve == 1 &&
		Tag_2 == 1
	)
}
