import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
EVENTS_FILE = PROJECT_ROOT / "config" / "events.json"

DATA_DIR = PROJECT_ROOT / "data" / "sentinel"


# ---------------------------------------------------------
# CDSE API endpoints
# ---------------------------------------------------------

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)

CATALOGUE_URL = (
    "https://catalogue.dataspace.copernicus.eu"
    "/odata/v1/Products"
)

DOWNLOAD_URL = (
    "https://download.dataspace.copernicus.eu"
    "/odata/v1/Products"
)


# ---------------------------------------------------------
# Load environment
# ---------------------------------------------------------

load_dotenv(ENV_FILE)


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

def get_access_token():
    """Get a CDSE access token using credentials from .env."""

    email = os.getenv("CDSE_EMAIL")
    password = os.getenv("CDSE_PASSWORD")

    if not email:
        raise RuntimeError("CDSE_EMAIL is missing from .env")

    if not password:
        raise RuntimeError("CDSE_PASSWORD is missing from .env")

    data = {
        "client_id": "cdse-public",
        "username": email,
        "password": password,
        "grant_type": "password",
    }

    print("Requesting CDSE access token...")

    response = requests.post(
        TOKEN_URL,
        data=data,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"CDSE authentication failed: "
            f"{response.status_code}\n"
            f"{response.text[:500]}"
        )

    result = response.json()

    token = result.get("access_token")

    if not token:
        raise RuntimeError("CDSE response did not contain an access token.")

    print("CDSE authentication successful.")

    return token


# ---------------------------------------------------------
# Event loading
# ---------------------------------------------------------

