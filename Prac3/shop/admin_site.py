from django.contrib.admin import AdminSite


class LabAdminSite(AdminSite):
    site_header = 'Администрирование мебельного магазина'
    site_title = 'Админ-панель'
    index_title = 'Управление магазином'

    def has_permission(self, request):
        return (
            super().has_permission(request)
            and request.user.username == 'Lab16'
        )


lab_admin_site = LabAdminSite(name='lab_admin')
