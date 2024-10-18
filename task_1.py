#!/usr/bin/env python3
"""
INDI 3rd-party Driver Info Fetcher Module

This script interacts with the GitHub API to retrieve information about drivers
from the "indi-3rdparty" repository. It fetches driver names, versions from
changelog files, and the latest commit hash with the associated commit date.

The script handles GitHub rate limits and uses basic authentication with a
GitHub Personal Access Token. Results are printed to standard output.

This script includes error handling for missing modules and provides
installation instructions.

Modules:
    - requests: To make HTTP requests to the GitHub API.
    - json: To parse and handle JSON data from API responses.
    - sys: To handle standard input/output and exit the program on errors.
    - time: To handle rate-limiting and timeout functionality.
    - os: To access environment variables (specifically the GitHub token).
    - re: To extract version numbers using regular expressions.
    - HTTPBasicAuth: To handle GitHub authentication.
    - datetime: To format and handle date information from GitHub commits.

Functions:
    - main: Main function to initiate the driver fetching process.
    - rate_limited_get: Wrapper function to perform rate-limited GET requests.
    - get_drivers: Fetches a list of drivers, versions, and latest commit hashes.
    - get_changelog: Fetches the changelog for a given driver from the repository.
    - extract_version: Extracts the version number from the changelog content.

Constants:
    - GITHUB_TOKEN: GitHub Personal Access Token for authentication.
    - RATE_LIMIT: Defines the number of requests allowed per minute.
    - RATE_LIMIT_RESET: Time to wait between requests in seconds.
    - TIMEOUT: The maximum time to wait for a response from GitHub API.
    - BASE_URL: Base URL of the GitHub repository "indi-3rdparty".
"""

import sys
import os


def check_modules():
    """
    Check for required modules and provide installation instructions if missing.
    This function run before driver checks start.

    Raises:
        SystemExit: If any required modules are missing, the function prints
                    installation instructions and exits with status code 1.
    """
    required_modules = {
        'requests': 'python3-requests',
        'json': 'built-in',
        'time': 'built-in',
        're': 'built-in',
        'datetime': 'built-in'
    }

    missing_modules = []

    for module, package in required_modules.items():
        try:
            __import__(module)
        except ImportError:
            missing_modules.append((module, package))

    if missing_modules:
        print("\nThe following required modules are missing:", file=sys.stderr)
        for module, package in missing_modules:
            if package == 'built-in':
                print(f"  - {module} (This is a built-in module and should be available)\n", file=sys.stderr)
            else:
                print(f"  - {module} (Install with: sudo apt install {package})\n", file=sys.stderr)
        sys.exit(1)


# Lets check for required modules before importing
check_modules()


import requests
import argparse
import json
import time
import re
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Line buffering for sys.stdout
sys.stdout.reconfigure(line_buffering=True)

# GitHub Personal Access Token for API authentication
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("Please set the GITHUB_TOKEN environment variable", file=sys.stderr)
    sys.exit(1)

# Basic authentication with GitHub token
auth = HTTPBasicAuth('', GITHUB_TOKEN)

# Rate limit parameters and base configurations
RATE_LIMIT = 30
RATE_LIMIT_RESET = 60 / RATE_LIMIT
TIMEOUT = 10
BASE_URL = "https://api.github.com/repos/indilib/indi-3rdparty"


def main(ignore_file=None):
    """
    Main function to fetch and display driver information.

    Args:
        ignore_file (str, optional): Path to a file containing directories to ignore.
    """
    default_ignore_dirs = ['.circleci', '.github', 'cmake_modules', 'debian', 'examples', 'scripts', 'spec', 'obsolete']

    if ignore_file and (ignore_dirs := parse_ignore_file(ignore_file)) is not None:
        print(f"Using custom dir. ignore list from {ignore_file}")
    else:
        ignore_dirs = default_ignore_dirs
        print("Using default ignore list")

    if ignore_dirs is None:
        ignore_dirs = default_ignore_dirs

    print(f"Directories being ignored: {ignore_dirs}\n")
    print("Starting to fetch drivers...")

    try:
        drivers = get_drivers(ignore_dirs)
        for driver in drivers:
            print(
                f"Driver: {driver['name']}, Version: {driver['version']}, Latest Git Hash: {driver['latest_git_hash']}"
            )
    except KeyboardInterrupt:
        print("\nProgram terminated. Thank you for using this program!")
        sys.exit(0)