def load_events():
    """Load spill events from config/events.json."""

    import json

    if not EVENTS_FILE.exists():
        raise FileNotFoundError(
            f"Events file not found: {EVENTS_FILE}"
        )

    with open(EVENTS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ---------------------------------------------------------
# Sentinel-1 search
# ---------------------------------------------------------

def search_sentinel(
    latitude,
    longitude,
    start_date,
    end_date,
    top=10,
):
    """
    Search Sentinel-1 IW GRD products around an event.

    The point is:
        longitude latitude

    because OData expects:
        POINT(longitude latitude)
    """

    filters = (
        "Collection/Name eq 'SENTINEL-1' "
        "and OData.CSC.Intersects("
        "area=geography'SRID=4326;"
        f"POINT({longitude} {latitude})'"
        ") "
        "and ContentDate/Start gt "
        f"{start_date}T00:00:00.000Z "
        "and ContentDate/Start lt "
        f"{end_date}T23:59:59.999Z "
        "and Attributes/OData.CSC.StringAttribute/any("
        "att:att/Name eq 'productType' "
        "and att/OData.CSC.StringAttribute/Value eq 'IW_GRDH_1S'"
        ")"
    )

    params = {
        "$filter": filters,
        "$orderby": "ContentDate/Start asc",
        "$top": top,
    }

    print()
    print("Searching Sentinel-1 products...")
    print(f"Location : {latitude}, {longitude}")
    print(f"Dates    : {start_date} → {end_date}")
    print("Product  : IW_GRDH_1S")
    print()

    response = requests.get(
        CATALOGUE_URL,
        params=params,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Sentinel-1 search failed: "
            f"{response.status_code}\n"
            f"{response.text[:1000]}"
        )

    return response.json().get("value", [])


# ---------------------------------------------------------
# Print search results
# ---------------------------------------------------------

def print_products(products):
    """Display useful information about search results."""

    if not products:
        print("No Sentinel-1 products found.")
        return

    print("=" * 80)
    print(f"FOUND {len(products)} SENTINEL-1 PRODUCT(S)")
    print("=" * 80)

    for index, product in enumerate(products, start=1):

        product_id = product.get("Id")
        name = product.get("Name")
        size = product.get("ContentLength")
        online = product.get("Online")
        start = product.get("ContentDate", {}).get("Start")

        if size:
            size_gb = size / (1024 ** 3)
            size_text = f"{size_gb:.2f} GB"
        else:
            size_text = "unknown"

        print()
        print(f"[{index}]")
        print(f"ID      : {product_id}")
        print(f"Name    : {name}")
        print(f"Date    : {start}")
        print(f"Size    : {size_text}")
        print(f"Online  : {online}")

    print()
    print("=" * 80)


# ---------------------------------------------------------
# Download
# ---------------------------------------------------------

def download_product(product, token, output_dir):
    """Download one Sentinel-1 product."""

    product_id = product["Id"]
    product_name = product["Name"]

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # CDSE may return the native product content.
    # We keep the catalogue product name as the output name.
    output_file = output_dir / product_name

    if output_file.exists():
        print()
        print(f"Already exists:")
        print(output_file)
        return output_file

    url = f"{DOWNLOAD_URL}({product_id})/$value"

    headers = {
        "Authorization": f"Bearer {token}",
    }

    print()
    print("=" * 80)
    print("DOWNLOADING SENTINEL-1 PRODUCT")
    print("=" * 80)
    print(f"Product : {product_name}")
    print(f"ID      : {product_id}")
    print(f"Output  : {output_file}")
    print()

    response = requests.get(
        url,
        headers=headers,
        stream=True,
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Download failed: {response.status_code}\n"
            f"{response.text[:1000]}"
        )

    total = int(response.headers.get("Content-Length", 0))

    downloaded = 0
    chunk_size = 1024 * 1024

    with open(output_file, "wb") as file:

        for chunk in response.iter_content(
            chunk_size=chunk_size
        ):

            if not chunk:
                continue

            file.write(chunk)
            downloaded += len(chunk)

            if total:
                percent = downloaded * 100 / total
                downloaded_gb = downloaded / (1024 ** 3)
                total_gb = total / (1024 ** 3)

                print(
                    f"\rDownloaded: "
                    f"{downloaded_gb:.2f}/{total_gb:.2f} GB "
                    f"({percent:.1f}%)",
                    end="",
                    flush=True,
                )
            else:
                downloaded_gb = downloaded / (1024 ** 3)

                print(
                    f"\rDownloaded: "
                    f"{downloaded_gb:.2f} GB",
                    end="",
                    flush=True,
                )

    print()
    print()
    print("Download completed.")
    print(f"Saved to: {output_file}")

    return output_file


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Search and download Sentinel-1 data from CDSE."
    )

    parser.add_argument(
        "--event",
        default="wakashio",
        help="Event name from config/events.json",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Maximum number of products to show",
    )

    parser.add_argument(
        "--download",
        type=int,
        help=(
            "Download product by result number. "
            "Example: --download 1"
        ),
    )

    args = parser.parse_args()

    events = load_events()

    if args.event not in events:
        print(
            f"Unknown event: {args.event}"
        )
        print(
            "Available events:"
        )

        for name in events:
            print(f"  - {name}")

        sys.exit(1)

    event = events[args.event]

    latitude = event["latitude"]
    longitude = event["longitude"]
    start_date = event["start_date"]
    end_date = event["end_date"]

    print()
    print("=" * 80)
    print("OCEANEYE - SENTINEL-1 INGESTION")
    print("=" * 80)
    print(f"Event: {event['name']}")
    print("=" * 80)

    products = search_sentinel(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        top=args.top,
    )

    print_products(products)

    if not products:
        return

    # Search-only mode
    if args.download is None:
        print()
        print("Search complete.")
        print()
        print("To download a product, use:")
        print(
            f"python scripts/download_sentinel.py "
            f"--event {args.event} --download 1"
        )
        return

    # Validate selected result
    index = args.download - 1

    if index < 0 or index >= len(products):
        raise ValueError(
            f"Invalid product number: {args.download}"
        )

    # Authentication only when actually downloading
    token = get_access_token()

    event_dir = DATA_DIR / args.event

    download_product(
        product=products[index],
        token=token,
        output_dir=event_dir,
    )


if __name__ == "__main__":
    main()
