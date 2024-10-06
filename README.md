# INDI Driver Fetcher

This repository contains Python scripts to:

1. Fetch a list of INDI 3rd-party drivers and extract their version and latest Git commit hash.
2. Retrieve a list of Debian-packaged INDI drivers, extracting their Debian version and corresponding Git hash.

## Detailed Description of Scripts

### Script 1 - `task_1.py`

This script interacts with the GitHub API to retrieve information about drivers from the **`indi-3rdparty`** repository. It fetches driver names, their versions from changelog files, and the latest commit hashes along with the associated commit dates. The script efficiently handles GitHub rate limits and utilizes basic authentication with a GitHub Personal Access Token.

#### Table of Contents

- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [Functions](#functions)
- [Environment Variables](#environment-variables)
- [Error Handling](#error-handling)

#### Prerequisites

Make sure you have the following installed:

- Python 3.x
- `requests` library


#### Usage

1. Set your GitHub Personal Access Token as an environment variable:

   ```bash
   export GITHUB_TOKEN='your_personal_access_token'
   ```

2. Run the script:

   ```bash
   python task_1.py
   ```
   or
      ```bash
   ./task_1.py
   ```

This will initiate the process of fetching driver information and display it in the console.

#### Functions

### `main()`
The main entry point of the script that initiates the fetching process of driver information.

### `rate_limited_get(url, headers=None)`
A wrapper function to perform GET requests that respect GitHub's rate limits. It retries requests if the rate limit is exceeded.

- **Arguments**:
  - `url`: The URL to send the GET request to.
  - `headers`: Optional headers for the GET request.
  
- **Returns**: The response from the GET request.

### `get_drivers()`
Fetches a list of drivers from the GitHub repository, extracting information such as driver name, version, and the latest commit hash.

- **Returns**: A list of dictionaries containing driver information.

### `get_changelog(driver_name)`
Fetches the changelog file for a specific driver.

- **Arguments**:
  - `driver_name`: The name of the driver whose changelog is being fetched.
  
- **Returns**: The content of the changelog file if found, otherwise `None`.

### `extract_version(file_content)`
Extracts the version number from the changelog content.

- **Arguments**:
  - `file_content`: The content of the changelog file.
  
- **Returns**: The extracted version, or "Unknown" if not found.

## Environment Variables

The script uses a GitHub Personal Access Token for authentication. You must set this token as an environment variable named `GITHUB_TOKEN` before running the script.

## Error Handling

The script handles various exceptions, including:

- Rate limit errors (HTTP status 403)
- Timeout errors
- General request exceptions

In case of an error, a message will be printed to standard error, and the script will attempt to retry if applicable.


### Script 2 - `task_2.py`

 TODO: *(Add detailed description here once the script is completed)*