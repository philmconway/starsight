# starsight

A simple script for pulling public email addresses and social media handles from stars associated with a repo

This script only pulls publicly listed info - users with no email address or social media handles are omitted from the results. It does not scrape user commits for email addresses or attempt to gain indirect contact information for a user.

# Usage

Grab a copy of the script, and populate the following values:

GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"  

OWNER = "your-username"

REPO = "your-repo"

# Output

Results are saved in starsight.csv in the same folder as the script.
