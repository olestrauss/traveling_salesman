from itertools import cycle, permutations
from typing import Dict, List

import folium
import geopandas as gdf
import networkx as nx
import osmnx as ox
import pandas as pd

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from constants import Constants
from utilities import Utilities


class TSP(Constants):
    # Inherit the constants from the Constants class
    def __init__(self, gdf: gdf.GeoDataFrame) -> None:
        # Geography data setup
        self.gdf = gdf
        self.locations = self.gdf.location
        self.streets = self.gdf.street

        # Graph creation
        self.G = self.__create_graph()
        self.nodes = self.__get_nearest_nodes()

        # Google OR-Tools setup
        self.distance_matrix = self.__distance_matrix()
        self.data = self.__create_data_model()
        self.__ortools_setup()

        # Solve the TSP
        self.solution = self.routing.SolveWithParameters(
            self.search_parameters)
        self.path = self.__get_solution_path()
        self.path_between_nodes = self.__solution_to_route()
        # Divide by 100 to account for the scaling of the distance matrix
        self.optimal_distance = self.solution.ObjectiveValue() / self.SCALE_FACTOR

        # Map setup
        self.tsp_route = {
            **{f'{self.streets[0]}: Depot': 0},
            **{self.streets[self.path[i]]: i for i in range(1, len(self.path))}
        }
        self.m = self.folium_map()

    def __create_graph(self,
                       network_type: str = 'drive',
                       dist: int = 10000) -> nx.Graph:
        
        '''
        Creates a graph from the GeoDataFrame.
        '''

        try:    
            G = ox.graph_from_point(Utilities.get_center(
                self.gdf.geometry), network_type=network_type, dist=dist)
        except ox._errors.InsufficientResponseError:
            return None
        
        return G

    def __get_nearest_nodes(self) -> List[int]:
        '''
        Takes the x and y coordinates from the GeoDataFrame,
        and returns a list of the nearest nodes for each location.
        '''

        x = self.gdf.geometry.x
        y = self.gdf.geometry.y

        # I truly do not understand why it wants x=y, and y=x,
        # but it only works like this. I have looked through all documentation.
        # might be this line in the nearest_nodes source code:
        #   points_rad = np.deg2rad(np.array([Y, X]).T) (its Y, X, not X, Y)
        # Lost, but it works...

        nodes = ox.nearest_nodes(self.G, X=y, Y=x)
        self.gdf['nodes'] = nodes

        return nodes

    def __scale_distance_matrix(self, distance_matrix: pd.DataFrame) -> pd.DataFrame:
        '''
        Scales the distance matrix to integers.
        '''
        # Convert diagonal from NaN to 0
        distance_matrix.fillna(0, inplace=True)
        # Scale by a factor of 100
        distance_matrix = distance_matrix * self.SCALE_FACTOR
        return distance_matrix.astype(int)

    def __distance_matrix(self) -> pd.DataFrame:
        '''
        Returns a distance matrix dataframe.
        Distance from every point to every other point.
        '''
        distance_matrix = pd.DataFrame(
            index=self.streets.to_list(), columns=self.streets.to_list())
        paths = {}

        for i, j in permutations(range(len(self.nodes)), 2):
            try:
                distance = nx.shortest_path_length(
                    self.G, source=self.nodes[i], target=self.nodes[j], weight='length')
                distance_matrix.iloc[i, j] = distance

                path = nx.shortest_path(
                    self.G, source=self.nodes[i], target=self.nodes[j], weight='length')
                paths[(self.nodes[i], self.nodes[j])] = path

            except (nx.NodeNotFound, nx.NetworkXNoPath):
                distance_matrix.iloc[i, j] = 0
                paths[(self.nodes[i], self.nodes[j])] = []

        self.paths = paths
        distance_matrix = self.__scale_distance_matrix(distance_matrix)

        return distance_matrix

    def __create_data_model(self, num_vehicles: int = 1, depot: int = 0) -> Dict:
        '''
        Code from: https://developers.google.com/optimization/routing/tsp
        Accessed: 4/17/2024

        Creates a dictionary containing data and settings for the OR-Tools TSP solver.
        '''
        data = {}

        data['distance_matrix'] = self.distance_matrix.values
        data['num_vehicles'] = num_vehicles
        data['depot'] = depot

        return data

    def __distance_callback(self, from_index: int, to_index: int) -> int:
        '''
        Code from: https://developers.google.com/optimization/routing/tsp
        Accessed: 4/17/2024

        Returns the distance between the two nodes.
        '''
        from_node = self.manager.IndexToNode(from_index)
        to_node = self.manager.IndexToNode(to_index)
        return self.data['distance_matrix'][from_node][to_node]

    def __ortools_setup(self) -> None:
        '''
        Code from: https://developers.google.com/optimization/routing/tsp
        Accessed: 4/17/2024

        Sets up the OR-Tools TSP solver.
        '''
        self.manager = pywrapcp.RoutingIndexManager(
            len(self.data['distance_matrix']),
            self.data['num_vehicles'],
            self.data['depot'])
        self.routing = pywrapcp.RoutingModel(self.manager)
        self.transit_callback_index = self.routing.RegisterTransitCallback(
            self.__distance_callback)
        self.routing.SetArcCostEvaluatorOfAllVehicles(
            self.transit_callback_index)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        # Using same algorithm as in my POC: Christofides
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.CHRISTOFIDES
        )

        self.search_parameters = search_parameters

    def __get_solution_path(self) -> List[int]:
        '''
        Returns the optimal route as a list of indexes.
        '''
        index = self.routing.Start(0)
        path = []
        while not self.routing.IsEnd(index):
            path.append(self.manager.IndexToNode(index))
            index = self.solution.Value(self.routing.NextVar(index))

        return path + [self.routing.Start(0)]

    def __solution_to_route(self) -> List[str]:
        '''
        Returns the solution as a list of nodes.
        This is the node representation of streets between locations.
        '''

        # Get the optimal route
        optimal_route = self.path

        # Get the nodes in the optimal route
        nodes_in_route = [self.nodes[i] for i in optimal_route]

        # Get the path between nodes in the optimal route
        path_between_nodes = [self.paths[(node1, node2)] for node1, node2 in zip(
            nodes_in_route, nodes_in_route[1:])]

        return path_between_nodes

    def __create_legend(self) -> str:
        '''
        Creates a legend for the folium map.
        HTML constants are in the Constants class.
        Clicking on the legend will toggle the visibility of the content.
        '''

        legend_html = self.HTML_BASE

        for location, i in self.tsp_route.items():
            legend_html += f"{i}: {location}<br>"

        legend_html += self.HTML_END

        return legend_html

    def __optimal_coords(self) -> List[List[tuple[float, float]]]:
        '''
        Returns a list of coordinates following the optimal route.
        Creates
        '''
        paths_between_locations = []

        for road in self.path_between_nodes:
            nodes_per_road = []
            for node in road:
                nodes_per_road.append(
                    (self.G.nodes[node]['y'], self.G.nodes[node]['x']))

            paths_between_locations.append(nodes_per_road)

        return paths_between_locations

    def folium_map(self, tiles: str = 'cartodb positron', html: bool = False) -> folium.Map | str:
        '''
        Creates a folium map with the optimal route plotted.
        Can also return str html representation of the map.
        '''
        # Create a map. Start at the depot.
        m = folium.Map(location=(self.gdf.geometry.iloc[0].x, self.gdf.geometry.iloc[0].y),
                       zoom_start=13, tiles=tiles)

        optimal_coords = self.__optimal_coords()

        # Cycle through the colors for the routes
        COLORS = cycle(self.COLORS)

        # Loop through the routes and add each one to the map with a different color
        for road in optimal_coords:
            folium.PolyLine(road, color=next(COLORS),
                            weight=3, opacity=0.7).add_to(m)

        # Add marker for depot
        coord = self.G.nodes[self.nodes[0]
                             ]['y'], self.G.nodes[self.nodes[0]]['x']
        folium.Marker(coord,
                      icon=folium.Icon(color='green', icon='home'),
                      popup=f'Depot: {self.streets[0]}').add_to(m)

        # Add markers for the rest of the locations
        # Start at 1 and end at -1 to skip the depot
        for stop in self.path[1:-1]:
            loc = self.streets[stop]
            node = self.nodes[stop]
            coord = self.G.nodes[node]['y'], self.G.nodes[node]['x']
            folium.Marker(coord,
                          icon=folium.Icon(icon='map-marker'),
                          popup=f'Stop {self.tsp_route[loc]}: {loc}').add_to(m)

        # Add legend to the map.
        m.get_root().html.add_child(folium.Element(self.__create_legend()))

        if not html:
            return m

        return m.get_root().render()
