import re

from allauth.socialaccount.models import SocialToken
from . import github, gitlab
from . import GIT_REGEX


def get_commit_sha(git_url, branch, author, service):
    # TODO: this could be repo full name instead of git_url
    match = re.match(GIT_REGEX, git_url).groupdict()
    full_name = f"{match['org']}/{match['repo']}"
    try:
        token_object = SocialToken.objects.get(account__user=author, account__provider=service)
        if service == "gitlab":
            token_object = gitlab.ensure_valid_token(token_object)
        token = token_object.token
    except SocialToken.DoesNotExist:
        token = None
    if service == "github":
        return github.get_head_commit(token, full_name, branch)
    if service == "gitlab":
        return gitlab.get_head_commit(token, full_name, branch)
