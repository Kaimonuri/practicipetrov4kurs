from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from shop.admin_site import lab_admin_site

urlpatterns = [
    path('admin/', lab_admin_site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('shop.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
