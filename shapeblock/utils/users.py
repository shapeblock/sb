from allauth.socialaccount.models import SocialToken


def get_user_connected_accounts(user):
    tokens = SocialToken.objects.filter(account__user=user)
    if tokens:
        return [
            {
                "id": token.token,
                "name": "{}.com/{}".format(
                    token.account.provider,
                    token.account.extra_data.get("login") or token.account.extra_data.get("username"),
                ),
            }
            for token in tokens
        ]
