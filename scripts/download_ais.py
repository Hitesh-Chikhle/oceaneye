import os
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()

AISHUB_USERNAME = os.getenv("AISHUB_USERNAME")

OUTPUT_DIR = "data/ais/wakashio"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "ais_sample.csv")

# Wakashio area
LAT_MIN = -21.0
LAT_MAX = -19.5
LON_MIN = 57.0
LON_MAX = 58.5


def download_ais():

    # Check username
    if not AISHUB_USERNAME:
        print("ERROR: AISHUB_USERNAME is missing in .env")
        return

    # Create output folder
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # AISHub API
    url = "https://data.aishub.net/ws.php"

    params = {
        "username": AISHUB_USERNAME,
        "format": 1,
        "output": "csv",
        "compress": 0,
        "latmin": LAT_MIN,
        "latmax": LAT_MAX,
        "lonmin": LON_MIN,
        "lonmax": LON_MAX,
    }

    print("Downloading AIS data...")
    print(f"Latitude: {LAT_MIN} to {LAT_MAX}")
    print(f"Longitude: {LON_MIN} to {LON_MAX}")

    try:

        response = requests.get(
            url,
            params=params,
            timeout=60
        )

        response.raise_for_status()

        # Get response text
        data = response.text.strip()

        # Check for AISHub error
        if "Invalid username or password" in data:
            print("\nERROR: AISHub rejected the username.")
            print("Check your AISHUB_USERNAME in .env")
            return

        if not data:
            print("\nERROR: AISHub returned empty data.")
            return

        # Save CSV
        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(data)

        print("\nAIS data downloaded successfully!")
        print(f"Saved to: {OUTPUT_FILE}")

    except requests.exceptions.RequestException as error:

        print("\nERROR connecting to AISHub:")
        print(error)


if __name__ == "__main__":
    download_ais()

