from django.db import models


class DeleteQuerySet(models.QuerySet):
    """
    This QuerySet is adapted to deal with the
    complexities of deleting objects that have potentially
    locked objects on the DRC API.

    Force delete will attempt to unlock the document in the DRC API
    and then continue to delete.
    """

    def delete(self):
        for instance in self:
            instance.delete()

    # This should probably be called asynchronously
    def force_delete(self):
        for instance in self:
            instance.force_delete()