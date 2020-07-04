from django.contrib import admin

from est.models import Import


class ImportAdmin(admin.ModelAdmin):
    pass


admin.site.register(Import, ImportAdmin)

# Register your models here.
