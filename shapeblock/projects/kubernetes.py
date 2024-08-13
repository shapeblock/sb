import logging
import yaml
from kubernetes import client, config

from django.template.loader import render_to_string
from django.conf import settings
from .models import Project

logger = logging.getLogger("django")


def run_setup_project(project: Project):
    logger.info("Setting up project.")
    if settings.TEST_RUN:
        logger.debug("--- TEST RUN ---")
        return
    try:
        config.load_incluster_config()
    # TODO: show we throw the exception instead of handling it
    except Exception as error:
        logger.error(error)
        logger.error(f"Unable to get cluster config for {project.name}.")
        return
    api = client.CustomObjectsApi()
    data = {
        "project_uuid": project.uuid,
        "project_name": project.name,
        "project_description": project.description,
    }
    create_project = render_to_string("project.yaml", data)
    payload = yaml.load(create_project, Loader=yaml.FullLoader)
    response = api.create_cluster_custom_object(
        group="dev.shapeblock.com",
        version="v1alpha1",
        plural="projects",
        body=payload,
    )
    return response


def run_delete_project(project: Project):
    logger.info("Deleting project.")
    if settings.TEST_RUN:
        logger.debug("--- TEST RUN ---")
        return
    config.load_incluster_config()
    api = client.CustomObjectsApi()
    try:
        response = api.delete_cluster_custom_object(
            group="dev.shapeblock.com",
            version="v1alpha1",
            plural="projects",
            name=project.name,
        )
    except Exception as e:
        logger.error(e)
        return
    return response
