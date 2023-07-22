
from urllib.parse import urlparse, unquote
from github import Github
import base64

path = urlparse('https://github.com/elunez/eladmin/blob/61c71313436482eda6b365ed124bf90e962a3a90/sql/eladmin.sql').path
path_parts = path.split('/')
repo_name = path_parts[1] + '/' + path_parts[2]
file_path = '/'.join(path_parts[3:])

print(path)
print(path_parts)
print(repo_name)
print(file_path)

# Use the Github API to get the file contents
g = Github('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')
repo = g.get_repo(repo_name)

file_content = repo.get_contents(file_path)

# Decode the base64 encoded content
file_data = base64.b64decode(file_content.content)

print(file_data)