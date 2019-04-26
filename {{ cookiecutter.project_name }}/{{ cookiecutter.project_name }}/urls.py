from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path, register_converter
from django.urls.converters import StringConverter
from django.views.generic import RedirectView, TemplateView


class UnicodeSlugConverter(StringConverter):
    regex = r'[-\w]+'


register_converter(UnicodeSlugConverter, 'unicode_slug')


urlpatterns = [
    path('',
         TemplateView.as_view(template_name='index.html'), name='index'),
    path('favicon.ico',
         RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'),
                              permanent=True)),
    path('robots.txt',
         TemplateView.as_view(template_name='robots.txt',
                              content_type='text/plain')),
    path('admin/',
         admin.site.urls),
]


# DEBUG TOOLBAR
if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls))
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# Тестировать 404 страницу
if getattr(settings, 'DEBUG404', False):
    from django.views.static import serve

    urlpatterns += [
        path('media/<path:path>/',
             serve, {'document_root': settings.MEDIA_ROOT}),
        path('static/<path:path>/',
             serve, {'document_root': settings.STATIC_ROOT})
    ]
