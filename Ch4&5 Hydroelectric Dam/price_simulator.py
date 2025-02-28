from datetime import datetime, timedelta
import pandas as pd
class PriceSimulator:
    # Path: location of csv file containing "Date(dt), Time(%H:%M), Price(£00.00)" columns
    def __init__(self, path, scale, duration, loop):
        # Increases how fast a simulated day passes. e.g. 2 = 2x speed -> 1 sim day = 12hrs.
        self.scale_factor = scale
        
        # Number of hours to iterate over
        self.duration = duration
        
        # Whether or not to activate groundhog mode
        self.loop = loop

        # Load data from CSV into Pandas DataFrame
        self.prices = pd.read_csv(path)

        # Process date into appropriate datetypes
        self.prices['Date'] = pd.to_datetime(self.prices['Date'])
        self.prices['Day'] = self.prices['Date'].dt.day
        self.prices['Month'] = self.prices['Date'].dt.month
        self.prices['Year'] = self.prices['Date'].dt.year
        self.prices['DayOfYear'] = self.prices['Date'].dt.dayofyear
        self.prices['Time'] = pd.to_datetime(self.prices['Time'], format='%H:%M').dt.time
        self.prices['Hour'] = self.prices['Time'].apply(lambda x: x.hour)
        self.prices['Minute'] = self.prices['Time'].apply(lambda x: x.minute)

        # Find the most recent date and work back duration hours to ensure a full 24 hours to simulate (simulation starts at 00:00 that day)
        date = self.prices['Date'].max() - timedelta(hours=duration)
        self.day_to_predict = date.day
        self.month_to_predict = date.month
        self.year_to_predict = date.year

        # This is the time that the simulation was run at. Used to calculate how long the simulation has been running for.
        self.time_simulation_started = datetime.now()
        
        # This is the first timestamp within the simulation clock.
        self.first_simulation_time = datetime(year=self.year_to_predict, month=self.month_to_predict, day=self.day_to_predict, hour=0, minute=0, second=0, microsecond=0)
        self.sim_end_point = self.first_simulation_time + timedelta(hours=duration)
        
        self.most_recent_sim_time = self.first_simulation_time
        self.most_recent_timecheck_at = datetime.now()

    # When the simulation is running, time_simulation_started is used to offset first_simulation_time to return the time within the simulated day.
    def get_sim_time(self):
    
        now = datetime.now()
    
        sim_time = self.most_recent_sim_time + ((now - self.most_recent_timecheck_at)*self.scale_factor)
        
        # If looping, reset to start of duration
        if self.loop and sim_time > self.sim_end_point:
            sim_time = sim_time - timedelta(hours=self.duration)
        
        self.most_recent_sim_time = sim_time
        self.most_recent_timecheck_at = now
       
        return sim_time
    
    # Unused method for calculating sim time and then returning a price when called
    def get_sim_price(self):
        current_sim_time = self.get_sim_time()
        relevant_prices = self.prices[
            (self.prices['Date'] == current_sim_time.date()) &
            (self.prices['Time'] <= current_sim_time.time())
        ].sort_values(by='Time', ascending=False)
        #print(relevant_prices.head())
        return relevant_prices['Price'].iloc[0]  # Select the first entry

    # Given a time will return the most recent price entry in the prices dataframe
    def get_sim_price(self, given_time):
        relevant_prices = self.prices[
            (self.prices['Date'].dt.date == given_time.date()) &
            (self.prices['Time'] <= given_time.time())
        ].sort_values(by='Time', ascending=False)
        #print(relevant_prices.head())
        return relevant_prices['Price'].iloc[0]  # Select the first entry

    # Initialises the simulation to start from the current time.
    # Returns first timestamp within the simulation time.
    def start_simulation(self):
        self.time_simulation_started = datetime.now()
        print(f'Simulation starting at {self.time_simulation_started.strftime("%H:%M:%S")}')
        
        self.first_simulation_time = datetime(year=self.year_to_predict, month=self.month_to_predict, day=self.day_to_predict, hour=0, minute=0, second=0, microsecond=0)
        
        self.most_recent_sim_time = self.first_simulation_time
        self.most_recent_timecheck_at = self.time_simulation_started
        
        #Print all prices for the given day.
        #print(self.prices[self.prices['Date'].dt.date == self.first_simulation_time.date()])

        return self.first_simulation_time