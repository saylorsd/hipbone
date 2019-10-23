from django.contrib import admin
from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views
#from . import pdf_view

from . import weasy_pdf

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^pdf/', weasy_pdf.generate_pdf, name='pdf'),
    #path('pdf/', pdf_view.make_pdf, name='pdf'),
    url(r'^login/', views.user_login, name='login'),
    url(r'login/', views.user_login, name='login'),
    #url(r'^logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'), # Django 1.11,2+ version
    url(r'^logout/$', auth_views.logout, {'template_name': 'registration/logout.html'}, name='logout'), #Django 1.10 version
    url(r'logout/$', auth_views.logout, {'template_name': 'registration/logout.html'}, name='logout'), #Django 1.10 version
    #path('login/', auth_views.LoginView.as_view(), name='login'),
    #path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    #path('admin/', admin.site.urls),
    #path('login/', auth_views.LoginView.as_view(template_name='extractor/login.html')),
    #path('logout/', auth_views.LogoutView.as_view(template_name='extractor/logout.html'))
]
