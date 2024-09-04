import hashlib
import hmac
import os

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

GITHUB_SECRET = os.getenv("GITHUB_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")


def verify_signature(payload, signature):
    mac = hmac.new(GITHUB_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest("sha256=" + mac.hexdigest(), signature)


@csrf_exempt
def webhook(request):
    payload = request.body
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(payload, signature):
        return JsonResponse({"message": "Invalid signature"}, status=400)
    event = request.headers.get("X-GitHub-Event")
    if event == "pull_request":
        pr_data = request.json()
        action = pr_data.get("action")
        if action == "opened" or action == "synchronize":
            pr_number = pr_data["pull_request"]["number"]
            files_url = pr_data["pull_request"]["url"] + "/files"
            files_response = requests.get(files_url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=10)
            files = files_response.json()
            for file in files:
                if file["filename"].endswith(".gitmodules"):
                    approve_pr(pr_number)
                    break
    return JsonResponse({"message": "Success"}, status=200)


def approve_pr(pr_number):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/reviews"
    data = {"event": "APPROVE"}
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.post(url, json=data, headers=headers, timeout=10)
    if response.status_code == 200:
        print(f"Approved PR #{pr_number}")
    else:
        print(f"Failed to approve PR #{pr_number}: {response.content}")
