import os
import logging
import base64
import aiofiles
import aiohttp
import json
import time  # Import for cache-busting
import stat  # Import for file permissions
import shutil
import asyncio

_LOGGER = logging.getLogger(__name__)

DOMAIN = "smartiPowerFlow"

GITHUB_REPO_URL = "https://github.com/Prosono/SMARTiPowerFlow/contents/"
PACKAGES_URL = GITHUB_REPO_URL + "packages/"
DASHBOARDS_URL = GITHUB_REPO_URL + "dashboards/"
SMARTIUPDATER_URL = GITHUB_REPO_URL + "custom_components/smartipowerflow/"
#NODE_RED_FLOW_URL = GITHUB_REPO_URL + "node-red-flows/"
#THEMES_URL = GITHUB_REPO_URL + "themes/smarti_themes/"
#IMAGES_URL = GITHUB_REPO_URL + "www/images/smarti_images/"
#CUSTOM_CARD_RADAR_URL = GITHUB_REPO_URL + "www/community/weather-radar-card/"

VERSION_URL = GITHUB_REPO_URL + "version.json"

PACKAGES_PATH = "/config/packages/"
#THEMES_PATH = "/config/themes/smarti_themes/"
DASHBOARDS_PATH = "/config/dashboards/"
SMARTIUPDATER_PATH = "/config/custom_components/smartiupdater/"
#IMAGES_PATH = "/config/www/images/smarti_images"
#NODE_RED_PATH = "/share/node-red-flows/"
#CUSTOM_CARD_RADAR_PATH = "/config/www/community/weather-radar-card/"

PACKAGES_FILES_TO_DELETE = [
    "smarti_dashboard_package_powerflow.yaml",
]

DASHBOARDS_FILES_TO_DELETE = {
    "SMARTi_Power_Control_Page_Test.yaml",
}

_LOGGER = logging.getLogger(__name__)

def log_file_size(filepath: str, description: str):
    """Log the size of a file with a description."""
    try:
        file_size = os.path.getsize(filepath)
        _LOGGER.info(f"{description} - File size of {filepath}: {file_size} bytes")
    except Exception as e:
        _LOGGER.error(f"Failed to get file size for {filepath}: {str(e)}")

def ensure_writable(filepath: str):
    """Ensure that the file has writable permissions."""
    try:
        # Set the file permissions to be writable by the user (owner)
        os.chmod(filepath, stat.S_IWUSR | stat.S_IRUSR)
        _LOGGER.info(f"Permissions set to writable for {filepath}.")
    except Exception as e:
        _LOGGER.error(f"Failed to set writable permissions for {filepath}: {str(e)}")

def ensure_directory_exists(directory_path: str):
    """Ensure that a directory exists."""
    if not os.path.exists(directory_path):
        _LOGGER.error(f"The directory {directory_path} does not exist.")
        raise FileNotFoundError(f"The directory {directory_path} does not exist.")
    else:
        _LOGGER.info(f"Directory {directory_path} exists.")

async def download_file(url: str, dest: str, session: aiohttp.ClientSession):
    try:
        _LOGGER.info(f"Attempting to download file from {url} to {dest}")

        # Ensure 'dest' is the full path to a file, not a directory
        if os.path.isdir(dest):
            dest = os.path.join(dest, 'flows.json')  # Ensure saving to file, not directory

        async with session.get(url) as response:
            response.raise_for_status()
            content = await response.read()

            async with aiofiles.open(dest, "wb") as file:
                await file.write(content)

        _LOGGER.info(f"File successfully downloaded and saved to {dest}")
    except aiohttp.ClientError as http_err:
        _LOGGER.error(f"HTTP error occurred while downloading {url}: {http_err}")
    except Exception as e:
        _LOGGER.error(f"Error occurred while downloading {url}: {str(e)}")

