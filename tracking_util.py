from .models import UserLoginActivity

#from icecream import ic

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def save_activity(request):
    """Given a particular login request, pull out the properties of interest and save
    them to an instance of the UserLoginActivity model."""
    user_agent_info = request.META.get('HTTP_USER_AGENT', '<unknown>')[:255]

    user_login_activity_log = UserLoginActivity(login_IP=get_client_ip(request),
                                                login_username=request.user.username,
                                                user=request.user,
                                                user_agent_info=user_agent_info,
                                                status=UserLoginActivity.SUCCESS)
    user_login_activity_log.save()
