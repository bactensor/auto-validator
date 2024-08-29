from django.core.files.storage import default_storage
from django.db import models  # noqa


class UploadedFile(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    file_name = models.CharField(max_length=4095)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    storage_file_name = models.CharField(
        max_length=4095,
        db_comment="File name (id) in Django Storage",
    )
    file_size = models.PositiveBigIntegerField(db_comment="File size in bytes")

    def __str__(self):
        return f"{self.file_name!r} uploaded by {self.user}"

    @property
    def url(self):
        return default_storage.url(self.storage_file_name)
