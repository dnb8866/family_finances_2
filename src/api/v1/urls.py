from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.v1.users import views as user_views
from api.v1.transactions import views as transactions_views

app_name = 'api_v1'

router_v1 = DefaultRouter()
router_v1.register('users', user_views.UserViewSet, basename='users')
router_v1.register(
    r'users/(?P<user_id>\d+)/transactions',
    transactions_views.TransactionViewSet,
    basename='user_transactions'
)
router_v1.register(
    r'users/(?P<user_id>\d+)/groups',
    transactions_views.GroupViewSet,
    basename='user_groups'
)
router_v1.register(
    r'users/(?P<user_id>\d+)/summary',
    transactions_views.SummaryViewSet,
    basename='user_summary'
)
router_v1.register(
    r'users/(?P<user_id>\d+)/basenames',
    transactions_views.BasenameViewSet,
    basename='user_basenames'
)

urlpatterns = [
    path(
        '',
        include(router_v1.urls)
    ),
    path(
        'users/<int:user_id>/core-settings/',
        user_views.CoreSettingsViewSet.as_view(
            {'put': 'update', 'get': 'list', 'patch': 'partial_update'}
        )
    ),
    path(
        'users/<int:user_id>/telegram-settings/',
        user_views.TelegramSettingsViewSet.as_view(
            {'put': 'update', 'get': 'list', 'patch': 'partial_update'}
        )
    )
]