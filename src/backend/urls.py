"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from api.views import GenerateMapView, IndicadorListView, EstabelecimentosSaudeProxy, EstabelecimentosView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/generate_map/', GenerateMapView.as_view(), name='generate_map'),
    path('api/indicadores/', IndicadorListView.as_view(), name='indicadores_list'),
    # path('api/estabelecimentos/', EstabelecimentosSaudeProxy.as_view(), name='estabelecimentos-saude-proxy'),
    path('api/estabelecimentos/', EstabelecimentosView.as_view(), name='estabelecimentos'),
]
