import pandas as pd
import streamlit as st

from utilities import Utilities
from location import Locations
from database import Database
from tsp import TSP

# Streamlit wants this for FutureWarning on some python versions
try:
    pd.set_option('future.no_silent_downcasting', True)
except Exception:
    pass

st.set_page_config(
    page_title="TSP Solver",
    page_icon="📍",
)

Utilities.title_above_navbar()

def main():
    '''
    Main function for the Streamlit home page.
    '''
    st.title('Route Optimizer')
    st.write('Ole Strauss for INSY 4433')
    st.divider()

    DB = Database()
    city_list = DB.pull()
    
    # Add blank option
    city_list['Blank'] = ['']

    if len(city_list) == 1:
        st.warning('Failed to fetch locations from supabase. Please manually enter your locations.')

    selected_city = st.selectbox(
        'Select predefined locations, edit them, or add your own.', list(city_list.keys()))

    if selected_city:
        with st.container():

            st.markdown(body='**Please enter the locations you would like to visit.**',
                        help='Edit the addresses in the table below. You can add or remove rows as needed.')
            st.markdown(body='The first row should be the depot.',
                        help='The depot is the starting and ending point of the route.')
            st.markdown(body='The preferred format is: Street Address, City, State.',
                        help='Example: 123 Main St, Houston, TX.')

            new_locations = st.data_editor(pd.DataFrame({'Locations': city_list[selected_city]}),
                                           num_rows='dynamic',
                                           use_container_width=True)

            if st.button('Solve for optimal route'):

                new_locations.dropna(inplace=True)

                if len(new_locations) < 2:
                    st.warning('Please enter at least two locations.')

                else:
                    progress_bar = st.progress(
                        0, text='Geocoding locations. Please wait.')

                    loc_object = Locations(new_locations.get('Locations'),
                                           progress_callback=lambda prog: progress_bar.progress(prog,
                                                                                                text='Geocoding locations. Please wait.'))
                    if not loc_object:
                        st.error(f'Too few valid locations. Invalid locations: {", ".join(loc_object.error_locations)}. Please try again.')
                        st.rerun()

                    progress_bar.empty()

                    success_message = st.empty()

                    if loc_object.error_locations:
                        if len(loc_object.coordinates) < 2:
                            success_message.error(
                                f'Too few valid locations. Invalid locations: {", ".join(loc_object.error_locations)}. Please try again.')
                            return
                        else:
                            success_message.warning(
                            f"Failed to geocode locations: {','.join(loc_object.error_locations)}. Proceeding with other locations.")
                    else:
                        success_message.success(
                            'All locations geocoded successfully!')

                    with st.spinner('Solving the TSP. Please wait...'):
                        solver = TSP(loc_object.gdf)
                        m = solver.folium_map(html=True)

                    # Clear the success message
                    success_message.empty()

                    m = solver.folium_map(html=True)

                    st.components.v1.html(m, height=450)

                    km, miles = Utilities.meters_to_km_miles(
                        solver.optimal_distance)
                    st.write(
                        f'Total distance: {km:.2f} km ({miles:.2f} miles)')


if __name__ == '__main__':
    main()