async def get_files_from_github(url: str, session: aiohttp.ClientSession):
    try:
        _LOGGER.info(f"Fetching file list from {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            files = await response.json()

            _LOGGER.debug(f"API response from {url}: {files}")

            # Check if 'files' is a list (directory) or a dictionary (single file)
            if isinstance(files, list):
                file_urls = [file['download_url'] for file in files if file.get('type') == 'file']
                _LOGGER.info(f"Found {len(file_urls)} files at {url}")
            elif isinstance(files, dict):
                # Handle case where a single file dict is returned
                if 'download_url' in files:
                    file_urls = [files['download_url']]
                    _LOGGER.info(f"Found a single file at {url}")
                else:
                    _LOGGER.error(f"No download URL found for the file at {url}")
                    return []
            else:
                _LOGGER.error(f"Unexpected format from {url}")
                return []

            return file_urls
    except aiohttp.ClientError as http_err:
        _LOGGER.error(f"HTTP error occurred while fetching file list from {url}: {http_err}")
        return []
    except Exception as e:
        _LOGGER.error(f"Error occurred while fetching file list from {url}: {str(e)}")
        return []

def ensure_directory(path: str):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            _LOGGER.info(f"Created directory {path}")
        else:
            _LOGGER.info(f"Directory {path} already exists")
    except Exception as e:
        _LOGGER.error(f"Error creating directory {path}: {str(e)}")


async def clear_specific_files(directory: str, files_to_delete: list):
    """Delete only specific files in the given directory."""
    for filename in files_to_delete:
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            await asyncio.to_thread(os.remove, file_path)
            _LOGGER.info(f"Deleted file: {file_path}")
        else:
            _LOGGER.info(f"File {file_path} does not exist or is not a file.")


async def clear_directory(directory_path: str):
    """Delete all files in the specified directory asynchronously."""
    try:
        if os.path.exists(directory_path):
            # Use asyncio.to_thread to run the blocking shutil.rmtree call in a separate thread
            await asyncio.to_thread(shutil.rmtree, directory_path)
            await asyncio.to_thread(os.makedirs, directory_path)  # Recreate the directory asynchronously
            _LOGGER.info(f"Cleared and recreated directory: {directory_path}")
        else:
            await asyncio.to_thread(os.makedirs, directory_path)  # Create the directory if it doesn't exist
            _LOGGER.info(f"Directory {directory_path} did not exist, so it was created.")
    except Exception as e:
        _LOGGER.error(f"Failed to clear directory {directory_path}: {str(e)}")

async def update_files(session: aiohttp.ClientSession, config_data: dict):
    # Clear the packages and dashboards directories before downloading new files
    #await clear_directory(PACKAGES_PATH)   # Await the coroutine
    await clear_specific_files(PACKAGES_PATH, PACKAGES_FILES_TO_DELETE)
    await clear_specific_files(DASHBOARDS_PATH, DASHBOARDS_FILES_TO_DELETE)
    #await clear_directory(DASHBOARDS_PATH) # Await the coroutine

    ensure_directory(PACKAGES_PATH)
    ensure_directory(DASHBOARDS_PATH)
    ensure_directory(SMARTIUPDATER_PATH)
    #ensure_directory(THEMES_PATH)
    #ensure_directory(IMAGES_PATH)
    #ensure_directory(NODE_RED_PATH)
    #nsure_directory(CUSTOM_CARD_RADAR_PATH)

    # Get and download package files
    package_files = await get_files_from_github(PACKAGES_URL, session)
    for file_url in package_files:
        if file_url:
            file_name = os.path.basename(file_url)
            dest_path = os.path.join(PACKAGES_PATH, file_name)
            _LOGGER.info(f"Saving package file to {dest_path}")
            await download_file(file_url, dest_path, session)

    # Get and download dashboard files
    if config_data.get("update_dashboards"):
        dashboard_files = await get_files_from_github(DASHBOARDS_URL, session)
        for file_url in dashboard_files:
            if file_url:
                file_name = os.path.basename(file_url)
                dest_path = os.path.join(DASHBOARDS_PATH, file_name)
                _LOGGER.info(f"Saving dashboard file to {dest_path}")
                await download_file(file_url, dest_path, session)

    # Get and download custom component files
    smartiupdater_files = await get_files_from_github(SMARTIUPDATER_URL, session)
    for file_url in smartiupdater_files:
        if file_url:
            file_name = os.path.basename(file_url)
            dest_path = os.path.join(SMARTIUPDATER_PATH, file_name)
            _LOGGER.info(f"Saving SmartiUpdater file to {dest_path}")
            await download_file(file_url, dest_path, session)

    # Download Node-RED files and log at each step
 #   if config_data.get("update_node_red"):
 #       node_red_files = await get_files_from_github(NODE_RED_FLOW_URL, session)
 #       for file_url in node_red_files:
 #           if file_url:
 #               file_name = os.path.basename(file_url)  # This should be 'flows.json'
 #               dest_path = os.path.join(NODE_RED_PATH, file_name)  # Correctly append 'flows.json'
 #               _LOGGER.info(f"Saving Node-RED file to {dest_path}")
 #               await download_file(file_url, dest_path, session)

#        _LOGGER.info("Starting merge of strømpriser flow.")
#        await merge_strømpriser_flow(session)

    # Get and download Themes files
    #themes_files = await get_files_from_github(THEMES_URL, session)
    #for file_url in themes_files:
    #    if file_url:
    #        file_name = os.path.basename(file_url)
    #        dest_path = os.path.join(THEMES_PATH, file_name)
    #        _LOGGER.info(f"Saving themes file to {dest_path}")
    #        await download_file(file_url, dest_path, session)

    # Get and download IMAGE files
    #image_files = await get_files_from_github(IMAGES_URL, session)
    #for file_url in image_files:
    #    if file_url:
    #        file_name = os.path.basename(file_url)
    #        dest_path = os.path.join(IMAGES_PATH, file_name)
    #        _LOGGER.info(f"Saving image file to {dest_path}")
    #        await download_file(file_url, dest_path, session)

    # Get and download CUSTOM CARDS files
    #radar_card_files = await get_files_from_github(CUSTOM_CARD_RADAR_URL, session)
    #for file_url in radar_card_files:
    #    if file_url:
    #        file_name = os.path.basename(file_url)
    #        dest_path = os.path.join(CUSTOM_CARD_RADAR_PATH, file_name)
    #        _LOGGER.info(f"Saving card files to {dest_path}")
    #        await download_file(file_url, dest_path, session)



async def get_latest_version(session: aiohttp.ClientSession):
    try:
        cache_buster = f"?nocache={str(time.time())}"
        async with session.get(VERSION_URL + cache_buster) as response:
            response.raise_for_status()
            version_info = await response.json()
            _LOGGER.debug(f"Fetched version info: {version_info}")

            # Decode the base64 content
            encoded_content = version_info.get("content", "")
            if encoded_content:
                decoded_content = base64.b64decode(encoded_content).decode("utf-8")
                version_data = json.loads(decoded_content)
                latest_version = version_data.get("version", "unknown")
                return latest_version
            else:
                _LOGGER.error("No content found in the version info.")
                return "unknown"
    except aiohttp.ClientError as http_err:
        _LOGGER.error(f"HTTP error occurred while fetching version info: {http_err}")
        return "unknown"
    except Exception as e:
        _LOGGER.error(f"Error occurred while fetching version info: {str(e)}")
        return "unknown"

async def check_for_update(session: aiohttp.ClientSession, current_version: str):
    try:
        latest_version = await get_latest_version(session)
        _LOGGER.debug(f"Current version: {current_version}, Latest version: {latest_version}")
        return current_version != latest_version, latest_version
    except aiohttp.ClientError as http_err:
        _LOGGER.error(f"HTTP error occurred while checking for update: {http_err}")
        return False, "unknown"
    except Exception as e:
        _LOGGER.error(f"Error occurred while checking for update: {str(e)}")
        return False, "unknown"

async def update_manifest_version(latest_version: str):
    manifest_file = "/config/custom_components/smartipowerflow/manifest.json"
    try:
        async with aiofiles.open(manifest_file, 'r+') as file:
            manifest_data = json.loads(await file.read())
            manifest_data['version'] = latest_version
            await file.seek(0)
            await file.write(json.dumps(manifest_data, indent=4))
            await file.truncate()
        _LOGGER.info(f"Updated manifest file version to {latest_version}")
    except Exception as e:
        _LOGGER.error(f"Error updating manifest file: {str(e)}")



# # Implement the merge function for Node-RED flows
# async def merge_strømpriser_flow(session: aiohttp.ClientSession):
#     strømpriser_file_url = os.path.join(NODE_RED_PATH, 'flows.json')  # Correct path to local flows.json
#     temp_file_url = os.path.join(NODE_RED_PATH, 'temp_flows.json')    # Temporary path for downloaded flows.json

#     # Function to set file permissions
#     def set_file_permissions(filepath: str):
#         """Set the file permissions to ensure it's writable."""
#         try:
#             if os.path.isfile(filepath):  # Ensure it's a file
#                 os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR)  # Read and write permissions for the owner
#                 _LOGGER.info(f"Permissions set to writable for {filepath}.")
#             else:
#                 _LOGGER.error(f"{filepath} is not a file. Cannot set permissions.")
#         except Exception as e:
#             _LOGGER.error(f"Failed to set permissions for {filepath}: {str(e)}")

#     # Download the strømpriser flow (flows.json) from GitHub to a temporary location
#     await download_file(NODE_RED_FLOW_URL + "flows.json", temp_file_url, session)

#     # Ensure the existing flows.json file is present at the local path
#     if not os.path.exists(strømpriser_file_url):
#         _LOGGER.error(f"The file {strømpriser_file_url} does not exist. Exiting merge.")
#         return

#     log_file_size(strømpriser_file_url, "Before merge")

#     try:
#         # Read the existing flows.json from the local path
#         async with aiofiles.open(strømpriser_file_url, 'r') as file:
#             existing_flows = json.loads(await file.read())

#         # Read the newly downloaded flows.json from GitHub
#         async with aiofiles.open(temp_file_url, 'r') as file:
#             new_flows = json.loads(await file.read())

#         # Find the "Strømpriser" flow in the new_flows data
#         strømpriser_flow = next((flow for flow in new_flows if flow.get('label') == 'Strømpriser'), None)

#         if strømpriser_flow:
#             _LOGGER.debug(f"Found strømpriser flow: {strømpriser_flow}")
#         else:
#             _LOGGER.error("No strømpriser flow found in the fetched data.")
#             return

#         # Merge the new strømpriser flow into the existing flows
#         updated_flows = [
#             flow if flow.get('label') != 'Strømpriser' else strømpriser_flow
#             for flow in existing_flows
#         ]

#         # Append the strømpriser flow if it's not already in the list
#         if not any(flow.get('label') == 'Strømpriser' for flow in updated_flows):
#             updated_flows.append(strømpriser_flow)

#         # Write the merged flows back to the original flows.json file
#         async with aiofiles.open(strømpriser_file_url, 'w', encoding='utf-8') as file:
#             await file.write(json.dumps(updated_flows, indent=4))
#             await file.flush()  # Ensure all data is written to disk
#             _LOGGER.info(f"Merged strømpriser flow successfully into {strømpriser_file_url}.")
#             _LOGGER.debug(f"Final updated flows content: {json.dumps(updated_flows, indent=4)}")

#         log_file_size(strømpriser_file_url, "After writing")

#         # Remove the temporary file after merging
#         os.remove(temp_file_url)

#     except Exception as e:
#         _LOGGER.error(f"Error merging strømpriser flow: {str(e)}")