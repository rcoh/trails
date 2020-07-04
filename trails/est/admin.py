from django.contrib import admin

from est.models import Import


class ImportAdmin(admin.ModelAdmin):
    list_display = ("num_parks", )
    readonly_fields = ("num_parks",)

    def num_parks(self, obj: Import):
        return obj.networks.count()


admin.site.register(Import, ImportAdmin)

# Register your models here.
