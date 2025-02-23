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

# %%

import sqlite3
import requests
import zipfile
import io
import re
import pandas as pd
import json
import tqdm

from Raman_helper_functions import find_peak_positions

# %%
def extract_wavelength(filename):
    # Extract the wavelength using regular expression
    wavelength_match = re.search(r'Raman__([\d.]+)__', filename)
    if wavelength_match:
        return wavelength_match.group(1)
    else:
        return None

def extract_file_number(filename):
    # Extract the file number using regular expression
    file_number_match = re.search(r'__(\d+)\.txt$', filename)
    if file_number_match:
        return file_number_match.group(1)
    else:
        return None

def extract_elements(chemical_formula):
    # Extract elements from chemical formula using regular expression
    element_symbols = re.findall(r'[A-Z][a-z]*', chemical_formula)
    return ', '.join(element_symbols)

conn = sqlite3.connect('Raman_database.db')
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
        peak_prominences REAL
    )
'''
cursor.execute(create_table_query)
conn.commit()

zip_files = [
    "excellent_unoriented.zip",
    "custom_spectra.zip"
]

for zip_file_name in zip_files:
    with zipfile.ZipFile(zip_file_name) as zip_ref:
        for filename in tqdm.tqdm(zip_ref.namelist()):
            try:
                with zip_ref.open(filename) as file:
                    content = file.read().decode('utf-8')  # Try to decode as UTF-8
                    df = pd.read_csv(io.StringIO(content), comment="#", names=["Wavenumber", "Intensity"])
            except UnicodeDecodeError:
                print(f"Skipping file {filename} due to UnicodeDecodeError.")
                continue  # Skip this file and move to the next one
            
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
                
            peak_xs, peak_ys, peak_prominences = find_peak_positions(df["Wavenumber"], df["Intensity"]/df["Intensity"].max(), prominence_threshold=0.05, remove_bg=True)

            # Insert into the database
            if len(df) != 0:
                # print(filename)
                cursor.execute("INSERT INTO database_table (filename, mineral_name, rruff_id, wavelength, orientation, file_number, elements, quality, x_data, y_data, peak_xs, peak_ys, peak_prominences) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (filename, mineral_name, rruff_id, wavelength, orientation, file_number, elements, quality, json.dumps(list(df["Wavenumber"])), json.dumps(list(df["Intensity"])), json.dumps(list(peak_xs)), json.dumps(list(peak_ys)), json.dumps(list(peak_prominences))))


conn.commit()

# Print unique mineral names in alphabetical order
cursor.execute("SELECT DISTINCT mineral_name FROM database_table ORDER BY mineral_name")
unique_minerals = cursor.fetchall()
print("Unique Mineral Names:")
for mineral in unique_minerals:
    print(mineral[0])

conn.close()
