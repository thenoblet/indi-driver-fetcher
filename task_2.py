#!/usr/bin/env python3
"""
Module: INDI-Related Debian Astro Packages Fetcher

This script is designed to retrieve package information from the Debian Astro team's repository, 
specifically for INDI-related packages. It interfaces with the Salsa GitLab API to query repositories 
and extract version information from changelog files.

Main functionalities include:
1. Fetching a list of projects from the Debian Astro team on Salsa.
2. Searching for changelog files across branches and predefined paths to extract the version number.
3. Optionally, reading an ignore file to skip certain directories or projects.
4. Outputting package names, versions, and the branches from which the changelog was fetched.

### Key Features:
- **Asynchronous HTTP requests**: Uses `aiohttp` to perform API requests concurrently for better performance.
- **Version extraction**: Parses changelog files to extract the version number of each package.
- **Customizable ignore list**: Supports an external ignore file for skipping certain directories or projects.
- **Fallback to default branch**: When no specific branch is provided, it tries to retrieve information
    from the project's default branch (or "master" by default).
"""

import sys
import os


def check_modules():
    """
    Check for required modules and provide installation instructions if missing.
    This function runs before driver checks start.

    Raises:
        SystemExit: If any required modules are missing, the function prints
                    installation instructions and exits with status code 1.
    """
    required_modules = {
        'aiohttp': 'python3-aiohttp',
        'asyncio': 'built-in',
        'json': 'built-in',
        're': 'built-in',
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
                print(
                    f"  - {module} (This is a built-in module and should be available)\n", file=sys.stderr)
            else:
                print(
                    f"  - {module} (Install with: sudo apt install {package})\n", file=sys.stderr)
        sys.exit(1)


check_modules()


import argparse
import aiohttp
import asyncio
import re
from urllib.parse import quote_plus
from aiohttp.client_exceptions import ClientError


# GitLab API configuration
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
if not GITLAB_TOKEN:
    print("Please set the GITLAB_TOKEN environment variable", file=sys.stderr)
    print("Use: export GITLAB_TOKEN='<Your gitlab/salsa personal access token>'")
    sys.exit(1)

SALSA_API_URL = "https://salsa.debian.org/api/v4"
DEBIAN_ASTRO_TEAM = "debian-astro-team"


async def main(ignore_file=None):
    """
    Main function that orchestrates fetching Debian Astro Team packages.

    Args:
        ignore_file (str): Optional path to a file that contains directories to be ignored.
    """
    async with aiohttp.ClientSession() as session:
        default_ignore_dirs = ['indi-asu', 'indi-ahp-xc']

        if ignore_file and (ignore_dirs := parse_ignore_file(ignore_file)) is not None:
            print(f"Using custom dir. ignore list from {ignore_file}")
        else:
            ignore_dirs = default_ignore_dirs
            print("Using default package ignore list")

        if ignore_dirs is None:
            ignore_dirs = default_ignore_dirs

        print(f"Packages being ignored: {ignore_dirs}\n")
        print('Getting Debian Astro Team ID...')

        headers = {'PRIVATE-TOKEN': GITLAB_TOKEN}

        group_id = await get_astro_team_id(session, headers)
        if group_id is None:
            print(
                f"Failed to find the {DEBIAN_ASTRO_TEAM} group.", file=sys.stderr)
            sys.exit(1)

        print('Getting info about packages...\n')
        try:
            packages = await get_indi_packages(session, headers, group_id, ignore_dirs)
            if packages is None:
                print("Error fetching packages...", file=sys.stderr)
                sys.exit(1)

            packages.sort(key=lambda x: x['name'])
            
            for package in packages:
                print(f"Package: {package['name']}, Version: {package['debian_version']}")

        except KeyboardInterrupt:
            print("\nProgram terminated. Thank you for using this program!")
            sys.exit(0)
        except Exception as e:
            print(f"\nUnexpected error occurred: {e}", file=sys.stderr)
            sys.exit(1)


async def get_astro_team_id(session, headers, retries=5):
    """
    Get the GitLab group ID for the Debian Astro team.

    Args:
        session (aiohttp.ClientSession): An active HTTP session for making requests.
        headers (dict): HTTP headers including the authorization token.
        retries (int): The number of retry attempts in case of rate-limiting errors.

    Returns:
        int: The group ID of the Debian Astro team, or None if the request fails.
    """
    backoff_factor = 1  # Initial backoff time in seconds
    for attempt in range(retries):
        try:
            url = f"{SALSA_API_URL}/groups/{quote_plus(DEBIAN_ASTRO_TEAM)}"
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                group_info = await response.json()
                return group_info['id']
        except aiohttp.ClientResponseError as e:
            if e.status == 429:  # Too Many Requests
                wait_time = backoff_factor * \
                    (2 ** attempt)  # Exponential backoff
                print(
                    f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying...", file=sys.stderr)
                await asyncio.sleep(wait_time)
                continue
            print(
                f"Error fetching debian-astro-team info: {e}", file=sys.stderr)
            return None
        except ClientError as e:
            print(
                f"Error fetching debian-astro-team info: {e}", file=sys.stderr)
            return None
    print("Exceeded maximum retries. Could not fetch debian-astro-team info.", file=sys.stderr)
    return None


async def get_indi_packages(session, headers, group_id, ignore_dirs):
    """
    Fetch all INDI-related packages from the Debian Astro team.

    Args:
        session (aiohttp.ClientSession): An active HTTP session for making requests.
        headers (dict): HTTP headers including the authorization token.
        group_id (int): The group ID of the Debian Astro team.
        ignore_dirs (list): List of directories to ignore while fetching packages.

    Returns:
        list: A list of package details (name, version, git hash) or None in case of an error.
    """
    packages = []
    page = 1
    per_page = 100

    try:
        while True:
            url = f"{SALSA_API_URL}/groups/{group_id}/projects"
            params = {
                "page": page,
                "per_page": per_page,
                "order_by": "name",
                "sort": "asc"
            }

            async with session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                projects = await response.json()
                if not projects:
                    break

                tasks = [
                    get_package_info(session, headers, project)
                    for project in projects
                    if project['name'].startswith(('indi-', 'lib')) and not any(
                        ignored in project['name'] for ignored in ignore_dirs
                    )
                ]

                if tasks:
                    package_infos = await asyncio.gather(*tasks)
                    packages.extend([pkg for pkg in package_infos if pkg])

            page += 1

        return packages

    except ClientError as e:
        print(f"Error fetching projects: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return None


async def get_package_info(session, headers, project):
    """
    Get detailed information about a specific package.

    Args:
        session (aiohttp.ClientSession): An active HTTP session for making requests.
        headers (dict): HTTP headers including the authorization token.
        project (dict): A dictionary containing project details from GitLab.

    Returns:
        dict: A dictionary containing package information (name, version, git hash).
    """
    # print(f"Processing {project['name']}...")
    
    try:
        # First, lets get the default branch, yeah?
        default_branch = await get_default_branch(session, headers, project['id'])

        # Let's check these branches in priority order
        branches = ['debian/main', default_branch, 'master']

        latest_commit = None
        for branch in branches:
            commits_url = f"{SALSA_API_URL}/projects/{project['id']}/repository/commits"
            try:
                async with session.get(
                    commits_url, headers=headers, params={
                        "ref_name": branch, "per_page": 1}
                ) as response:
                    if response.status == 200:
                        commits = await response.json()
                        if commits:
                            latest_commit = commits[0]
                            break
            except ClientError:
                continue

        # Check multiple possible changelog locations
        changelog_paths = [
            'debian/changelog',
            'packaging/debian/changelog',
            'debian.upstream/changelog',
            'orig/debian/changelog'
        ]

        changelog, found_branch = await get_changelog(
            session, headers, project['id'], changelog_paths, branches
        )

        version = "Unknown"
        if changelog:
            version = extract_version(changelog)
        else:
            print(
                f"Warning: No changelog found for {project['name']}", file=sys.stderr)

        git_hash = "Unknown"
        if latest_commit:
            last_activity_date = project.get('last_activity_at', "Unknown")
            if last_activity_date != "Unknown":
                formatted_date = last_activity_date.split(
                    "T")[0].replace("-", "")
                git_hash = f"git{formatted_date}.{latest_commit['id'][:8]}"

        return {
            "name": project['name'],
            "debian_version": version,
            "git_hash": git_hash,
            "last_activity": project.get('last_activity_at', "Unknown"),
            "changelog_found": changelog is not None,
            "changelog_branch": found_branch if found_branch else "Not found"
        }

    except ClientError as e:
        print(
            f"Error fetching data for {project['name']}: {e}", file=sys.stderr)
        return create_error_package_info(project)
    except Exception as e:
        print(
            f"Error processing data for {project['name']}: {e}", file=sys.stderr)
        return None


def create_error_package_info(project):
    """Create a package info dictionary with error states."""
    return {
        "name": project['name'],
        "debian_version": "Unknown",
        "git_hash": "Unknown",
        "last_activity": project.get('last_activity_at', "Unknown"),
        "changelog_found": False,
        "changelog_branch": "Not found"
    }


async def get_changelog(session, headers, project_id, paths, branches):
    """
    Try to retrieve the changelog from different paths and branches.

    Args:
        session (aiohttp.ClientSession): An active HTTP session for making requests.
        headers (dict): HTTP headers including the authorization token.
        project_id (int): The project ID in GitLab.
        changelog_paths (list): A list of possible paths to the changelog.
        branches (list): A list of branches to check.

    Returns:
        tuple: A tuple containing the changelog content (or None) and the
        branch where it was found.
    """
    """Try multiple possible changelog paths in different branches."""
    for branch in branches:
        for path in paths:
            encoded_path = quote_plus(path)
            changelog_url = f"{SALSA_API_URL}/projects/{project_id}/repository/files/{encoded_path}/raw?ref={quote_plus(branch)}"
            try:
                async with session.get(changelog_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text(), branch
            except ClientError:
                continue
    return None, None


async def get_default_branch(session, headers, project_id):
    """
    Fetch the default branch of a given project.

    Args:
        session (aiohttp.ClientSession): An active HTTP session for making requests.
        headers (dict): HTTP headers including the authorization token.
        project_id (int): The ID of the project in GitLab.

    Returns:
        str: The default branch name, or "master" if it cannot be determined.
    """
    try:
        url = f"{SALSA_API_URL}/projects/{project_id}"
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                project_info = await response.json()
                return project_info.get('default_branch', 'master')
    except ClientError:
        pass
    return 'master'


def parse_ignore_file(file_path):
    """
    Parse the ignore file to extract directories that should be ignored.

    Args:
        ignore_file (str): Path to the ignore file.

    Returns:
        list: A list of directories to ignore, or None if the file cannot be read.
    """
    ignore_list = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.split('#', 1)[0].strip()  # Ignore comments
                if line:
                    # Split by commas or whitespace
                    dirs = re.split(r'[,\s]+', line)
                    ignore_list.extend(dirs)
    except Exception as e:
        print(f"Error reading ignore file: {e}", file=sys.stderr)
        sys.exit(1)
    return ignore_list


def extract_version(file_content):
    """
    Extract the package version from the changelog content.

    Args:
        changelog (str): The content of the changelog file.

    Returns:
        str: The extracted version number, or "Unknown" if extraction fails.
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
        print("No version found in changelog", file=sys.stderr)
    return "Unknown"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch Debian packages for the Astro team, with an option to ignore specified directories."
    )
    parser.add_argument(
        "ignore_file", nargs="?",
        help="Path to file containing directories to ignore"
    )

    args = parser.parse_args()

    asyncio.run(main(args.ignore_file))
