from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from strava.api.helpers.request import request_handler
from strava.api.helpers.request import restricted
from strava.api.auth import verified_tokens
from strava.api.helpers.request import request_handler, restricted, get_body
from django.http import JsonResponse
from strava.api.activities import (
    get_activity_strava,
    update_activity_description,
    generate_activity_description,
)
import os


@csrf_exempt
def webhook(request) -> JsonResponse:
    def read(request):
        return handle_webhook_subscribe(request, os.environ.get("VERIFY_TOKEN"))

    def create(request):
        body = get_body(request)
        object_type, aspect_type = body["object_type"], body["aspect_type"]
        is_activity_creation = object_type == "activity" and aspect_type == "create"
        if not is_activity_creation:
            return JsonResponse({"skip": "yes, not an activity creation"}, status=200)
        user_id, activity_id = body["owner_id"], body["object_id"]
        res, description = handle_activity_webhook(user_id, activity_id)
        if not res.status_code in ["200", "201", 200, 201]:
            return JsonResponse({"error": f"{res}"}, status=res.status_code)
        return JsonResponse({"success": f"{description}"}, status=200)

    return request_handler(create, read, restricted, restricted)(request)


def handle_activity_webhook(user_id, activity_id):
    access_token, _ = verified_tokens(user_id)
    activity = get_activity_strava(activity_id, access_token)
    description = generate_activity_description(activity)
    res = update_activity_description(activity_id, description, access_token)
    return res, description


def handle_webhook_subscribe(request, secret_token) -> JsonResponse:
    mode, token, challenge = (
        request.GET.get("hub.mode"),
        request.GET.get("hub.verify_token"),
        request.GET.get("hub.challenge"),
    )

    is_invalid = not mode or not token or not challenge
    is_subscribable = mode == "subscribe" and token == secret_token

    if is_invalid:
        return JsonResponse({"error": "Bad request"}, status=400)
    if is_subscribable:
        return JsonResponse({"hub.challenge": challenge})

    return JsonResponse({"error": "Forbidden"}, status=403)
