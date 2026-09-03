import requests
import time
import csv
import re

GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
OWNER = "your-username"
REPO = "your-repo"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

# fallback domain patterns, only used for links not already categorized
# by GitHub's own provider label (e.g. things pasted into 'blog')
SOCIAL_PATTERNS = {
    "twitter": r"twitter\.com|x\.com",
    "linkedin": r"linkedin\.com",
    "youtube": r"youtube\.com|youtu\.be",
    "mastodon": r"mastodon\.[a-z]+|@.+@.+\.[a-z]+",
    "instagram": r"instagram\.com",
    "facebook": r"facebook\.com",
    "twitch": r"twitch\.tv",
    "bluesky": r"bsky\.app",
}

# GitHub's social_accounts 'provider' values -> our column names
PROVIDER_MAP = {
    "twitter": "twitter",
    "linkedin": "linkedin",
    "youtube": "youtube",
    "mastodon": "mastodon",
    "instagram": "instagram",
    "facebook": "facebook",
    "twitch": "twitch",
    "bluesky": "bluesky",
    "generic": "other",
}

def get_stargazers(owner, repo):
    users = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/stargazers"
        resp = requests.get(url, headers=HEADERS, params={"per_page": 100, "page": page})
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        users.extend(u["login"] for u in batch)
        page += 1
        remaining = int(resp.headers.get("X-RateLimit-Remaining", 1))
        if remaining < 5:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            time.sleep(max(reset - time.time(), 1))
    return users

def categorize_link(url, row):
    """Fallback regex categorization for links not from social_accounts (e.g. 'blog' field)."""
    for name, pattern in SOCIAL_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            if not row.get(name):
                row[name] = url
            return
    if not row.get("blog"):
        row["blog"] = url
    else:
        row["other"] = url

def get_social_accounts(username):
    """Hits the dedicated social_accounts endpoint GitHub uses for profile 'social links'."""
    url = f"https://api.github.com/users/{username}/social_accounts"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        return []
    return resp.json()  # list of {"provider": "...", "url": "..."}

def get_profile_fields(username):
    row = {
        "username": username, "email": "", "twitter": "", "blog": "",
        "linkedin": "", "youtube": "", "mastodon": "", "instagram": "",
        "facebook": "", "twitch": "", "bluesky": "", "other": "", "bio": "",
    }
    url = f"https://api.github.com/users/{username}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        data = resp.json()
        row["email"] = data.get("email") or ""
        row["bio"] = (data.get("bio") or "").replace("\n", " ").strip()
        if data.get("twitter_username"):
            row["twitter"] = f"https://x.com/{data['twitter_username']}"

    # primary source: dedicated social accounts feature (catches LinkedIn etc.)
    for acct in get_social_accounts(username):
        provider = (acct.get("provider") or "generic").lower()
        link = acct.get("url") or ""
        column = PROVIDER_MAP.get(provider, "other")
        if not row.get(column):
            row[column] = link

    # secondary source: free-text 'blog' field, regex-matched as fallback
    url = f"https://api.github.com/users/{username}"
    resp2 = requests.get(url, headers=HEADERS)
    if resp2.status_code == 200:
        blog = (resp2.json().get("blog") or "").strip()
        if blog:
            if not blog.startswith("http"):
                blog = "https://" + blog
            categorize_link(blog, row)

    return row

def main():
    stargazers = get_stargazers(OWNER, REPO)
    print(f"Found {len(stargazers)} stargazers")

    rows = []
    for i, username in enumerate(stargazers, 1):
        fields = get_profile_fields(username)
        contact_keys = [k for k in fields if k not in ("username", "bio")]
        has_contact = any(fields[k] for k in contact_keys)
        has_bio = bool(fields["bio"])
        if has_contact or has_bio:
            rows.append(fields)
        if i % 20 == 0:
            print(f"Checked {i}/{len(stargazers)}")
        time.sleep(0.2)

    fieldnames = ["username", "email", "twitter", "linkedin", "blog", "youtube",
                  "mastodon", "instagram", "facebook", "twitch", "bluesky", "other", "bio"]
    with open("starsight.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} users with public info to starsight.csv")

if __name__ == "__main__":
    main()
