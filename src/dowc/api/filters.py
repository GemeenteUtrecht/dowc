from django_filters.rest_framework.backends import DjangoFilterBackend

from dowc.accounts.models import ApplicationToken


class IsOwnerOrApplicationFilterBackend(DjangoFilterBackend):
    """
    Filter that only allows users to see their own objects.

    """

    def filter_queryset(self, request, queryset, view):
        if request.auth and isinstance(request.auth, ApplicationToken):
            return super().filter_queryset(request, queryset, view)

        if view.action == "list":
            return super().filter_queryset(
                request, queryset.filter(user=request.user), view
            )

        return super().filter_queryset(request, queryset, view)