def rate_limited_get(url, headers=None):
    """
    Perform a rate-limited GET request.

    If the rate limit is exceeded, the function waits until the reset time
    before retrying.

    Args:
        url (str): The URL to send the GET request to.
        headers (dict, optional): Optional headers for the GET request.

    Returns:
        Response: The response from the GET request.
    """
    while True:
        try:
            response = requests.get(
                url, auth=auth, headers=headers, timeout=TIMEOUT
            )
            if response.status_code != 403:
                return response
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0)) - int(time.time())
            if reset_time > 0:
                print(f"Rate limit exceeded. Waiting for {reset_time} seconds.", file=sys.stderr)
                time.sleep(reset_time)
            else:
                time.sleep(RATE_LIMIT_RESET)
        except requests.exceptions.Timeout:
            print(f"Request timed out for URL: {url}. Retrying...", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}. Retrying...", file=sys.stderr)
        time.sleep(1)


def get_drivers(ignore_dirs):
    """
    Fetch a list of drivers from the GitHub repository.

    Iterates over the repository contents, extracting driver information like version and
    latest git hash.

    Returns:
        list: A list of dictionaries containing driver information (name, version, latest git hash).
    """
    drivers = []
    url = f"{BASE_URL}/contents"

    try:
        print("Fetching repository contents...\n")
        response = rate_limited_get(url)
        response.raise_for_status()
        contents = json.loads(response.text)

        if not isinstance(contents, list):
            print("Received a non-list response:", contents, file=sys.stderr)
            return []

        for item in contents:
            if item['type'] == 'dir' and item['name'] not in ignore_dirs:
                driver_name = item['name']
                print(f"Processing driver: {driver_name}")

                try:
                    file_content = get_changelog(driver_name)
                    version = extract_version(file_content) if file_content else "Unknown"

                    commit_url = f"{BASE_URL}/commits?path={driver_name}&per_page=1"
                    commit_response = rate_limited_get(commit_url)
                    commit_response.raise_for_status()
                    commit_info = json.loads(commit_response.text)

                    if commit_info:
                        commit_date = datetime.strptime(commit_info[0]['commit']['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")
                        formatted_date = commit_date.strftime("%Y%m%d")
                        short_hash = commit_info[0]['sha'][:7]
                        git_info = f"git{formatted_date}.{short_hash}"
                    else:
                        git_info = "Unknown"

                    drivers.append({
                        'name': driver_name,
                        'version': version,
                        'latest_git_hash': git_info
                    })
                except requests.RequestException as e:
                    print(f"Error fetching data for driver {driver_name}: {e}", file=sys.stderr)

    except requests.RequestException as e:
        print(f"Error fetching repository contents: {e}", file=sys.stderr)
        return []

    return drivers


def get_changelog(driver_name):
    """
    Fetch the changelog file for a specific driver from the GitHub repository.

    Args:
        driver_name (str): The name of the driver whose changelog is being fetched.

    Returns:
        str or None: The content of the changelog file if found, otherwise None.
    """
    url = f"{BASE_URL}/contents/debian/{driver_name}/changelog"
    try:
        response = rate_limited_get(url)
        response_content = response.json()

        if isinstance(response_content, dict) and response_content.get("download_url"):
            download_url = response_content['download_url']
            changelog_response = rate_limited_get(download_url)
            return changelog_response.text
        else:
            print(f"Changelog file for {driver_name} not found or incorrect response format.", file=sys.stderr)
            return None
    except requests.RequestException as e:
        print(f"Error fetching changelog for {driver_name}: {e}", file=sys.stderr)
        return None


def extract_version(file_content):
    """
    Extract the driver version from the changelog content.

    Args:
        file_content (str): The content of the changelog file.

    Returns:
        str: The extracted version, or "Unknown" if not found.
    """
    if not file_content:
        return "Unknown"
    version_pattern = r"\((.*?)\)"
    lines = file_content.splitlines()

    if lines:
        first_line = lines[0].strip()
        version = re.search(version_pattern, first_line)
        if version:
            return version.group(1)
        else:
            print("No version found in changelog", file=sys.stderr)
    return "Unknown"


def parse_ignore_file(file_path):
    """
    Parse an ignore file and return a list of directories to be ignored.

    This function reads a specified file, processes each line to extract
    directories to ignore, and returns them as a list. Comments in the file,
    which are marked by the '#' character, are ignored. Lines can also contain
    multiple directories separated by commas or whitespace.
    
    Args:
        file_path (str): The path to the ignore file to be parsed
    
    Returns:
        list or None: A list of directories to ignore if the file was successfully
        parsed. Returns None if the file could not be found, cannot be read, or
        if an unexpected error occurs.
    """  
    ignore_list = []

    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.split('#', 1)[0].strip()
                if line:
                    dirs = re.split(r'[,\s]+', line)
                    ignore_list.extend(dirs)

        ignore_list = [directory for directory in ignore_list if directory]

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except IOError:
        print(f"Error: Could not read the file '{file_path}'.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

    return ignore_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch INDI 3rd-party driver information"
    )
    parser.add_argument(
        "ignore_file", nargs="?",
        help="Path to file containing directories to ignore"
    )
    args = parser.parse_args()

    main(args.ignore_file)