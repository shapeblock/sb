import logging
import yaml

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from django.template.loader import render_to_string
from django.conf import settings

from .models import App, EnvVar, Secret, Volume, BuildVar, InitProcess, WorkerProcess, CustomDomain
from shapeblock.deployments.models import Deployment
from .mapper.validator import version_enum

logger = logging.getLogger("django")

def get_app_pod(app: App):
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    namespace = app.project.name
    label_selector = f"appUuid={str(app.uuid)}"
    pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)
    if pods.items:
        return pods.items[0].metadata.name
    else:
        return None


def create_app_secret(app: App):
    logger.info("Creating app secret.")
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    namespace = app.project.name
    if not app.key_config:
        return
    annotation = app.key_config.get("annotation")
    metadata = {"name": f"{app.name}-ssh", "namespace": namespace, "annotations": {"kpack.io/git": annotation}}
    private_key = app.key_config["private_key"]
    string_data = {"ssh-privatekey": private_key}
    body = client.V1Secret(
        api_version="v1", string_data=string_data, kind="Secret", metadata=metadata, type="kubernetes.io/ssh-auth"
    )
    try:
        logger.debug(body)
        api_response = v1.create_namespaced_secret(namespace, body)
    except ApiException as error:
        logger.error(error)
        logger.error(f"Unable to create secret for app {app.name} in project {app.project.name}.")
        return


def run_deploy_pipeline(deployment: Deployment):
    logger.info("Creating deployment.")
    config.load_incluster_config()
    app = deployment.app
    config.load_incluster_config()
    # create secret if not already created
    api = client.CustomObjectsApi()
    sb_config = {
        "app_uuid": str(app.uuid),
        "deployment_uuid": str(deployment.uuid),
        "deployment_type": deployment.type,
        "name": app.name,
        "cluster_domain": settings.CLUSTER_DOMAIN,
        "namespace": app.project.name,
        "git": {
            "url": app.repo,
            "revision": deployment.ref,
            "sub_path": app.sub_path,
        },
        # TODO: should this change on a per deployment basis?
        "chart_version": settings.CHART_VERSION,
        # TODO: don't hard code it
        "replicas": 1,
        "type": app.stack,
        "env_vars": EnvVar.objects.filter(app=app),
        "secrets": Secret.objects.filter(app=app),
        "volumes": Volume.objects.filter(app=app),
        "build_vars": BuildVar.objects.filter(app=app),
        "init_processes": InitProcess.objects.filter(app=app),
        "custom_domains": CustomDomain.objects.filter(app=app),
        "workers": WorkerProcess.objects.filter(app=app),
        "has_liveness_probe": app.has_liveness_probe,
    }
    # TODO: derive other parameters from deployment. envs, docroot,
    if not sb_config.get("version"):
        stack = sb_config["type"]
        if stack != "nginx":
            # get latest version if not already there
            sb_config["version"] = version_enum[stack][-1]
    deploy_app = render_to_string(f"app.yaml", sb_config)
    payload = yaml.load(deploy_app, Loader=yaml.FullLoader)
    logger.debug(payload)
    try:
        response = api.patch_namespaced_custom_object(
            group="dev.shapeblock.com",
            version="v1alpha1",
            namespace=app.project.name,
            plural="applications",
            name=app.name,
            body=payload,
        )
    except ApiException as e:
        # first deployment
        # TODO: handle exception, 401
        response = api.create_namespaced_custom_object(
            group="dev.shapeblock.com",
            version="v1alpha1",
            namespace=app.project.name,
            plural="applications",
            body=payload,
        )
    logger.debug(response)
    logger.info("Deployment created.")
    return response


def delete_app_task(app: App):
    logger.info("Deleting app.")
    config.load_incluster_config()
    api = client.CustomObjectsApi()
    try:
        response = api.delete_namespaced_custom_object(
            group="dev.shapeblock.com",
            version="v1alpha1",
            name=app.name,
            namespace=app.project.name,
            plural="applications",
            body=client.V1DeleteOptions(),
        )
    except Exception as e:
        logger.error(e)
        logger.info("Unable to delete application.")
        return
    logger.info(response)
    logger.info("Application deleted.")
    return response
