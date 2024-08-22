import logging

from github import Github
from shapeblock.utils.users import get_user_connected_accounts

logger = logging.getLogger("django")


def get_default_branch(token, repo_id):
    gh = Github(token) if token else Github()
    repo = gh.get_repo(repo_id)
    return repo.default_branch


def get_head_commit(token, full_name, branch):
    gh = Github(token) if token else Github()
    branch = gh.get_repo(full_name).get_branch(branch)
    return branch.commit.sha


# TODO: sort by time
def get_branches(token, repo_id):
    gh = Github(token) if token else Github()
    repo = gh.get_repo(repo_id)
    return [branch.name for branch in repo.get_branches()]


def get_repo(token, full_name):
    gh = Github(token) if token else Github()
    return gh.get_repo(full_name)


def add_deploy_key(repo, name, public_key):
    key = repo.create_key(title=name, key=public_key)
    return key.id


def get_user_repos(token, query, owner=None):
    gh = Github(token)
    # Github search is little weird. It does not search across orgs.
    # We create a list of orgs, seach in each org and append it to search results.
    user = gh.get_user()
    login = user.login
    if owner:
        login = owner
    orgs = user.get_orgs()
    user_search_results = gh.search_repositories(
        query=f"{query} user:{login} fork:true"
    )
    org_search_results = [
        gh.search_repositories(query=f"{query} user:{login} org:{org.login} fork:true")
        for org in orgs
    ]
    search_results = [user_search_results] + org_search_results
    results = []
    [
        results.extend(
            [
                {"id": repo.id, "url": repo.ssh_url, "full_name": repo.full_name}
                for repo in search_result
            ]
        )
        for search_result in search_results
    ]
    # make results unique
    unique_ids = []
    new_results = []
    for result in results:
        id = result["id"]
        if id not in unique_ids:
            new_results.append(result)
            unique_ids.append(id)
    return new_results


# TODO: delete github key


# TODO: add github webhook


def get_git_refs(user, git_path):
    owner, name = git_path.split("/")
    connected_accounts = get_user_connected_accounts(user)
    # Handle demo repos for un-connected accounts
    if not connected_accounts:
        repo = get_repo(None, git_path)
        return (
            get_branches(None, repo.id),
            get_default_branch(None, repo.id),
        )

    account = [ac for ac in connected_accounts if ac["name"].startswith("github")]
    token = account[0]["id"]
    repo = [r for r in get_user_repos(token, name, owner) if r["full_name"] == git_path]
    if not repo:
        return ["master"], "master"
    repo_id = repo[0]["id"]
    return (
        get_branches(token, repo_id),
        get_default_branch(token, repo_id),
    )


def get_app_config(repo, ref):
    pf_app = repo.get_contents(".platform.app.yaml", ref=ref)
    return pf_app.decoded_content.decode("utf-8")


def get_services_config(repo, ref):
    services = repo.get_contents(".platform/services.yaml", ref=ref)
    return services.decoded_content.decode("utf-8")


def get_services_config(repo, ref):
    routes = repo.get_contents(".platform/routes.yaml", ref=ref)
    return routes.decoded_content.decode("utf-8")
