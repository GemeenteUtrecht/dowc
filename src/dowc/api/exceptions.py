from rest_framework.exceptions import APIException

from dowc.core.constants import DOCUMENT_COULD_NOT_BE_UPDATED


class UpdateException(APIException):
    status_code = 500
    default_detail = DOCUMENT_COULD_NOT_BE_UPDATED
    default_code = "update_error"
