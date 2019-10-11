from django.contrib import admin
from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views
#from . import pdf_view

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
#    path('pdf/', views.IndexPrintView.as_view(), name='pdf'),
    #path('pdf/', pdf_view.make_pdf, name='pdf'),
    url(r'^login/', views.user_login, name='login'),
    url(r'^logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
    #path('login/', auth_views.LoginView.as_view(), name='login'),
    #path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    #path('admin/', admin.site.urls),
    #path('login/', auth_views.LoginView.as_view(template_name='extractor/login.html')),
    #path('logout/', auth_views.LogoutView.as_view(template_name='extractor/logout.html'))
]
