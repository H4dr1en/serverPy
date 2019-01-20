import numpy as np
import pandas as pd
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw


def normalize_list(data_list):
    data_list = np.array(data_list, dtype=float)
    return (data_list - data_list.min()) / ( data_list.max() - data_list.min() )

def create_features(df):
    displacement_list = []
    velocity_list = []
    acceleration_list = []
    angles_list = []
    time_list = []
    abs_list = []
    ord_list = []
    pos_list = []

    for i, row in df.iterrows():
        # Find indexes where time is repeated
        time = row["time"]
        time_diff = np.diff(row["time"])
        index_zero = np.where(time_diff == 0)[0]

        # Delete the values at those indexes
        time = np.delete(time, index_zero)
        time_diff = np.diff(time)

        absx = np.delete(row["abs"], index_zero)
        ordy = np.delete(row["ord"], index_zero)

        abs_diff = np.diff(absx)
        ord_diff = np.diff(ordy)

        displacement = np.sqrt(np.square(abs_diff) + np.square(ord_diff))
        position = np.sqrt(np.square(absx) + np.square(ordy))
        position_diff = np.diff(position)


        with np.errstate(divide='ignore', invalid='ignore'):
            velocity = np.nan_to_num(position_diff / time_diff)
            velocity_diff = np.diff(velocity)
            velocity_diff = np.append(velocity_diff, velocity_diff[-1])
            acceleration = np.nan_to_num(velocity_diff / time_diff)

        angles = np.arctan2(ord_diff, abs_diff)

        displacement_list.append(displacement)
        velocity_list.append(velocity)
        acceleration_list.append(acceleration)
        angles_list.append(angles)
        time_list.append(time)
        abs_list.append(absx)
        ord_list.append(ordy)
        pos_list.append(position)

    df['acceleration'] = acceleration_list
    df['displacement'] = displacement_list
    df['velocity'] = velocity_list
    df['angles'] = angles_list
    df['time'] = time_list
    df['abs'] = abs_list
    df['ord'] = ord_list
    df['position'] = pos_list

    return df



""" Zip two lists of numbers into a list of pairs elements """
def zip_lists(x,y):
    return [[i,j] for i,j in zip(x, y)]


""" Apply fastdtw to two signals """
def fastdtw_curves(c1, c2, c1_time, c2_time):
    val1, val2 = zip_lists(c1, c1_time), zip_lists(c2, c2_time)
    distance, _ = fastdtw(np.array(val1), np.array(val2), dist=euclidean)
    return distance


""" Compute distances for all combinaisons of rows of the two given dataframes"""
def compare_t_f(df_1, df_2, cols, time_col='time'):
    
    df_res = pd.DataFrame(columns=cols)
    
    distances = []
    for i, row_1 in df_1.iterrows():
        for j, row_2 in df_2.iterrows():
            distances = []
            for col in cols:
                distances.append(fastdtw_curves(row_1[time_col], row_2[time_col], row_1[col], row_2[col]))
            row = pd.Series(distances, index=cols)
            df_res = df_res.append(row, ignore_index=True)
            
    return df_res

def preprocess(df):
    columns_to_normalize = ["abs", "ord", "time"]
    df[columns_to_normalize] = df[columns_to_normalize].apply(lambda row: row.apply(normalize_list), axis=1)
    df = create_features(df)
    return df

def merge(x, y):
    return [[i, j] for i, j in zip(x, y)]

def calculate_distances(df):

    cols = ["abs", "ord", "displacement", "position", "velocity", "acceleration", "angles"]
    res = pd.DataFrame(columns=cols) 

    for i, row1 in df.iterrows():
        for j, row2 in df.loc[i+1:].iterrows(): 
            
            distances = {}
                
            for col in cols:
                distances[col] = None
                
                val1 = merge(row1["time"], row1[col])
                val2 = merge(row2["time"], row2[col])

                distance, _ = fastdtw(np.array(val1), np.array(val2), dist=euclidean)
                distances[col] = distance
            
            res = res.append(distances, ignore_index=True)

    return res


def compare_to_true_mean(dists, maxs):
    for col in list(dists):
        if dists[col].iloc[0] > maxs[col].iloc[0] *1.8:
            return False
    return True

def process(req, user):

    cols_feat = ["abs","acceleration","angles","displacement","ord","position","velocity"]

    df1 = pd.DataFrame(columns=["abs", "ord", "time"])
    df2 = pd.DataFrame(columns=["abs", "ord", "time"])
    
    df1 = df1.append(user, ignore_index=True) 
    df2 = df2.append(req, ignore_index=True) 

    if len(df2.index) != 1: # Refusing multiples signatures
        return False

    if len(df1.index) < 5: # Refusing verification if insuffisant saved number of signatures, because verification is not relevant otherwise
        return False

    df1_features = preprocess(df1)
    df2_features = preprocess(df2)
    
    df_dist_trues = calculate_distances(df1_features)

    df_dists = compare_t_f(df1_features, df2_features, cols=cols_feat)

    maxs = pd.DataFrame(df_dist_trues.max()).transpose()     
    dists = pd.DataFrame(df_dists.mean()).transpose()
    
    res = compare_to_true_mean(dists, maxs)

    return res