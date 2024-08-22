from typing import List
import requests
import json
import logging

from requests.auth import HTTPBasicAuth

logger = logging.getLogger("django")


def get_bitbucket_token(client_id: str, secret: str, refresh_token: str) -> str:
    refresh_token_url = "https://bitbucket.org/site/oauth2/access_token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = requests.post(
        refresh_token_url, auth=HTTPBasicAuth(client_id, secret), data=data
    )
    if response.status_code != 200:
        logger.error(
            f"Unable to get access token, got status code: {response.status_code}"
        )
        return response.status_code
    response_data = response.json()
    return response_data["access_token"]


def get_workspaces(slug: str, token: str) -> tuple[int, List]:
    url = "https://api.bitbucket.org/2.0/workspaces"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    params = {"q": f'slug ~ "{slug}"'}
    response = requests.get(
        url,
        headers=headers,
        params=params,
    )
    ret = []
    if response.status_code != 200:
        logger.error(
            f"Unable to get workspaces, got status code: {response.status_code}"
        )
        return response.status_code, ret
    response_data = response.json()
    for value in response_data["values"]:
        ret.append(value["slug"])
    return response.status_code, ret


def get_repo(workspace: str, repo_slug: str, token: str) -> tuple[int, List]:
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}"
    params = {"q": f'name ~ "{repo_slug}"'}
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    response = requests.get(
        url,
        headers=headers,
        params=params,
    )
    ret = []
    if response.status_code != 200:
        logger.error(f"Unable to get repo, got status code: {response.status_code}")
        return response.status_code, ret
    response_data = response.json()
    for value in response_data["values"]:
        # TODO: add name and default branch(mainbranch.name)
        ret.append(value["full_name"])
    return response.status_code, ret


def get_refs(workspace: str, repo_slug: str, token: str) -> tuple[int, List]:
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/refs"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    response = requests.get(
        url,
        headers=headers,
    )
    ret = []
    if response.status_code != 200:
        logger.error(
            f"Unable to get repo refs, got status code: {response.status_code}"
        )
        return response.status_code, ret
    response_data = response.json()
    for value in response_data["values"]:
        ret.append(value["name"])
    return response.status_code, ret


def add_key(
    selected_user_uuid: str, ssh_public_key: str, token: str
) -> tuple[int, str]:
    """
    Calling this results in the following error as of 3rd Jan 2022.

    '{"type": "error", "error": {"message": "This API is only accessible with the following authentication types: session, password, apppassword"}}'

    """
    key_url = f"https://api.bitbucket.org/2.0/users/{selected_user_uuid}/ssh-keys"
    data = {"key": ssh_public_key}
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    response = requests.post(key_url, headers=headers, json=data)
    if response.status_code != 201:
        logger.error(f"Unable to create key, got status code: {response.status_code}")
        return response.status_code, response.text
    response_data = response.json()
    return response.status_code, response_data["uuid"]


def add_deploy_key(
    workspace: str, repo_slug: str, ssh_public_key: str, token: str
) -> tuple[int, int]:
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/deploy-keys"
    print(url)
    data = {"key": ssh_public_key, "label": "e2e"}
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        logger.error(
            f"Unable to create deploy key, got status code: {response.status_code}"
        )
        return response.status_code, response.text
    response_data = response.json()
    return response.status_code, response_data["id"]


def add_webhook(
    workspace: str, repo_slug: str, description: str, token: str
) -> tuple[int, str]:
    pass
