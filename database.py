import os
from typing import List, Dict

from dotenv import load_dotenv
import supabase
import pandas as pd

from utilities import Utilities

class Database():
    def __init__(self) -> None:
        load_dotenv()
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        self.client = self.__connect()

    def __connect(self) -> supabase.Client:
        '''
        Private method to connect to the Supabase database.
        '''
        try:
            client = supabase.create_client(self.supabase_url, self.supabase_key)
            return client
        
        except Exception as e:
            print(f'Error connecting to Supabase: {e}')

    def pull(self) -> Dict[str, List[str]]:
        '''
        Pulls all records from the locations table.
        Formats them into Dict[str, List[str]].
        '''
        try:
            response = self.client.from_('locations').select('*').execute()
            locations = response.data 
            locations = Utilities.format_locations(locations)
            return locations
        
        except Exception as e:
            print(f'Error pulling data from Supabase: {e}')
            return {}

    def push(self, city: str, new_locations: pd.DataFrame, original_data: pd.DataFrame) -> bool | str:
        '''
        Uses Utilities function to get insertions and deletions.
        then pushes the changes to the database.
        '''
        changes = Utilities.dataframe_changes(original_data, new_locations)
        # both changes (insertions and deletions) will be counted as one in the success message for simplicity.
        changes_success = 'NO CHANGES MADE'

        if changes['insertions']:
            try:
                self.client.from_('locations').upsert([
                    {'address': change, 'city': city} for change in changes['insertions']]
                    ).execute()
                changes_success = True
            # Dont want to interrupt, hence exception is passed.
            # User will be notified of the error though.
            except Exception:
                pass

        if changes['deletes']:
            # the delete method deletes entries and returns True upon success.
            changes_success = self.__delete(changes['deletes'])
                    
        return changes_success

    def __delete(self, addresses: list) -> bool:
        '''
        Deletes a single record based on the address.
        '''
        try:
            # Could not find a batch delete method, so deleting one by one.
            for address in addresses:
                self.client.from_('locations').delete().eq('address', address).execute()
            return True
        except Exception:
            return False
        
    def delete_city(self, city: str) -> bool:
        '''
        Deletes all records in the DB with the specified city.
        '''
        try:
            self.client.from_('locations').delete().eq('city', city).execute()
            return True
        except Exception as e:
            return False

