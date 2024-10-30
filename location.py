from typing import Callable, Dict, List, Optional, Tuple

import geopandas as gpd
import osmnx as ox
from pandas import Series

class Locations():
    def __init__(self, locations: Series, 
                 progress_callback: Optional[Callable] = None) -> None:
        
        self.progress_callback = progress_callback
        self.error_locations = []

        self.locations = self.init_locations(locations)
        self.coordinates = self.__geocode_locations()
        self.streets = self.get_street()
        self.gdf = self.to_gdf()

    def init_locations(self, locations: Series) -> List[str]:
        '''
        Ensures there are no duplicate locations.
        '''
        if locations.empty:
            return []
        
        start, *rest = locations
        return [start] + list(set(rest))

    def __geocode_locations(self) -> Dict[str, Tuple[float, float]]:
        '''
        Geocodes the locations in the Series.
        Also reports errors to be displayed in the UI.
        '''
        coordinates = {}
        total = len(self.locations)

        for i, location in enumerate(self.locations):
            try:
                coords = ox.geocode(location)
                coordinates[location] = coords

            except Exception:
                self.error_locations.append(location)
                self.locations.remove(location)
            
            if self.progress_callback:
                self.progress_callback(int((i + 1) / total * 100))

        return coordinates

    def get_street(self, lower: Optional[bool] = False) -> List[str]:
        '''
        Returns the street names. Optionally lowercased.
        '''
        if lower:
            return [x.split(',')[0].lower() for x in self.coordinates.keys()]
        else:
            return [x.split(',')[0] for x in self.coordinates.keys()]

    def to_gdf(self) -> gpd.GeoDataFrame:
        '''
        Converts the coordinates to a GeoDataFrame.
        '''
        if len(self.coordinates) < 2:
            return None

        x, y = zip(*self.coordinates.values())

        gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(x=x, y=y))

        gdf['location'] = self.coordinates.keys()
        gdf['street'] = self.streets
        return gdf
