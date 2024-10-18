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
  - Installation:
    - Debian and Debian-Based Distros (like Ubuntu):
      - Using apt
      ```bash
      sudo apt install python3-requests
      ```
      - Using pip
      ```bash
      pip3 install requests
      ```

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

This script interacts with the Salsa GitLab API to retrieve information about Debian-packaged INDI drivers. It fetches the package names, their Debian version from changelog files, and the corresponding Git commit hash. The script allows for asynchronous requests using `aiohttp` to improve performance, and it provides an option to skip certain packages or directories by specifying an ignore file.

#### Table of Contents

- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [Functions](#functions)
- [Environment Variables](#environment-variables)
- [Error Handling](#error-handling)

#### Prerequisites

Make sure you have the following installed:

- Python 3.6+
- `aiohttp` library
  - Installation:
    - Debian and Debian-Based Distros (like Ubuntu):
      - Using apt
      ```bash
      sudo apt install python3-aiohttp
      ```
      - Using pip
      ```bash
      pip3 install aiohttp
      ```

#### Usage

1. Set up the Salsa GitLab API token by configuring it in the script or passing it via environment variables.
   ```bash
   export GITLAB_TOKEN='your_personal_access_token'  # Salsa access token
   ```
2. Run the script:
   - **Note**: The `[IGNORE DIRS FILE]` is optional. It contains the directories you want to skip during the fetch process. If not provided, the script defaults to fetch all.

   ```bash
   python task_2.py [IGNORE DIRS FILE]
   ```
   or
   ```bash
   ./task_2.py [IGNORE DIRS FILE]
   ```

   - **Example:**
   ```bash
   python task_2.py ignore_dirs.txt
   
   OR
   
   ./task_2.py ignore_dirs.txt
   ```
   where `ignore_dirs.txt` is a file containing all the directories you'd like the program to ignore.

This will fetch the Debian-packaged INDI drivers' names, versions from changelogs, and their Git commit hashes, printing them to the console.

#### Functions

### `main()`
The entry point of the script, responsible for orchestrating the fetch process and outputting driver information.

### `fetch_project_list()`
Fetches a list of projects from the Salsa GitLab API under the Debian Astro team, specifically targeting INDI-related packages.

- **Returns**: A list of project names available in the Debian Astro team repository.

### `fetch_package_info(project_name)`
Retrieves the Debian version of the package and the corresponding Git hash by parsing the changelog file of the provided project.

- **Arguments**:
  - `project_name`: The name of the project whose changelog and version are being fetched.
  
- **Returns**: A dictionary containing the project name, version, and Git commit hash.

### `extract_version(changelog_content)`
Extracts the version number from the changelog content.

- **Arguments**:
  - `changelog_content`: The content of the changelog file.
  
- **Returns**: The extracted version or "Unknown" if not found.

### `try_get_changelog(project_name, branch)`
Attempts to retrieve the changelog file from different branches of the project's repository.

- **Arguments**:
  - `project_name`: The name of the project whose changelog is being retrieved.
  - `branch`: The branch to look for the changelog file in.
  
- **Returns**: The content of the changelog file or `None` if not found.

### `get_default_branch(project_name)`
Retrieves the default branch of the project.

- **Arguments**:
  - `project_name`: The name of the project.
  
- **Returns**: The name of the default branch, typically "master" or "main".

### `parse_ignore_file(ignore_file_path)`
Parses the ignore file to get a list of directories or projects to skip during the fetch process.

- **Arguments**:
  - `ignore_file_path`: Path to the file that contains directories or project names to be ignored.
  
- **Returns**: A list of directories or projects to ignore.

## Environment Variables

You must configure a GitLab API token for accessing private repositories or avoiding API rate limits. The token can be set as an environment variable named `GITLAB_TOKEN`.

## Error Handling

The script handles various potential errors, including:

- Network errors (e.g., connection timeouts)
- Handling unavailable changelog files
- Handling non-existent or empty branches

In case of an error, the script logs the message and skips the problematic project or directory, continuing the fetch process for others.

