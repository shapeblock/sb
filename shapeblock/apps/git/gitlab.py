import logging
import datetime
from requests_oauthlib import OAuth2Session

import gitlab as gitlab_module
from django.utils import timezone

from shapeblock.utils.users import get_user_connected_accounts

logger = logging.getLogger("django")


def gitlab_handle(token):
    if token:
        return gitlab_module.Gitlab("https://gitlab.com", oauth_token=token)
    else:
        return gitlab_module.Gitlab("https://gitlab.com")


def get_repo(token: str, repo_fullname: str):
    gl = gitlab_handle(token)
    gl.auth()
    return gl.projects.get(repo_fullname)


def get_head_commit(token, full_name, branch):
    gl = gitlab_handle(token)
    gl.auth()
    branch = gl.projects.get(full_name).branches.get(branch)
    return branch.commit["id"]


def get_default_branch(token, repo_id):
    gl = gitlab_handle(token)
    gl.auth()
    project = gl.projects.get(repo_id)
    return project.default_branch


# TODO: sort by time
def get_branches(token, repo_id):
    gl = gitlab_handle(token)
    gl.auth()
    project = gl.projects.get(repo_id, lazy=True)
    return [branch.name for branch in project.branches.list(all=True)]


def add_public_key(token, name, public_key):
    gl = gitlab_handle(token)
    gl.auth()
    gl.user.keys.create({"title": name, "key": public_key})


def add_deploy_key(project, name, public_key):
    key = project.keys.create({"title": name, "key": public_key})
    return key.id


def get_user_repos(token, query):
    gl = gitlab_handle(token)
    gl.auth()
    return [
        {
            "id": project.id,
            "url": project.ssh_url_to_repo,
            "full_name": project.path_with_namespace,
        }
        for project in gl.projects.list(membership=True, all=True, search=query)
    ]


# TODO: delete gitlab key

# TODO: add gitlab webhook


def get_git_refs(user, git_path):
    owner, name = git_path.split("/")
    connected_accounts = get_user_connected_accounts(user)
    # TODO: Handle demo repos for un-connected accounts

    account = [ac for ac in connected_accounts if ac["name"].startswith("gitlab")]
    token = account[0]["id"]
    repo = [r for r in get_user_repos(token, name) if r["full_name"] == git_path]
    if not repo:
        return ["master"], "master"
    repo_id = repo[0]["id"]
    return (
        get_branches(token, repo_id),
        get_default_branch(token, repo_id),
    )


def get_app_config(repo, ref):
    pf_app = repo.files.raw(file_path=".platform.app.yaml", ref=ref)
    return pf_app.decode("utf-8")


def get_services_config(repo, ref):
    services = repo.files.raw(file_path=".platform/services.yaml", ref=ref)
    return services.decode("utf-8")


def get_services_config(repo, ref):
    routes = repo.files.raw(file_path=".platform/routes.yaml", ref=ref)
    return routes.decode("utf-8")


def ensure_valid_token(token):
    logger.debug("checking if token is valid")
    logger.debug(token.expires_at)
    logger.debug(token.token)
    if token.expires_at > timezone.now():
        return token  # Already valid, no need to do anything.

    # Otherwise, we need to refresh
    session = get_oauth2_session(token)
    data = session.refresh_token("https://gitlab.com/oauth/token")
    token.token = data["access_token"]
    token.token_secret = data["refresh_token"]
    token.expires_at = timezone.now() + datetime.timedelta(seconds=data["expires_in"])
    token.save()
    return token


def get_oauth2_session(social_application_token):
    extra = {
        "client_id": social_application_token.app.client_id,
        "client_secret": social_application_token.app.secret,
    }
    return OAuth2Session(
        social_application_token.app.client_id,
        token={
            "access_token": social_application_token.token,
            "token_type": "Bearer",
            "refresh_token": social_application_token.token_secret,
        },
        auto_refresh_kwargs=extra,
        auto_refresh_url="https://gitlab.com/oauth/token",
        scope=["api"],
    )


# session = get_oauth2_session(social_application_token)
# session.refresh_token('https://gitlab.com/oauth/token')
