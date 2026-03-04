"""
Signals for user/social account sync (e.g. keep User.oauth_provider and User.oauth_id in sync with SocialAccount).
"""
from allauth.socialaccount.signals import social_account_added
from django.dispatch import receiver


@receiver(social_account_added)
def sync_user_oauth_fields(sender, request, sociallogin, **kwargs):
    """When a social account is linked, update our User.oauth_provider and oauth_id."""
    user = sociallogin.user
    account = sociallogin.account
    if user and account:
        user.oauth_provider = account.provider
        user.oauth_id = account.uid
        user.save(update_fields=['oauth_provider', 'oauth_id'])
