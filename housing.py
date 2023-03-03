# OA3801 (Comp Methods II)
# Naval Postgraduate School
#
#   Austin McGahan
#
# This simple module includes a few support functions for housing layer.

import pandas as pd
import numpy as np

######################### Dataframe build functions ##############

def build_bah_df(csvfile_bah_wo, csvfile_bah_w):
    #1. List of zip codes and MHAs (sorted_zipmha23.txt)
    sorted_zipmha23_df = pd.read_csv('sorted_zipmha23.txt', sep=" ", header=None, names=["zip_code", "mha"])
    
    #2. List of MHAs and MHA names (mhanames23.txt)
    mhanames23_df = pd.read_csv('mhanames23.txt', sep=";", header=None, names=["mha", "mha_names"])
    mhanames23_df.set_index('mha',inplace=True)
    mhanames23_list = mhanames23_df.index.values.tolist()
    
    #2a. Combine first two sources on mha
    zip_mha_names_df = pd.merge(sorted_zipmha23_df, mhanames23_df, on='mha')
    
    #3. 2023 BAH rates with dependents (bahwo23.txt)
    dbahwo23_df = pd.read_csv(csvfile_bah_wo, sep=',', names=['mha', 
                                      'EO1', 'EO2', 'EO3', 'EO4', 'EO5', 'EO6', 'EO7', 'EO8', 'EO9',
                                      'WO1','WO2','WO3','WO4','WO5', 'O01E', 'O02E', 'O03E',
                                      'O01','O02','O03','O04','O05','O06','O07','O08','O09', 'O010', 'dep_status'])
    dbahwo23_df['dep_status']='WO'
    
    #4. 2023 BAH rates with dependents (bahw23.txt):
    bahw23_df = pd.read_csv(csvfile_bah_w, sep=',', names=['mha', 
                                      'EO1', 'EO2', 'EO3', 'EO4', 'EO5', 'EO6', 'EO7','EO8','EO9',
                                      'WO1','WO2','WO3','WO4','WO5', 'O01E', 'O02E', 'O03E',
                                      'O01','O02','O03','O04','O05','O06','O07','O08','O09', 'O010', 'dep_status'])
    bahw23_df['dep_status']='W'
    bigtest = pd.concat([dbahwo23_df,bahw23_df])
    biggest_test = pd.merge(zip_mha_names_df, bigtest, on='mha')
    #display(zip_mha_names_df, bigtest,biggest_test)
    biggest_test.set_index('zip_code',inplace=True)
    return biggest_test

def build_fmr_df(xlsxfile_fy_safmrs):
    fmr_data_df = pd.read_excel(xlsxfile_fy_safmrs, index_col=0)
    return fmr_data_df

def build_mhp_df(csvfile_RDC_ZIP):
    mhp_df = pd.read_csv(csvfile_RDC_ZIP)
    mhp_df.set_index('postal_code',inplace=True)
    return mhp_df


############### Look up functions ###################

#def lookup_bah_rate(zip_code,dependent_status, rank):
    #dependent_df = biggest_test[biggest_test['dep_status'] == dependent_status] #filter BAH rates by dependent status
    #mil_housing_area = dependent_df.loc[zip_code, 'mha_names'] #look up housing area by zip code and mha names column
    #BAH = dependent_df.loc[zip_code, rank] #look up BAH rate by zip code and rank
    #return BAH, mil_housing_area, zip_code, dependent_status, rank

#Having trouble getting this function to run from housing.py. No issues running directly in notebook

def lookup_bah_rate(zip_code,dependent_status, rank):
    dependent_df = bah_rates[bah_rates['dep_status'] == dependent_status] #filter BAH rates by dependent status
    mil_housing_area = dependent_df.loc[zip_code, 'mha_names'] #look up housing area by zip code and mha names column
    BAH = dependent_df.loc[zip_code, rank] #look up BAH rate by zip code and rank
    return BAH #mil_housing_area, zip_code, dependent_status, rank

