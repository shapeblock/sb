from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from rest_framework import status

from django.contrib.auth import get_user_model

User = get_user_model()


class AddUserGithubTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        github_token = data.get("github_token", None)

        if github_token:
            user.github_token = github_token
            user.save()
            return Response(
                {"detail": "Github token updated successfully."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"detail": "Invalid input."}, status=status.HTTP_400_BAD_REQUEST
            )


class GithubClientInfoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not settings.GITHUB_CLIENT_KEY:
            return Response(
                "This installation cannnot be integrated with Github. Please add a GITHUB_CLIENT_KEY and GITHUB_CLIENT_SECRET and re-deploy the application."
            )
        data = {
            "client_id": settings.GITHUB_CLIENT_KEY,
            "secret": settings.GITHUB_CLIENT_SECRET,
        }
        return Response(data)
