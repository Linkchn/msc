import os


token = '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'

os.makedirs("public_repo", exist_ok=True)

def search_github(query, token):
    url = "https://api.github.com/search/code"
    headers = {'Authorization': 'token ' + token}
    params = {'q': query}
    response = requests.get(url, headers=headers, params=params)
    return response.json()


import requests

def download_file(url, local_filename):
    response = requests.get(url, stream=True)

    with open(f'public_repo/sql_{local_filename}.sql', 'w') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(str(chunk))
    return local_filename


from urllib.parse import urlparse, unquote
from github import Github
import base64


def download_github_file_from_url(token, item, local_filename):
    # Parse the URL to get the path, and split the path to get the repo name and file path
    file_url = item['html_url']
    path = urlparse(file_url).path
    path_parts = path.split('/')
    repo_name = path_parts[1] + '/' + path_parts[2]
    file_path = item['path']

    # Use the Github API to get the file contents
    g = Github(token)
    repo = g.get_repo(repo_name)

    file_content = repo.get_contents(file_path)

    # Decode the base64 encoded content
    file_data = base64.b64decode(file_content.content)

    # Write the content to a local file
    with open(local_filename, 'wb') as f:
        f.write(file_data)

results = search_github('extension:sql', token)
items = results['items']

num = 1
for item in results['items']:

    # download_file(item['html_url'], str(num))
    print(item['html_url'])
    download_github_file_from_url(token, item, 'public_repo/sql_'+ str(num) + '.sql')
    num+=1