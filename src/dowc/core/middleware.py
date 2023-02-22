import logging

logger = logging.getLogger(__name__)


def request_response_logger_middleware(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if "core" in request.path or "_api" in request.path:
            logger.warning("REQUEST: {request}".format(request=request.__dict__))
            if hasattr(request, "auth"):
                logger.warning("AUTH: {auth}".format(auth=request.auth))
            if hasattr(request, "user"):
                logger.warning("USER: {user}".format(user=request.user))

        response = get_response(request)
        if "core" in request.path or "_api" in request.path:
            logger.warning("RESPONSE: {response}".format(response=response.__dict__))

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware
