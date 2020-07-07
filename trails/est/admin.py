from django.contrib import admin

from est.models import Import


def activate(modeladmin, request, queryset):
    queryset.update(active='True')


class ImportAdmin(admin.ModelAdmin):
    list_display = ("num_parks", "active", "name", "updated_at", "complete")
    readonly_fields = ("num_parks",)

    actions = [activate]

    def num_parks(self, obj: Import):
        return obj.networks.count()


admin.site.register(Import, ImportAdmin)

# Register your models here.
