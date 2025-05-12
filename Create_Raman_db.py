# Ramanalysis: Creation of database for interactive comparison and matching of Raman spectra

# Copyright (C) 2025 , Peter Methley

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# %% CONFIGURATION

database_file_name = "Raman_database.db"

urls_to_download = [
    # "https://rruff.info/zipped_data_files/raman/excellent_oriented.zip",
    "https://rruff.info/zipped_data_files/raman/excellent_unoriented.zip",
    # "https://rruff.info/zipped_data_files/raman/fair_oriented.zip",
    # "https://rruff.info/zipped_data_files/raman/fair_unoriented.zip",
    # "https://rruff.info/zipped_data_files/raman/ignore_unoriented.zip",
    # "https://rruff.info/zipped_data_files/raman/poor_oriented.zip",
    # "https://rruff.info/zipped_data_files/raman/poor_unoriented.zip",
    # "https://rruff.info/zipped_data_files/raman/unrated_oriented.zip",
    # "https://rruff.info/zipped_data_files/raman/unrated_unoriented.zip"
]

extra_zip_files = [
    # "custom_spectra.zip"
]

minimum_prominence_threshold = 0.01 # Minimum prominence at which peak locations will be inserted into the database

# %% IMPORTS

import os
import sqlite3
import requests
import zipfile
import io
import re
import pandas as pd
import json
import tqdm
from collections.abc import Iterable

from Raman_helper_functions import find_peak_positions

# %% FUNCTIONS FOR DATABASE CREATION

def extract_wavelength(filename: str) -> str | None:
    "Extracts the measurement wavelength from the given filename using regular expression"
    
    wavelength_match = re.search(r'Raman__([\d.]+)__', filename)
    if wavelength_match:
        return wavelength_match.group(1)
    else:
        return None


def extract_file_number(filename: str) -> str | None:
    "Extracts the ID number from the given filename using a regular expression"
    
    file_number_match = re.search(r'__(\d+)\.txt$', filename)
    if file_number_match:
        return file_number_match.group(1)
    else:
        return None


def extract_elements(chemical_formula: str) -> str:
    "Extracts elements from chemical formula using regular expression"
    
    element_symbols = re.findall(r'[A-Z][a-z]*', chemical_formula)
    return ', '.join(element_symbols)


def insert_data_from_zip(zip_ref: zipfile.ZipFile, zip_file_name: str, cursor: sqlite3.Cursor, prominence_threshold: float) -> None:
    "For each file in the zip file zip_ref, insert data into the database using the sqlite3 cursor. Peaks identified using the prominence threshold"
    
    for filename in tqdm.tqdm(zip_ref.namelist()):
        try:
            with zip_ref.open(filename) as file:
                content = file.read().decode('utf-8')  # Try to decode as UTF-8
                df = pd.read_csv(io.StringIO(content), comment="#", names=["Wavenumber", "Intensity"])
        except UnicodeDecodeError:
            print(f"Skipping file {filename} due to UnicodeDecodeError.")
            continue  # Skip this file and move to the next one
        
        try:
            lines = content.split('\n')
            mineral_name = filename.split('__')[0]
            rruff_id = filename.split('__')[1]
            orientation = filename.split('__')[-3]  # Extract the last part as orientation
            wavelength = extract_wavelength(filename)
            file_number = extract_file_number(filename)
            quality = zip_file_name.split("_")[0]
            
            elements = ""
            for line in lines:
                if line.startswith("##IDEAL CHEMISTRY="):
                    elements = line.split('=')[1]
                    elements = extract_elements(elements)
                    break
                
            peak_xs, peak_ys, peak_prominences = find_peak_positions(df["Wavenumber"], df["Intensity"]/df["Intensity"].max(), prominence_threshold=prominence_threshold, remove_bg=True)

            min_x = df["Wavenumber"].min()
            max_x = df["Wavenumber"].max()

            # Insert into the database
            if len(df) != 0:
                # print(filename)
                cursor.execute("INSERT INTO database_table (filename, mineral_name, rruff_id, wavelength, orientation, file_number, elements, quality, x_data, y_data, peak_xs, peak_ys, peak_prominences, min_x, max_x) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (filename, mineral_name, rruff_id, wavelength, orientation, file_number, elements, quality, json.dumps(list(df["Wavenumber"])), json.dumps(list(df["Intensity"])), json.dumps(list(peak_xs)), json.dumps(list(peak_ys)), json.dumps(list(peak_prominences)), min_x, max_x))
                
        except Exception as e:
            print(f"Skipping file {filename}, due to error: {e}")
            continue
            
    return None


# %% MAIN PROGRAM

def main(database_file_name : str, urls_to_download: Iterable[str], extra_zip_files: Iterable[str], minimum_prominence_threshold: float) -> None:
    "Run the database creation process"

    # Delete the existing database file if it exists
    try:
        os.remove(database_file_name)
    except FileNotFoundError:
        pass

    conn = sqlite3.connect(database_file_name)
    cursor = conn.cursor()
    
    create_table_query = '''
        CREATE TABLE IF NOT EXISTS database_table (
            id INTEGER PRIMARY KEY,
            filename TEXT,
            mineral_name TEXT,
            rruff_id TEXT,
            wavelength TEXT,
            orientation TEXT,
            file_number TEXT,
            elements TEXT,
            quality TEXT,
            x_data REAL,
            y_data REAL,
            peak_xs REAL,
            peak_ys REAL,
            peak_prominences REAL,
            min_x REAL,
            max_x REAL
        )
    '''
    cursor.execute(create_table_query)
    conn.commit()
    
    # Add data from online sources
    for url in urls_to_download:
        print(f"Downloading data from {url}")
        response = requests.get(url)
        if response.status_code == 200:
            with io.BytesIO(response.content) as zip_stream:
                with zipfile.ZipFile(zip_stream) as zip_ref:
                    insert_data_from_zip(zip_ref, os.path.basename(url), cursor, minimum_prominence_threshold)
                    
            conn.commit()
            print(f"Data from {url} processed successfully.")
        else:
            print(f"Failed to download data from {url}")

    # Add data from extra zip files
    for zip_file_name in extra_zip_files:
        with zipfile.ZipFile(zip_file_name) as zip_ref:
            insert_data_from_zip(zip_ref, zip_file_name, cursor, minimum_prominence_threshold)

        conn.commit()
        print(f"Data from {zip_file_name} processed successfully.")

    # Print unique mineral names in alphabetical order
    cursor.execute("SELECT DISTINCT mineral_name FROM database_table ORDER BY mineral_name")
    unique_minerals = cursor.fetchall()
    print("Unique Mineral Names:")
    for mineral in unique_minerals:
        print(mineral[0])

    conn.close()
    
    print("Database creation complete.")
    
    return None

# Run the main program
if __name__ == "__main__":
    main(database_file_name, urls_to_download, extra_zip_files, minimum_prominence_threshold)