from django.db import models, transaction


class DeleteQuerySet(models.QuerySet):
    """
    This QuerySet is adapted to deal with the
    complexities of deleting objects that have potentially 
    locked objects on the DRC API.
    """

    @transaction.atomic
    def delete(self):
        [instance.delete() for instance in self]

    def force_delete(self):
        for instance in self:
            instance.unlock_drc_document()
            instance.delete()


class DeletionManager(models.Manager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        return DeleteQuerySet(model=self.model, using=self._db)
