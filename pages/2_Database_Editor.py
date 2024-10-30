import streamlit as st
from database import Database
from utilities import Utilities
import pandas as pd

st.set_page_config(page_title='DB Editor', 
                   page_icon='🗃️')

DB = Database()
original_locations = DB.pull()

Utilities.title_above_navbar()

def main() -> None:
    '''
    Main function for the Streamlit database editor page.
    '''
    with st.container():
        st.title('Default Location Editor')
        city_options = sorted(list(original_locations.keys())) + ['Add New City...']
        selected_city = st.selectbox('Select City', options=city_options, index=0)

        if selected_city == 'Add New City...':
            new_city = st.text_input('Enter New City Name')
            if new_city:
                original_locations[new_city] = ['']
                selected_city = new_city

        if selected_city in original_locations:
            original_data = pd.DataFrame({selected_city: original_locations[selected_city]})
            
            edited_data = st.data_editor(original_data, 
                                         num_rows='dynamic', 
                                         use_container_width=True)
            
            if st.button('Save Changes'):
                push_success = DB.push(city=selected_city,
                                new_locations=edited_data.dropna(),
                                original_data=original_data.dropna())
                if push_success == 'NO CHANGES MADE':
                    st.warning('No changes made.')
                else:
                    if push_success:
                        st.success('All changes successfully pushed to the database.')
                    else:
                        st.error('Error pushing changes to the database. Please try again.')
                        
            elif st.button('Delete City'):
                city_deletion = DB.delete_city(selected_city)
                if city_deletion:
                    st.success('City successfully deleted.')
                else:
                    st.error('Error deleting city. Please try again.')
              
main()
