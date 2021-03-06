import random

from django.http import HttpResponseNotFound
from django.contrib.contenttypes.models import ContentType
from likes.utils import (can_vote, can_like, can_unlike, likes_enabled,
                         VOTE_MIN, VOTE_MAX)

from secretballot import views

from likes import signals


def can_vote_test(request, content_type, object_id, vote):
    # if vote not in ['0', '1']:
    vote_val = int(vote)
    if vote_val < VOTE_MIN or vote_val > VOTE_MAX:
        return False

    return can_vote(
        content_type.get_object_for_this_type(id=object_id),
        request.user,
        request
    )


def like(request, content_type, id, vote):
    # Crawlers will follow the like link if anonymous liking is enabled. They
    # typically do not have referrer set.
    if 'HTTP_REFERER' not in request.META:
        return HttpResponseNotFound()

    url_friendly_content_type = content_type
    app, modelname = content_type.split('-')
    content_type = ContentType.objects.get(app_label=app,
                                           model__iexact=modelname)

    ct_class = content_type.model_class()
    obj = ct_class.objects.get(pk=id)

    if request.is_ajax():
        response = views.vote(
            request,
            content_type=content_type,
            object_id=id,
            vote=vote,
            template_name='likes/inclusion_tags/likes.html',
            can_vote_test=can_vote_test,
            extra_context={
                'likes_enabled': likes_enabled(obj, request),
                'can_vote': can_vote(obj, request.user, request),
                'can_like': not can_like(obj, request.user, request),
                'can_unlike': not can_unlike(obj, request.user, request),
                'content_obj': obj,
                "content_type": url_friendly_content_type
            }
        )
    else:
        # Redirect to referer but append unique number(determined
        # from global vote count) to end of URL to bypass local cache.
        redirect_url = '%s?v=%s' % (request.META['HTTP_REFERER'],
                                    random.randint(0, 10))
        response = views.vote(
            request,
            content_type=content_type,
            object_id=id,
            vote=vote,
            redirect_url=redirect_url,
            can_vote_test=can_vote_test
        )

    signals.object_liked.send(
        sender=content_type.model_class(),
        instance=content_type.get_object_for_this_type(id=id),
        request=request)
    return response
