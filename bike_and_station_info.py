import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from get_features import *
import statsmodels.api as sm


def unique_stations(df):
    '''
    Given a dataframe, identify the unique start/end stations
    
    INPUT: DataFrame
    OUTPUT: 1 array of unique start station ids
  
    '''
    #start station name/id and the number of trips for that station
    lst_start_station_name = df.start_station_name.value_counts()
    lst_start_station_id = df.start_station_id.value_counts()

    num_unique_stations = lst_start_station_id.unique().size
    unique_start_sations = df.start_station_id.unique()
    unique_end_stations = df.end_station_id.unique()
    return unique_start_sations

def new_stn_coords(df1, df2):
    '''
    INPUT: 2 lists. 1 list of new station ids
                    1 list of old station ids
    '''

    new_stn = unique_stations(df2)
    curr_stn = unique_stations(df1)
    ps = set(new_stn) - set(curr_stn)
    lst_new = list(ps)
    return lst_new


def stn_coords(df):
    '''
    returns a dictionary with all station_id and coordinate combinations
    '''
    #getting the coordinates from the dataset
    coordinates = np.array(df[['start_station_longitude', 'start_station_latitude']])
    unique_coords = np.unique(coordinates, axis = 0)
    #create a dictionary with
    #station id as key
    #coordinates for the station id as values
    id_coord = {}
    for u in unique_coords:
        k = df.start_station_id[(df.start_station_longitude == u[0]) &(df.start_station_latitude == u[1])].iloc[0]
        id_coord[int(k)] = u
    return id_coord



def euclidean_distance(x, y):
    return np.sqrt(((x-y)**2).sum(axis=1))


def knn_proposed_stn(sub, df1, df2, proposed_stn, num_neighbors = 3):
    '''
    INPUT 3 dataframes, subsetted df, current month's df, and next month's df
            as well as the number of desired neighbors
    OUTPUT dict of knn, dict for id and coordinate combinations for each current and next month


    '''

    #all coordinates for each trip
    coordinates = np.array(df1[['start_station_longitude', 'start_station_latitude']])
    
    #unique coords in df1
    unique_coords = np.unique(coordinates, axis = 0)
    
    #current month
    cm = df1.month.unique()[0]
    
    #get the id and coords for current month
    id_coord_df1 = stn_coords(df1)
    id_coord_df2 = stn_coords(df2)
    
    knn_dict = {}
    baseline_knn = {}
    
    #iterate through each proposed station
    for p in proposed_stn:
        
        #use euclidean_distance to find distances between each point
        dist = euclidean_distance(id_coord_df2.get(p), unique_coords)
        
        #sort the distances from closest to furthest
        potential_neighbors = unique_coords[np.argsort(dist)]
        
        neighbors = np.array([0,0])
        baseline_neighbors = np.array([0,0])
       
        
        #in the list of potential neighbors, use neighbors with more than 30 days of trips
        for pot in potential_neighbors:
            
            #get the station id
            sid = sub.start_station_id[(sub.start_station_longitude==pot[0])\
                                       &(sub.start_station_latitude==pot[1])].unique()[0]

#             if len(cdf.days[cdf.start_station_id==sid].unique())>10:
            baseline_neighbors = np.vstack((neighbors, pot))

            if len(sub.day[(sub.start_station_id==sid) & (sub.month == cm)].unique())>25:
                neighbors = np.vstack((neighbors, pot))

        neighbors = neighbors[1:num_neighbors+1]
        baseline_neighbors = baseline_neighbors[1:num_neighbors+1]


        #list for storing neighboring station ids
        baseline_neighbor_ids = []
        for i in range(num_neighbors):
            baseline_knn_id = sub.start_station_id[(sub.start_station_longitude == baseline_neighbors[i][0]) &(sub.start_station_latitude == baseline_neighbors[i][1])].iloc[0]
            baseline_neighbor_ids.append(int(baseline_knn_id))
        
        #list for storing neighboring station ids
        neighbor_ids = []
        for i in range(num_neighbors):
            knn_id = sub.start_station_id[(sub.start_station_longitude == neighbors[i][0]) &(sub.start_station_latitude == neighbors[i][1])].iloc[0]
            neighbor_ids.append(int(knn_id))

        knn_dict[int(p)] = neighbor_ids
        baseline_knn[int(p)]= baseline_neighbor_ids
    return knn_dict, baseline_knn, id_coord_df1, id_coord_df2


def trips_per_day(df, station_id):
    '''
    number of trips per day, given a station id
    INPUT: df and station id
    OUTPUT: sorted array of trip counts by date
    '''
#regular time series data
    # tseries = df['days'][df.end_station_id == station_id].value_counts().reset_index()
    # tseries = np.array(tseries)
    # tseries = tseries[np.argsort(tseries[:,0])]


#detrend by subtracting average from data
    # data = df['days'][df.end_station_id == station_id].value_counts().reset_index()
    # average = np.array(data.iloc[:,1]).mean()
    # data['diff'] = data.days - average
    # test_s = data.drop('days', axis=1)
    # diff_arr = np.array(test_s)
    # # diff_arr[:,1][diff_arr[:,1]<0] = 0
    # tseries = diff_arr[np.argsort(diff_arr[:,0])]

#detrend by seasonality
    original_df = df[['end_time','days']][df.end_station_id == station_id]
    #change end_time to datetime
    original_df['end_time']= pd.to_datetime(original_df.end_time)
    #group trips by date and count 
    #end time becomes index
    grouped = original_df.groupby(original_df.end_time.dt.date).count()
    #change index to datetime
    grouped.index = pd.to_datetime(grouped.index)
    #create our series
    series = grouped['days']
    #get dummie variables
    day = series.index.dayofweek
    dummies = pd.get_dummies(day).iloc[:, :6]

    #predict seasonal trend
    X = sm.add_constant(dummies.values)
    seasonal_model = sm.OLS(series.values, X).fit()
    seasonal_trend = seasonal_model.predict(X)

    #subtract seasonal trend from original
    detrended_series = np.array(series).T - seasonal_trend
    tseries = np.array(pd.Series(detrended_series).reset_index())
    print(seasonal_trend.size,station_id)
    return tseries,seasonal_trend


def num_malfunctions(df):
    '''
    INPUT: Dataframe with a "malfunction" column
    Sum the number of malfunctions up
    OUTPUT: Tuple with 
            first element as number of malfunctions and
            second element as number of non-malfunctions
    '''

    num_malfunctions = df.malfunction.sum()
    num_working = len(df.malfunction) - num_malfunctions

    return (num_malfunctions, num_working)

def frequent_malfunction(df):
    '''
    Returns the bike id and number of times it "malfunctioned" in a given period
    '''
    return df.bike_id[df.malfunction == True].value_counts()

def same_station(df):
    return df.bike_id[df.start_station_name == df.end_station_name].value_counts()
