import os
import copernicusmarine


OUTPUT_DIR = "data/cmems/wakashio"

# Wakashio area
MIN_LON = 56.5
MAX_LON = 59.0
MIN_LAT = -21.5
MAX_LAT = -19.0

# Wakashio event period
START_DATE = "2020-08-05"
END_DATE = "2020-08-17"

# Historical global wind dataset
DATASET_ID = "cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H"


def download_wind():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Downloading CMEMS historical wind data...")
    print(f"Area: {MIN_LON} to {MAX_LON} longitude")
    print(f"Area: {MIN_LAT} to {MAX_LAT} latitude")
    print(f"Dates: {START_DATE} to {END_DATE}")
    print(f"Dataset: {DATASET_ID}")

    copernicusmarine.subset(
        dataset_id=DATASET_ID,

        variables=[
            "eastward_wind",
            "northward_wind"
        ],

        minimum_longitude=MIN_LON,
        maximum_longitude=MAX_LON,

        minimum_latitude=MIN_LAT,
        maximum_latitude=MAX_LAT,

        start_datetime=START_DATE,
        end_datetime=END_DATE,

        output_directory=OUTPUT_DIR,
        output_filename="wakashio_wind.nc",

        overwrite=True
    )

    print("\nCMEMS wind data downloaded successfully!")
    print(f"Saved to: {OUTPUT_DIR}/wakashio_wind.nc")


if __name__ == "__main__":
    download_wind()
