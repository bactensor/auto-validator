import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        payload = json.loads(request.body)
        if payload.get('action') == 'opened' and 'pull_request' in payload:
            pr = payload['pull_request']
            if 'submodule' in pr['title'].lower():
                approve_pr(pr['number'], payload['repository']['full_name'])
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid request'}, status=400)

def approve_pr(pr_number, repo_full_name):
    url = f'https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/reviews'
    headers = {
        'Authorization': f'token {settings.GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    payload = {
        'event': 'APPROVE'
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f'Approved PR #{pr_number}')
    else:
        print(f'Failed to approve PR #{pr_number}: {response.content}')