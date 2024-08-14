import logging
import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from shapeblock.apps.git import github
from django.conf import settings
from .models import EnvVar, App
from shapeblock.deployments.models import Deployment

from .kubernetes import run_deploy_pipeline

logger = logging.getLogger("django")


def create_and_trigger_deployment(app, user, deployment_type="config"):
    # if app status is created and no last deployment exists
    if app.status == "created":
        return
    #TODO: if app status is created and last deployment failed, trigger a new code deployment
    last_deployment = Deployment.objects.filter(app=app, type__in=["code", "config"], status="success").latest(
        "created_at"
    )
    # TODO: what to do if last_deployment doesn't exist
    deployment = Deployment.objects.create(user=user, app=app, type=deployment_type, ref=last_deployment.ref)
    run_deploy_pipeline(deployment)
    app.status = "building"
    app.save()


def create_env_vars(app_service):
    service = app_service.service
    app = app_service.app
    if app_service.exposed_as == "url":
        if service.type == "mysql":
            EnvVar.objects.create(
                key="DATABASE_URL",
                value=f"mysql://shapeblock:shapeblock@{service.service_statefulset}/shapeblock",
                app=app,
                service=service,
            )
        if service.type == "postgres":
            EnvVar.objects.create(
                key="DATABASE_URL",
                value=f"postgres://shapeblock:shapeblock@{service.service_statefulset}/shapeblock",
                app=app,
                service=service,
            )
        if service.type == "mongodb":
            EnvVar.objects.create(
                key="DATABASE_URL",
                value=f"mongodb://shapeblock:shapeblock@{service.service_statefulset}/shapeblock",
                app=app,
                service=service,
            )
        if service.type == "redis":
            EnvVar.objects.create(
                key="REDIS_URL",
                value=f"redis://:shapeblock@{service.service_statefulset}",
                app=app,
                service=service,
            )
    else:
        if service.type in ["mongodb", "postgres", "mysql"]:
            EnvVar.objects.create(key="DB_HOST", value=f"{service.service_statefulset}", app=app, service=service)
            EnvVar.objects.create(key="DB_NAME", value="shapeblock", app=app, service=service)
            EnvVar.objects.create(key="DB_USER", value="shapeblock", app=app, service=service)
            EnvVar.objects.create(key="DB_PASSWORD", value="shapeblock", app=app, service=service)
        if service.type == "redis":
            EnvVar.objects.create(key="REDIS_HOST", value=f"{service.service_statefulset}", app=app, service=service)
            EnvVar.objects.create(key="REDIS_PASSWORD", value="shapeblock", app=app, service=service)


def delete_env_vars(app_service):
    app = app_service.app
    service = app_service.service
    deleted_count, _ = EnvVar.objects.filter(app=app, service=service).delete()
    return deleted_count


def generate_ecdsa_keys():
    private_key = ec.generate_private_key(ec.SECP384R1())
    public_key = private_key.public_key()
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH
    )
    return private_key_pem.decode(), public_key_pem.decode()


def add_github_deploy_key(app: App):
    token = app.get_github_user_token()
    if not token:
        return
    protocol, repo_fullname = app.get_repo_details()
    repo = github.get_repo(token, repo_fullname)
    if not repo.private:
        return
    if protocol != "git":
        return
    private_key, public_key = generate_ecdsa_keys()
    key_id = github.add_deploy_key(repo, f"Added by SB for application {app.name}", public_key)
    app.key_config = {
        "public_key": public_key,
        "private_key": private_key,
        "key_id": key_id,
        "annotation": "git@github.com",
    }
    app.save()


def add_github_webhook(app: App):
    token = app.get_github_user_token()
    if not token:
        return
    protocol, repo_fullname = app.get_repo_details()
    repo = github.get_repo(token, repo_fullname)
    if not repo.private:
        return
    if protocol != "git":
        return
    webhook_config = {"url": f"{settings.SB_URL}/webhook/", "content_type": "json"}
    hook = repo.create_hook(name="web", config=webhook_config, events=["push"], active=True)

    logger.info(f"Webhook created with id: {hook.id} for app {app.name}.")
    app.autodeploy = True
    app.webhook_id = hook.id
    app.save()


def trigger_deploy_from_github_webhook(request_headers, body):
    github_hook_id = request_headers.get("X-GitHub-Hook-ID")
    if not github_hook_id:
        return
    webhook_event = request_headers.get("X-GitHub-Event")
    if webhook_event != "push":
        return
    try:
        app = App.objects.get(webhook_id=github_hook_id)
    except App.DoesNotExist:
        logger.error(f"App with {github_hook_id} doesn't exist.")
        return
    if not app.autodeploy:
        return
    fullname_ref = body.get("ref")
    ref = fullname_ref.split("/")[-1]
    if app.ref != ref:
        logger.info(f"Webhook ref {ref} doesn't match the ref '{app.ref}' configured in app.")
        return
    delivery_id = request_headers.get("X-GitHub-Delivery")
    sha = body.get("after")
    if sha:
        deployment = Deployment.objects.create(user=app.user, app=app, type="code", ref=sha)
        run_deploy_pipeline(deployment)
        app.status = "building"
        app.save()
    logger.info(f"Triggering deployment for webhook {delivery_id} in app {app.name}.")


def get_kubeconfig():
    with open('/var/run/secrets/kubernetes.io/serviceaccount/ca.crt', 'r') as ca_crt_file:
        ca_crt = ca_crt_file.read()

    with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as token_file:
        token = token_file.read()

    external_kube_api_url = settings.CONTROL_PLANE_IP

    base64_ca_crt = base64.b64encode(ca_crt.encode('utf-8')).decode('utf-8')
    kubeconfig = f"""
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority: {base64_ca_crt}
    server: {external_kube_api_url}
    name: external-cluster
contexts:
- context:
    cluster: external-cluster
    user: default
    name: external-cluster
current-context: external-cluster
users:
- name: default
  user:
    token: {token}
    """
    return kubeconfig
