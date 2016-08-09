import json
from typing import Tuple

from django.http import HttpResponse


def json_response(data: dict = None, message: str = None,
                  status_code: int = None, headers: dict = None) -> HttpResponse:
    response = HttpResponse(content_type="application/json",
                            status=status_code,
                            content=json.dumps({
                                "data": data,
                                "message": message})
                            )

    if headers:
        for header, value in headers.items():
            response[header] = value
    return response


def is_valid_hashtag(hashtag: str) -> Tuple[bool, str]:
    """
    check if hashtag is valid
    return validity and message
    """
    if not hashtag.startswith("#"):
        return False, 'Hashtag "%s" must starts with "#" sign' % hashtag
    if hashtag.count(" ") > 0:
        return False, 'Hashtag "%s" cannot contain whitespaces' % hashtag

    return True, None
