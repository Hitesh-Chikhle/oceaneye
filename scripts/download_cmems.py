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

# Historical global ocean physics reanalysis
DATASET_ID = "cmems_mod_glo_phy_my_0.083deg_P1D-m"


def download_cmems():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Downloading CMEMS historical ocean current data...")
    print(f"Area: {MIN_LON} to {MAX_LON} longitude")
    print(f"Area: {MIN_LAT} to {MAX_LAT} latitude")
    print(f"Dates: {START_DATE} to {END_DATE}")
    print(f"Dataset: {DATASET_ID}")

    copernicusmarine.subset(
        dataset_id=DATASET_ID,

        variables=["uo", "vo"],

        minimum_longitude=MIN_LON,
        maximum_longitude=MAX_LON,

        minimum_latitude=MIN_LAT,
        maximum_latitude=MAX_LAT,

        start_datetime=START_DATE,
        end_datetime=END_DATE,

        minimum_depth=0,
        maximum_depth=10,

        output_directory=OUTPUT_DIR,
        output_filename="wakashio_currents.nc",

        overwrite=True
    )

    print("\nCMEMS current data downloaded successfully!")
    print(f"Saved to: {OUTPUT_DIR}/wakashio_currents.nc")


if __name__ == "__main__":
    download_cmems()
