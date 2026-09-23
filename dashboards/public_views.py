from django.http import Http404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ShareLink
from .serializers import PublicDashboardSerializer


class PublicDashboardView(APIView):
    # The one place in this project with AllowAny instead of the default
    # IsAuthenticated (see REST_FRAMEWORK settings) — kept in its own module
    # so that's easy to spot on review.
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            link = ShareLink.objects.select_related("dashboard__dataset").get(
                token=token,
                revoked_at__isnull=True,
                # dashboard__deleted_at is explicit here on purpose: this
                # queries ShareLink directly, so it does NOT go through
                # Dashboard's own soft-delete manager — a soft-deleted
                # dashboard's share link would otherwise keep resolving.
                dashboard__deleted_at__isnull=True,
            )
        except ShareLink.DoesNotExist:
            # A nonexistent token, a revoked one, and one whose dashboard was
            # soft-deleted all hit this exact same path and the exact same
            # 404 — don't leak which is which.
            raise Http404() from None

        return Response(PublicDashboardSerializer(link.dashboard).data)
