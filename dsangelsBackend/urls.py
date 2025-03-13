from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('api.authentication.urls')),
    path('api/content/', include('api.content.urls')),
    path('api/progress/', include('api.progress.urls')),
    path('api/gamification/', include('api.gamification.urls')),
    path('api/community/', include('api.community.urls')),
    path('api/analytics/', include('api.analytics.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)