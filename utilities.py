from typing import List, Optional, Tuple, Dict

import folium
import geopandas as gpd
import osmnx as ox
import pandas as pd
from dotenv import load_dotenv
import streamlit as st

from constants import Constants


class Utilities():
    def __init__(self):
        '''
        Utility class for clarity and reusability.
        '''
        load_dotenv()

    @staticmethod
    def title_above_navbar():
        '''
        Code from: https://discuss.streamlit.io/t/put-logo-and-title-above-on-top-of-page-navigation-in-sidebar-of-multipage-app/28213/6
        Accessed: 5/3/2024
        By default, Streamlit does not allow for text above the navbar.
        This function adds text above the navbar.
        '''
        css = st.markdown(
                Constants.CSS_TITLE_ABOVE_NAVBAR,
                unsafe_allow_html=True,
            )
        
        return css

    @staticmethod
    def get_center(coordinates: pd.Series) -> Tuple[float, float]:
        '''
        Gets the center of a pd.Series of coordinates.
        '''
        lon = coordinates.x
        lat = coordinates.y
        return (sum(lon) / len(coordinates), sum(lat) / len(coordinates))

    @staticmethod
    def geocode(location: List[str]) -> List[Tuple[float, float]] | None:
        '''
        Geocodes a location or a list of locations.
        '''
        if isinstance(location, str):
            location = [location]

        coordinates = []

        try:
            for loc in location:
                coords = ox.geocode(loc)
                coordinates.append((coords[0], coords[1]))
            return coordinates

        except Exception:
            return None

    @staticmethod
    def format_locations(locations: List[Dict[str, str]]) -> Dict[str, List[str]]:
        '''
        Formats the locations for the TSP solver.
        Converts the list of dictionaries to a dictionary of lists.
        '''

        result = {}
        for item in locations:
            state = item['city']
            address = item['address']
            if state in result:
                result[state] += [address]
            else:
                result[state] = [address]
        return result

    @staticmethod
    def verify_input(locations: pd.DataFrame) -> pd.DataFrame | bool:
        '''
        Verifies the input locations.
        '''
        locations.dropna(inplace=True)

        # Since the depot is being added to the end of the list later,
        # the last location is dropped if it is the same as the first location.
        if locations.iloc[0].equals(locations.iloc[-1]):
            locations = locations[:-1]

        # Need minimum 2 locations to solve the TSP.
        if locations.empty or len(locations) < 2:
            return False

        return locations

    @staticmethod
    def meters_to_km_miles(meters: float) -> Tuple[float, float]:
        '''
        Converts meters to kilometers and miles.
        '''
        km = meters / 1000
        miles = meters / 1609.34
        return km, miles

    @staticmethod
    def dataframe_changes(original: pd.DataFrame, 
                          edited: pd.DataFrame) -> Dict[str, List[pd.Series]]:
        changes = {
            'insertions': [],
            'deletes': [],
        }

        # Get first column (addresses) as a list.
        original_addresses = original.iloc[:, 0].tolist()
        edited_addresses = edited.iloc[:, 0].tolist()

        # If the address is in the edited list but not in the original list, it is an insertion.
        for address in edited_addresses:
            if address not in original_addresses:
                changes['insertions'].append(address)
        # If the address is in the original list but not in the edited list, it is a deletion.
        for address in original_addresses:
            if address not in edited_addresses:
                changes['deletes'].append(address)

        return changes
