#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  6 05:43:21 2023

@author: sam
"""

import folium as fm
from folium.features import DivIcon
from folium import plugins
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon
from fiona import drvsupport
import param
import panel as pn
import re
import branca

class MapGenerator(param.Parameterized):
    '''
    This is the supporting object to handle user parameters and generate the map HTML object.
    '''
    def get_map(self,grid=(38.87194866197945, -77.05625617335261), zoom_start=10):
        return fm.Map(location=grid,zoom_start=zoom_start)
    #map1 = get_map()
    #pn.panel(map1, height=400)

    def lookup_bah_rate(self,zip,dependent_status, rank):
        '''
        
        Parameters
        ----------
        zip : 
            Reference Zip Code of a duty location.
        dependent_status : 
            'W' or 'WO' based on user input.
        rank : 
            Based on availble options in 'grade' param object.

        Returns
        -------
        BAH : 
            If BAH available in BAH_df, returns the value
            Else returns 90% of the Fair Market Rent.

        '''
        try:
            BAH = self.BAH_df[(self.BAH_df.zip_code == str(zip))&(self.BAH_df.dep_status == dependent_status)][rank].values[0] #look up BAH rate by zip code and rank
        except: 
            if dependent_status == 'W':
                br_number = self.BAH_W[rank]
            if dependent_status == 'WO':
                br_number = self.BAH_WO[rank]
            FMR = self.lookup_fmr(zip, br_number)
            BAH = .9*FMR  #If zipcode is not in database, use 90% of FMR based on BAH primer (+/-10%)
        return BAH 

    def lookup_fmr(self,zip_code, br_number):
        '''

        Parameters
        ----------
        zip_code : 
            Zip Code for a reference location.
        br_number : 
            BAH Primer specified standard number of bedrooms based on grade and dependent status.

        Returns
        -------
        FMR
            Fair Market Rent value (40th percentile) for the reference zip code and specified housing standard.

        '''
        FMR_df = self.FMR_df
        county_FMR_df = self.county_FMR_df
        try:
            FMR1 = FMR_df.loc[zip_code, '1BR']
            FMR2 = FMR_df.loc[zip_code, '2BR']
            FMR3 = FMR_df.loc[zip_code, '3BR']
            FMR4 = FMR_df.loc[zip_code, '4BR']
        #If FMR not included by zip code, use county FMR
        except(ValueError):
            FMR1 = county_FMR_df.loc[zip_code, '1BR']
            FMR2 = county_FMR_df.loc[zip_code, '2BR']
            FMR3 = county_FMR_df.loc[zip_code, '3BR']
            FMR4 = county_FMR_df.loc[zip_code, '4BR']

        #If FMR not found for zipcode in counties, use national average (https://www.ushousingdata.com/fair-market-rents)
        except:
            FMR1 = 880
            FMR2 = 1096
            FMR3 = 1416
            FMR4 = 1624
        if br_number == 1:
            FMR = FMR1
        elif br_number == 2:
            FMR = FMR2 
        elif br_number == 3:
            FMR = FMR3 
        elif br_number == 4:
            FMR = FMR4 
        return int(FMR)

    def affordability_rating(self,duty_zip_code,input_zip_code,dependent_status, rank): 
        '''

        Parameters
        ----------
        duty_zip_code : 
            Zip Code of duty location.
        input_zip_code : 
            Zip Code of housing area.
        dependent_status : 
            'W' or 'WO'.
        rank : 
            Based on options from the param selector for grade.

        Returns
        -------
        percentage_covered : 
            Returns percentage the duty BAH covers FMR for a given area.
            Likely greater than 1 due to the comparison of FMR (40th percentile) and BAH (50th percentile)

        '''
        if dependent_status == 'W':
            br_number = self.BAH_W[rank]
        if dependent_status == 'WO':
            br_number = self.BAH_WO[rank]
        BAH = self.lookup_bah_rate(duty_zip_code,dependent_status, rank)
        FMR = self.lookup_fmr(input_zip_code, br_number)
        percentage_covered = BAH/FMR
        return percentage_covered

    def create_support_df(self, duty_location):
        '''
        

        Parameters
        ----------
        duty_location : Grid coordinate of the duty location.

        Returns
        -------
        walk_df : GeoDataFrame
            The likelihood an individual primarily walks if they live in an area.
        crime_df_merge : GeoDataFrame
            The FBI's crime index of incorporated places (cities, towns, ect.).
        school_df_merge : GeoDataFrame
            The average GreatSchools rating of a zipcode.
        recreation_df_nonnull : GeoDataFrame
            The number of breweries in a zipcode.
        zip_df : GeoDataFrame
            The geographies of all zipcodes within MD, VA, and Washington DC.
        BAH_df : DataFrame
            Reference BAH rates nationwide.
        FMR_df : DataFrame
            Reference FMR rates nationwide.
        county_FMR_df : DataFrame
            Reference county FMR rates nationwide.

        '''
        drvsupport.supported_drivers['KML'] = 'rw'

        #build walkability dataframe
        walk_df = gpd.read_file('./Data/Geographies/DC_MD_VA_Blocks.kml', driver = 'KML')
        wi_df = pd.read_csv('./Data/Walkability Index.csv')
        duty_location = Point(duty_location[1],duty_location[0])
        walk = []
        for _, i in walk_df.iterrows():
            score = list(wi_df[(wi_df['STATEFP']== int(i['Name'][15:17])) &
                  (wi_df['COUNTYFP']== int(i['Name'][17:20])) &
                  (wi_df['TRACTCE']== int(i['Name'][20:26])) &
                  (wi_df['BLKGRPCE']==int(i['Name'][26]))
                 ].NatWalkInd)
            if score == list():
                walk.append(10)
            else:
                walk.append(score[0])
        walk_df['Walkability'] = walk

        #build crime index df
        crime_df = pd.read_csv('Data/2020_FBI_Crime_Statistics.csv')
        crime_df = crime_df.fillna(0) #fill in Nan with 0's
        crime_df['Crime Index'].astype('float64')
        #Incorporated Places data frame
        place_df = gpd.read_file('Data/Geographies/DC_MD_VA_Places.kml', driver='KML')
        #regex to get city name
        def find_city_name(cell):
            match = re.search(r'<at><openparen>([A-Za-z ]+)<closeparen>', cell)
            if match:
                return match.group(1)
            else:
                return None
        cities = list()
        for r in place_df.iterrows():
            cities.append(find_city_name(r[1]['Name']))
        place_df['City'] = cities
        #Merging crime and place DataFrames. Not that not every city in zip has reported crime data to FBI data base
        crime_df_merge = pd.merge(place_df, crime_df[['City','Crime Index']], on='City', how = 'left')
        crime_df_merge = crime_df_merge.fillna(0) #filling Nan with 0's
        #setting cities without reported crime to the average of the population reported by FBI
        crime_df_merge.loc[crime_df_merge['Crime Index']==0, ['Crime Index']] = 4.46 
        crime_df_merge.to_crs(4326) #set coords to WGS84

        #build school rating
        schools_df = pd.read_csv('./Data/greatSchools.csv', dtype={'Zip': object})
        schools_df = schools_df.fillna(5) #fill in NaN with 5s
        schools_df['School Rating'] = schools_df['Rating'].astype('int64')
        grouped_df = schools_df.groupby(by='Zip_Code')['School Rating'].mean()
        grouped_df.index = grouped_df.index.astype(str)
        zip_df = gpd.read_file('./Data/Geographies/DC_MD_VA_Zipcodes.kml', driver='KML')
        #regex to get zipcode
        def find_zip_code(cell):
            match = re.search(r'<at><openparen>(\d{5})<closeparen>', cell)
            if match:
                return match.group(1)
            else:
                return None
        zipCodes = list()
        for r in zip_df.iterrows():
            zipCodes.append(find_zip_code(r[1]['Name']))
        zip_df['Zip_Code'] = zipCodes
        #Merging school and zip DataFrames. 
        school_df_merge = pd.merge(zip_df, grouped_df, left_on='Zip_Code', right_index=True)
        school_df_merge = school_df_merge.fillna(0) #filling Nan with 0's
        #setting zips without reported school rating to the average of the population reported by great schools
        school_df_merge.loc[school_df_merge['School Rating']==0, ['School Rating']] = 5

        #build recreation df
        NCRbreweries = pd.read_csv('Data/NCRbreweries.csv')
        NCRbreweries = NCRbreweries.rename(columns={'postal_code' : 'Zip_Code'})
        recreation_df = pd.merge(zip_df, NCRbreweries, on = 'Zip_Code', how = 'left')
        recreation_df_nonnull = recreation_df[recreation_df['name'].notnull()]
        recreation_df_nonnull['Brewery Count'] = 1

        #build affordability df
        #1. Dataframe of zip codes and MHAs (sorted_zipmha23.txt)
        sorted_zipmha23_df = pd.read_csv('Data/sorted_zipmha23.txt', sep=" ", header=None, names=["zip_code", "mha"], dtype={"zip_code":"string"})
        #2. Dataframe of MHAs and MHA names (mhanames23.txt)
        mhanames23_df = pd.read_csv('Data/mhanames23.txt', sep=";", header=None, names=["mha", "mha_names"]) 
        #2a. Combine 1st two df on mha
        zip_mha_names_df = pd.merge(sorted_zipmha23_df, mhanames23_df, on='mha') 
        #3. 2023 BAH rates without dependents (bahwo23.txt)
        dbahwo23_df = pd.read_csv('Data/bahwo23.txt', sep=',', names=['mha', 
                                              'EO1', 'EO2', 'EO3', 'EO4', 'EO5', 'EO6', 'EO7', 'EO8', 'EO9',
                                              'WO1','WO2','WO3','WO4','WO5', 'O01E', 'O02E', 'O03E',
                                              'O01','O02','O03','O04','O05','O06','O07','O08','O09', 'O010', 'dep_status'])
        dbahwo23_df['dep_status']='WO'
        #4. 2023 BAH rates with dependents (bahw23.txt):
        bahw23_df = pd.read_csv('Data/bahw23.txt', sep=',', names=['mha', 
                                              'EO1', 'EO2', 'EO3', 'EO4', 'EO5', 'EO6', 'EO7', 'EO8', 'EO9',
                                              'WO1','WO2','WO3','WO4','WO5', 'O01E', 'O02E', 'O03E',
                                              'O01','O02','O03','O04','O05','O06','O07','O08','O09', 'O010', 'dep_status'])
        bahw23_df['dep_status']='W'
        #5. Stack BAH WO & W dfs from #3 and #4
        bahtot23_df = pd.concat([dbahwo23_df,bahw23_df])
        #6. Combine BAH rates and zipcodes
        BAH_df = pd.merge(zip_mha_names_df, bahtot23_df, on='mha', how='left') 
        #1. Dataframe of Fair Market Rents by metro areas (source: fy2023_safmrs.xlsx)
        FMR_df = pd.read_excel('Data/fy2023_safmrs.xlsx', dtype=str)
        FMR_df = FMR_df[['ZIP\nCode',
                         'SAFMR\n1BR',
                         'SAFMR\n2BR',
                         'SAFMR\n3BR',
                         'SAFMR\n4BR',
                         'HUD Area Code',
                         'HUD Metro Fair Market Rent Area Name']]
        FMR_df.rename(columns={'ZIP\nCode':'zip_code',
                               'SAFMR\n1BR':'1BR',
                               'SAFMR\n2BR':'2BR',
                               'SAFMR\n3BR':'3BR',
                               'SAFMR\n4BR':'4BR'}, inplace = True)
        #2. Dataframe of Fair Market Rents by counties (source: ZIP_COUNTY_122021.xlsx)
        zip_county_df = pd.read_excel('Data/ZIP_COUNTY_122021.xlsx', dtype=str)
        zip_county_df.rename(columns={'county':'fips'}, inplace = True)
        zip_county_df = zip_county_df[['zip', 'fips']]
        county_FMR_df = pd.read_excel('Data/FY23_FMRs.xlsx', dtype=str)
        county_FMR_df.rename(columns={'hud_area_code':'HUD Area Code',
                                      'fmr_1':'1BR',
                                      'fmr_2':'2BR',
                                      'fmr_3':'3BR', 
                                      'fmr_4':'4BR'}, inplace = True)
        county_FMR_df =county_FMR_df[['fips',
                                      '1BR',
                                      '2BR',
                                      '3BR', 
                                      '4BR',
                                      'HUD Area Code', 
                                      'countyname']]
        county_FMR_df['fips'] = county_FMR_df['fips'].str[:5]
        county_FMR_df = pd.merge(zip_county_df, county_FMR_df, on='fips', how='left')

        walk_df.to_crs(4326) #set coords to WGS84
        return walk_df, crime_df_merge, school_df_merge, recreation_df_nonnull, zip_df, BAH_df, FMR_df, county_FMR_df

    def generate_score(self,affordability, crime, recreation, schools, walk, duty_location, grade, dependents,
                       base_df, walk_df, crime_df, school_df, recreation_df,zip_df, BAH_df, FMR_df, county_FMR_df):
        '''
        Creates score dataframe based on user inputs

        Parameters
        ----------
        affordability : TYPE
            DESCRIPTION.
        crime : TYPE
            DESCRIPTION.
        recreation : TYPE
            DESCRIPTION.
        schools : TYPE
            DESCRIPTION.
        walk : TYPE
            DESCRIPTION.
        duty_location : TYPE
            DESCRIPTION.
        grade : TYPE
            DESCRIPTION.
        dependents : TYPE
            DESCRIPTION.
        base_df : TYPE
            DESCRIPTION.
        walk_df : TYPE
            DESCRIPTION.
        crime_df : TYPE
            DESCRIPTION.
        school_df : TYPE
            DESCRIPTION.
        recreation_df : TYPE
            DESCRIPTION.
        zip_df : TYPE
            DESCRIPTION.
        BAH_df : TYPE
            DESCRIPTION.
        FMR_df : TYPE
            DESCRIPTION.
        county_FMR_df : TYPE
            DESCRIPTION.

        Returns
        -------
        score_df : GeoDataFrame
            Contains all metric scores and weighted sum for every census block group (neighborhood) in MD, VA, and Washington DC.
        rent_df : GeoDataFrame
            The precentage of coverage BAH/FMR for every zipcode.

        '''
        centers = base_df.to_crs('+proj=cea').centroid.to_crs(base_df.crs)
        distance = list()
        for point in centers:
            distance.append(point.distance(Point(duty_location[1],duty_location[0])))
        base_df['Distance'] = distance
        rent_df = zip_df.copy()
        rent_df['Rent Affordability'] = rent_df.Zip_Code.apply(lambda x: self.affordability_rating(int(self.duty_zip_code),int(x),self.dependents,self.grade))
        score_df = base_df.copy()
        score_df = base_df.sjoin(crime_df[['geometry','City','Crime Index']], how='left',predicate='within').drop('index_right', axis=1)
        score_df = score_df.sjoin(school_df[['geometry', 'Zip_Code', 'School Rating']], how = 'left', predicate='within').drop('index_right', axis=1)
        score_df = score_df.sjoin(rent_df[['geometry', 'Rent Affordability']], how = 'left', predicate='within').drop('index_right', axis=1)
        score_df = score_df.sjoin(recreation_df[['geometry','name', 'longitude','latitude','Brewery Count']], how='left', predicate='within').drop('index_right', axis=1)
        score_df['Walkability'] = walk_df['Walkability']
        score_df['School Rating'].fillna(5,inplace = True)
        score_df['Brewery Count'].fillna(0,inplace = True)
        score_df['Overall Score'] = (-crime*score_df['Crime Index']/4.46
                                     -self.distance*score_df['Distance']/.1
                                    + walk*score_df['Walkability']/10
                                    + schools*score_df['School Rating']/5
                                    + affordability*score_df['Rent Affordability']
                                    + recreation*score_df['Brewery Count'])
        return score_df, rent_df
    
    def popup_html(self,location):
        '''
        Supporting function to generate html for marker popup table
        '''
        zipcode = location.Zip_Code
        distance = round(location['Distance'],2)*60
        overall_score = round(location['Overall Score'],3)
        affordability = round(location['Rent Affordability'],2)*100
        walkability = location.Walkability
        crime_index = location['Crime Index']                   
        school_rating = location['School Rating']
        brewery_count = location['Brewery Count']
    
        left_col_color = "#19a7bd"
        right_col_color = "#f2f0d3"
        
        html = """<!DOCTYPE html>
    <html>
    <head>
    <h4 style="margin-bottom:10"; width="200px">{}</h4>""".format(zipcode) + """
    </head>
        <table style="height: 126px; width: 350px;">
    <tbody>
    <tr>
    <td style="background-color: """+ left_col_color +""";"><span style="color: #ffffff;">Distance</span></td>
    <td style="width: 150px;background-color: """+ right_col_color +""";">{}</td>""".format(distance) + """
    </tr>
    <tr>
    <td style="background-color: """+ left_col_color +""";"><span style="color: #ffffff;">Overall Score</span></td>
    <td style="width: 150px;background-color: """+ right_col_color +""";">{}</td>""".format(overall_score) + """
    </tr>
    <tr>
    <td style="background-color: """+ left_col_color +""";"><span style="color: #ffffff;">Rent Affordability</span></td>
    <td style="width: 150px;background-color: """+ right_col_color +""";">{}</td>""".format(affordability) + """
    </tr>
    <tr>
    <td style="background-color: """+ left_col_color +""";"><span style="color: #ffffff;">Walkability</span></td>
    <td style="width: 150px;background-color: """+ right_col_color +""";">{}</td>""".format(walkability) + """
    </tr>
    <tr>
    <td style="background-color: """+ left_col_color +""";"><span style="color: #ffffff;">Crime Index</span></td>
    <td style="width: 150px;background-color: """+ right_col_color +""";">{}</td>""".format(crime_index) + """
    </tr>
    <tr>
    <td style="background-color: """+ left_col_color +""";"><span style="color: #ffffff;">School Rating</span></td>
    <td style="width: 150px;background-color: """+ right_col_color +""";">{}</td>""".format(school_rating) + """
    </tr>
    <tr>
    <td style="background-color: """+ left_col_color +""";"><span style="color: #ffffff;">Brewery Count</span></td>
    <td style="width: 150px;background-color: """+ right_col_color +""";">{}</td>""".format(brewery_count) + """
    </tr>
    </tbody>
    </table>
    </html>
    """
        return html

    def add_map_points(self,m, score, points_count, duty_location):
        '''
        Adds number of specified markers to the map based on the score dataframe

        Parameters
        ----------
        m : folium.map
            Base map.
        score : GeoDataFrame
            Contains all metrics for every census block group.
        points_count : param.Integer
            Number of markers to be placed on the map.
        duty_location : param.XYCoordinate
            Location of duty.

        Returns
        -------
        None.

        '''
        fm.Marker(duty_location, 
              popup = 'Duty Location', 
              icon=fm.Icon(color='gray', prefix='fa', icon='briefcase')).add_to(m)
        i = 1
        #.3 corresponds to roughly 18nm of distance (.3*60nm/deg)
        duty_location = Point(duty_location[1],duty_location[0])
        marker_lats = [duty_location.y]
        marker_longs = [duty_location.x]
        for _,location in score[score['Distance'] <= .3].sort_values(
                'Overall Score',ascending=False)[:points_count].iterrows():
            point = location.geometry.centroid
            number_icon = plugins.BeautifyIcon(
                border_color="bleck",
                text_color="black",
                number=i,
                background_color = 'lightgrey',
                iconShape = 'marker'
            )
            html = self.popup_html(location)
            #iframe = branca.element.IFrame(html=html,width=510,height=280)
            popup = fm.Popup(fm.Html(html, script=True), max_width=500)
            fm.Marker((point.y,point.x), 
                     icon=number_icon,
                     popup = popup
                     ).add_to(m)
            marker_lats.append(point.y)
            marker_longs.append(point.x)
            i += 1
        m.fit_bounds([(min(marker_lats),min(marker_longs)),(max(marker_lats),max(marker_longs))])

    def create_choro(self,map, df, name):
        '''
        

        Parameters
        ----------
        map : folium.map
            Base map.
        df : GeoDataframe
            Contains geography and metric to be displayed.
        name : str
            Name of metric to be displayed.

        Returns
        -------
        None.

        '''
        choro = fm.FeatureGroup(name, show=False).add_to(map)
        choropleth = fm.Choropleth(df,
                     data=df,
                     key_on='feature.properties.Name',
                     columns=['Name',name],
                     fill_color='RdYlGn',
                     line_weight=0.1,
                     line_opacity=0.5,
                     legend_name=name).geojson.add_to(choro)

    #dictionary for bedroom housing standards(# of bedrms) by rank, dep status
    BAH_WD_standards_dict = {'EO1': 2,'EO2': 2, 'EO3': 2, 'EO4': 2, 'EO5': 2, 'EO6': 3, 'EO7': 3, 'EO8': 3, 'EO9': 3,
                             'WO1': 3,'WO2': 3,'WO3': 3,'WO4': 3,'WO5': 3, 
                             'O01E': 3, 'O02E': 3, 'O03E': 3,
                             'O01': 2,'O02': 2,'O03': 3,'O04': 3,'O05': 4,'O06': 4,'O07': 4,'O08': 4,'O09': 4, 'O010': 4}
    BAH_WOD_standards_dict = {'EO1': 1, 'EO2': 1, 'EO3': 1, 'EO4': 1, 'EO5': 1, 'EO6': 2, 'EO7': 2, 'EO8': 2, 'EO9': 2,
                              'WO1': 2,'WO2': 2,'WO3': 2,'WO4': 3,'WO5': 3, 
                              'O01E': 2, 'O02E': 2, 'O03E': 3,
                              'O01': 2, 'O02': 2,'O03': 2,'O04': 3,'O05': 3,'O06': 3,'O07': 3,'O08': 3,'O09': 3, 'O010': 3}
    #Source: BAH Primer: https://media.defense.gov/2022/Jun/23/2003023204/-1/-1/0/BAH-PRIMER.PDF
    
    duty_grid = param.XYCoordinates((38.87194866197945,-77.05625617335261))
    grade = param.Selector(BAH_WD_standards_dict.keys(), default = 'O04', doc='Used in BAH/FMR Calculation')
    dependents = param.Selector(['W', 'WO'], default = 'W', doc='Used in BAH/FMR Calculation')
    walkability = param.Integer(4, bounds=(0,10), doc='User defined weight of relative importance')
    crime = param.Integer(8, bounds=(0,10), doc='User defined weight of relative importance')
    affordability = param.Integer(10,bounds=(0,10), doc='User defined weight of relative importance')
    school_quality = param.Integer(7, bounds=(0,10), doc='User defined weight of relative importance')
    recreation = param.Integer(5,bounds=(0,10), doc='User defined weight of relative importance')
    points_count = param.Integer(5, bounds=(1,10), doc='Number of markers to place on the map')
    distance = param.Integer(8, bounds=(0,10), doc='User defined weight of relative importance')
    update_map = param.Action(lambda x: x.param.trigger('update_map'), doc='Action object tied to GUI button which initiates a map refresh')
    #show = param.Action() #button to launch server version of app in jupyter notebook
        
    def __init__(self, **params):
        super().__init__(**params)
        
        self.BAH_W = {'EO1': 2,'EO2': 2, 'EO3': 2, 'EO4': 2, 'EO5': 2, 'EO6': 3, 'EO7': 3, 'EO8': 3, 'EO9': 3,
                             'WO1': 3,'WO2': 3,'WO3': 3,'WO4': 3,'WO5': 3, 
                             'O01E': 3, 'O02E': 3, 'O03E': 3,
                             'O01': 2,'O02': 2,'O03': 3,'O04': 3,'O05': 4,'O06': 4,'O07': 4,'O08': 4,'O09': 4, 'O010': 4}
        self.BAH_WO = {'EO1': 1, 'EO2': 1, 'EO3': 1, 'EO4': 1, 'EO5': 1, 'EO6': 2, 'EO7': 2, 'EO8': 2, 'EO9': 2,
                              'WO1': 2,'WO2': 2,'WO3': 2,'WO4': 3,'WO5': 3, 
                              'O01E': 2, 'O02E': 2, 'O03E': 3,
                              'O01': 2, 'O02': 2,'O03': 2,'O04': 3,'O05': 3,'O06': 3,'O07': 3,'O08': 3,'O09': 3, 'O010': 3}
        
        self.duty_location = self.duty_grid
        
        self.walk_df, self.crime_df, self.school_df, self.recreation_df,self.zip_df, self.BAH_df, self.FMR_df, self.county_FMR_df = self.create_support_df(self.duty_location)
        
        self.base_df = self.walk_df.drop('Walkability', axis=1)
        self.duty_zip_code = self.zip_df[self.zip_df.contains(Point(self.duty_location[1],self.duty_location[0]))].Zip_Code.iloc[0]
        self.map = self.get_map(self.duty_location)
        self.html_pane = pn.pane.HTML(sizing_mode="scale_both", min_height=400)    
        self._update_map()
        self.show = self.show_using_server
    
    @param.depends('update_map', watch=True) #watches for user pressing update map button and executes following lines
    def _update_map(self):
        '''
        Refreshes map object when user intiates via button on the GUI

        Returns
        -------
        None.

        '''
        self.map = self.get_map(self.duty_location)
        self.duty_location = self.duty_grid
        self.duty_zip_code = self.zip_df[self.zip_df.contains(Point(self.duty_location[1],self.duty_location[0]))].Zip_Code.iloc[0]
        self.score_df, self.rent_df = self.generate_score(self.affordability, self.crime, self.recreation, self.school_quality, self.walkability, 
                                       self.duty_location, self.grade, self.dependents,
                                       self.base_df, self.walk_df, self.crime_df, self.school_df, self.recreation_df,
                                       self.zip_df, self.BAH_df, self.FMR_df, self.county_FMR_df)
        self.add_map_points(self.map, self.score_df, self.points_count, self.duty_location)
        self.create_choro(self.map, self.rent_df, 'Rent Affordability')
        self.create_choro(self.map, self.walk_df, 'Walkability')
        self.create_choro(self.map, self.crime_df, 'Crime Index')
        self.create_choro(self.map, self.school_df, 'School Rating')
        self.create_choro(self.map, self.recreation_df, 'Brewery Count')
        fm.LayerControl().add_to(self.map)
        self.html_pane.object = self.map #crux step to refresh the map with new inputs
        
    def show_using_server(self):
        '''
        Supporing function for use in jupyter notebook to launch server version of the app
        '''
        self.view.show()
        
app = MapGenerator()
dashboard = pn.Tabs(('Inputs',pn.Column(
                                pn.Row(pn.Column(
                                            app.param.duty_grid,
                                            app.param.grade,
                                            app.param.dependents,
                                            app.param.points_count,
                                            
                                            sizing_mode="stretch_width", min_height=400,
                                        ),
                                        pn.Column(
                                            app.param.distance,
                                            app.param.affordability,
                                            app.param.crime,
                                            app.param.school_quality,
                                            app.param.walkability,
                                            app.param.recreation
                                )),
                                app.param.update_map,
                                #self.param.show #button to launch server version in jupyter notebook
                            )),
                    ('Map', app.html_pane))
dashboard.show()