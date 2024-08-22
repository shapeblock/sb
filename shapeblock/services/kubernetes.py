import logging
import yaml

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from django.template.loader import render_to_string

from .models import Service

logger = logging.getLogger("django")


def create_service(service: Service):
    logger.info(f"Creating service {service.name} of type {service.type}.")
    config.load_incluster_config()
    api = client.CustomObjectsApi()
    sb_config = {
        "service_uuid": str(service.uuid),
        "name": service.name,
        "namespace": service.project.name,
        # TODO: should this change on a per deployment basis?
        #'chart_version': settings.CHART_VERSION,
    }
    # TODO: derive other parameters from deployment. envs, docroot,
    deploy_app = render_to_string(f"services/{service.type}.yaml", sb_config)
    payload = yaml.load(deploy_app, Loader=yaml.FullLoader)
    logger.debug(payload)
    try:
        response = api.patch_namespaced_custom_object(
            group="helm.toolkit.fluxcd.io",
            version="v2beta2",
            namespace=service.project.name,
            plural="helmreleases",
            name=service.name,
            body=payload,
        )
    except ApiException as e:
        # first deployment
        # TODO: handle exception, 401
        response = api.create_namespaced_custom_object(
            group="helm.toolkit.fluxcd.io",
            version="v2beta2",
            namespace=service.project.name,
            plural="helmreleases",
            body=payload,
        )
    logger.debug(response)
    logger.info(f"Service {service} created.")
    return response


def delete_service(service: Service):
    logger.info(f"Deleting service {service.name} of type {service.type}.")
    config.load_incluster_config()
    api = client.CustomObjectsApi()
    try:
        response = api.delete_namespaced_custom_object(
            group="helm.toolkit.fluxcd.io",
            version="v2beta2",
            name=service.name,
            namespace=service.project.name,
            plural="helmreleases",
            body=client.V1DeleteOptions(),
        )
    except Exception as e:
        logger.error(e)
        logger.info(f"Unable to delete service {service}.")
        return
    logger.info(response)
    logger.info(f"Service {service} deleted.")
    return response


def is_statefulset_ready(service: Service):
    """
    Check if a StatefulSet in the given namespace is ready.
    :return: bool, True if the StatefulSet is ready, False otherwise
    """
    # Load the kube config
    config.load_incluster_config()
    namespace = service.project.name
    # Create an API instance
    api_instance = client.AppsV1Api()

    try:
        # Get the specified StatefulSet
        statefulset = api_instance.read_namespaced_stateful_set(
            service.service_statefulset, namespace
        )

        # Check if the number of ready replicas matches the desired count
        desired_replicas = statefulset.spec.replicas
        current_ready_replicas = statefulset.status.ready_replicas

        if desired_replicas is None or current_ready_replicas is None:
            return False

        return desired_replicas == current_ready_replicas

    except ApiException as e:
        print(f"An error occurred when accessing the StatefulSet: {e}")
        return False
