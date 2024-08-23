import re

from . import github, gitlab
from . import GIT_REGEX


def get_commit_sha(git_url, branch, author, service):
    # TODO: this could be repo full name instead of git_url
    match = re.match(GIT_REGEX, git_url).groupdict()
    full_name = f"{match['org']}/{match['repo']}"
    token = author.github_token
    if service == "github":
        return github.get_head_commit(token, full_name, branch)
    if service == "gitlab":
        return gitlab.get_head_commit(token, full_name, branch)
