import os
import subprocess
import requests
import datetime
import argparse
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")


def get_git_diff(max_chars=12000):
    result = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True)
    diff = result.stdout

    if len(diff) > max_chars:
        print(f"⚠️  Diff is too large ({len(diff)} chars). Truncating to {max_chars} chars.")
        diff = diff[:max_chars]

    return diff



def create_branch():
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"UT-gen-{timestamp}"
    subprocess.run(["git", "checkout", "-b", branch_name])
    return branch_name


def commit_and_push(branch_name):
    subprocess.run(["git", "add", "tests/"])
    subprocess.run(["git", "commit", "-m", "Add LLM-generated unit tests"])
    subprocess.run(["git", "push", "-u", "origin", branch_name])


def get_pr_title_desc(diff):
    prompt = f"Generate a PR title and description based on this git diff:\n\n{diff}"
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",  # or other supported model
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=payload)

    # Print full response for debugging
    print("🔍 Groq API raw response:")
    print(response.text)

    # Raise error if the request failed
    if response.status_code != 200:
        raise Exception(f"Groq API error: {response.status_code} - {response.text}")

    data = response.json()

    if "choices" not in data:
        raise Exception(f"Unexpected response format from Groq: {data}")

    content = data["choices"][0]["message"]["content"]

    lines = content.strip().split("\n", 1)
    title = lines[0].strip()
    body = lines[1].strip() if len(lines) > 1 else "Auto-generated PR"
    return title, body



def create_pull_request(branch_name, title, body):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "title": title,
        "body": body,
        "head": branch_name,
        "base": "main"
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print(f"PR created successfully: {response.json()['html_url']}")
    else:
        print(f"Failed to create PR: {response.status_code}\n{response.text}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--generate-pr', action='store_true', help='Generate and raise a PR based on git diff')
    args = parser.parse_args()

    if args.generate_pr:
        diff = get_git_diff()
        branch = create_branch()
        commit_and_push(branch)
        title, body = get_pr_title_desc(diff)
        create_pull_request(branch, title, body)
    else:
        print("Run with --generate-pr to execute PR workflow")


if __name__ == "__main__":
    main()
