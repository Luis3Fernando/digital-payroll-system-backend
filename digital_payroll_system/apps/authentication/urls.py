from django.urls import path
from .views import AuthViewSet

login_view = AuthViewSet.as_view({'post': 'login'})
logout_view = AuthViewSet.as_view({'post': 'logout'})
refresh_view = AuthViewSet.as_view({'post': 'refresh'})

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('refresh/', refresh_view, name='refresh'),
]