#def lookup_fmr(zip_code):
    #FMR0 = fmr_data_df.loc[zip_code, 'SAFMR\n0BR']
    #FMR1 = fmr_data_df.loc[zip_code, 'SAFMR\n1BR']
    #FMR2 = fmr_data_df.loc[zip_code, 'SAFMR\n2BR']
    #FMR3 = fmr_data_df.loc[zip_code, 'SAFMR\n3BR']
    #FMR4 = fmr_data_df.loc[zip_code, 'SAFMR\n4BR']
    #hud_fmr_area = fmr_data_df.loc[zip_code, 'HUD Metro Fair Market Rent Area Name']
    #return print('Fair Market Rent for: HUD Metro FMR Area:', 
                 #hud_fmr_area, '(', zip_code, ')', 
                # ': 0 Bdrm: $', FMR0, 
                # ', 1 Bdrm: $', FMR1,  
                # ', 2 Bdrm: $', FMR2, 
                # ', 3 Bdrm: $', FMR3, 
                # ', 4 Bdrm: $', FMR4) 
                
def lookup_fmr(zip_code, br_number):
    FMR0 = fmr_rates.loc[zip_code, 'SAFMR\n0BR']
    FMR1 = fmr_rates.loc[zip_code, 'SAFMR\n1BR']
    FMR2 = fmr_rates.loc[zip_code, 'SAFMR\n2BR']
    FMR3 = fmr_rates.loc[zip_code, 'SAFMR\n3BR']
    FMR4 = fmr_rates.loc[zip_code, 'SAFMR\n4BR']
    #hud_fmr_area = fmr_rates.loc[zip_code, 'HUD Metro Fair Market Rent Area Name']
    if br_number == 1:
        rate_by_bdrm_standard = FMR1
    elif br_number == 2:
        rate_by_bdrm_standard = FMR2 
    elif br_number == 3:
        rate_by_bdrm_standard = FMR3 
    elif br_number == 4:
        rate_by_bdrm_standard = FMR4 
    return rate_by_bdrm_standard

####################### Objective ###############3
#Score: by zip, keep rank/dep status fixed, score is a percentage (BAH/FMR)
def affordability_rating(zip_code,dependent_status, rank): 
    BAH = lookup_bah_rate(zip_code,dependent_status, rank)
    #BAH Primer Standards for house size (bedroom number) based on rank/dep. status
    if dependent_status == 'W':
        br_number = BAH_WD_standards_dict[rank]
    if dependent_status == 'WO':
        br_number = BAH_WOD_standards_dict[rank]
    FMR = lookup_fmr(zip_code, br_number)
    percentage_covered = BAH/FMR
    #Rating from 0-5 based on percentage of BAH that covers the FMR for standard bdrm number per rank/dep. status
    if percentage_covered < .5:
        affordability_rating = 0
    if 0.5 < percentage_covered <= .65:
        affordability_rating = 1
    if 0.65 < percentage_covered <= .9:
        affordability_rating = 2
    if .9 < percentage_covered < 1:
        affordability_rating = 3
    if percentage_covered == 1:
        affordability_rating = 4
    if percentage_covered > 1:
        affordability_rating = 5
    return affordability_rating

##### Future work ##############

#Metric omitted for current project. Placeholder for future work.
def lookup_median_house_price(zip_code):
    mhp = mhp_rates.loc[zip_code, 'median_listing_price']
    area = mhp_rates.loc[zip_code, 'zip_name']
    listing_count = mhp_rates.loc[zip_code, 'active_listing_count']
    return print('Median House Listing Price(MHP) for: ', area, ',', zip_code, ': $',  round(mhp, 2), ', # of Listings:', listing_count)


mhp_rates = build_mhp_df('RDC_Inventory_Core_Metrics_Zip (3).csv')
mhp_rates.head(3)