from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin
)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from transactions.models import Summary, Space
from users.models import User
from .serializers import (
    TransactionCreateSerializer,
    GroupCreateSerializer,
    GroupDetailSerializer,
    SummarySerializer,
    TransactionDetailSerializer,
    LinkUserToSpaceSerializer,
    UnlinkUserToSpaceSerializer,
    SpaceSerializer
)


class TransactionViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    GenericViewSet
):
    """Отображение и создание для transactions."""

    serializer_class = TransactionCreateSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('period_month', 'period_year', 'space__id')
    search_fields = ('^group_name',)

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        return self.get_user().transactions

    def get_serializer_class(self):
        if self.action == 'create':
            return TransactionCreateSerializer
        return TransactionDetailSerializer

    def perform_create(self, serializer):
        user = self.get_user()
        with transaction.atomic():
            serializer.save(
                author=user,
                space=user.core_settings.current_space,
                period_month=user.core_settings.current_month,
                period_year=user.core_settings.current_year
            )
            summary = Summary.objects.get(
                space=user.core_settings.current_space,
                period_month=user.core_settings.current_month,
                period_year=user.core_settings.current_year,
                type_transaction=serializer.validated_data['type_transaction'],
                group_name=serializer.validated_data['group_name']
            )
            summary.fact_value += serializer.validated_data[
                'value_transaction'
            ]
            summary.save()


class GroupViewSet(ModelViewSet):
    """CRUD для group."""

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        return Summary.objects.filter(basename__user_id=self.kwargs['user_id'])

    def get_serializer_class(self):
        if self.action == 'create':
            return GroupCreateSerializer
        return GroupDetailSerializer

    def perform_create(self, serializer):
        user = self.get_user()
        serializer.save(
            basename=user.core_settings.current_basename
        )


class SummaryViewSet(
    ListModelMixin,
    GenericViewSet
):
    """Просмотр Summary."""

    serializer_class = SummarySerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('group_name', 'type_transaction')
    search_fields = ('^group_name',)

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        user = self.get_user()
        return Summary.objects.filter(
            space=user.core_settings.current_space,
            period_month=user.core_settings.current_month,
            period_year=user.core_settings.current_year
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        user = self.get_user()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'username': user.username,
                'period_month': user.core_settings.current_month,
                'period_year': user.core_settings.current_year,
                'current_space_id': user.core_settings.current_space.id,
                'summary': serializer.data
            }
        )


class SpaceViewSet(ModelViewSet):
    """CRUD для Basename."""

    serializer_class = SpaceSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)

    def get_user(self):
        return get_object_or_404(User, pk=self.kwargs['user_id'])

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        return Space.objects.filter(user_id=self.kwargs['user_id'])

    def perform_create(self, serializer):
        serializer.save(user=self.get_user())

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        user = self.get_user()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'owner_id': user.id,
                'owner_username': user.username,
                'spaces': serializer.data
            }
        )

    @swagger_auto_schema(
        tags=['Подключение/отключение пользователей'],
        operation_description='Подключение пользователя к базе',
        responses={
            status.HTTP_200_OK:
                f'Пользователь username '
                f'(id 1) подключен к базе '
                f'user_base '
                f'(id 11) '
                f'пользователя username_2 '
                f'(id 22).'
        },
        request_body=LinkUserToSpaceSerializer
    )
    @action(detail=True, methods=['post'], url_path='link_user')
    def link_user(self, request, user_id, pk=None):
        serializer = LinkUserToSpaceSerializer(
            data=request.data,
            context={'space_id': pk, 'user_id': int(user_id)}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {
                'status': f'Пользователь {instance.linked_user.username} '
                          f'(id {instance.linked_user.id}) подключен к базе '
                          f'{instance.space.name} '
                          f'(id {instance.space.id}) '
                          f'пользователя {instance.space.user.username} '
                          f'(id {instance.space.user.id}).'
            },
            status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        tags=['Подключение/отключение пользователей'],
        operation_description='Отключение пользователя от базы',
        responses={
            status.HTTP_200_OK:
                f'Пользователь username '
                f'(id 1) отключен от базы '
                f'user_base '
                f'(id 11) '
                f'пользователя username_2 '
                f'(id 22).'
        },
        request_body=UnlinkUserToSpaceSerializer
    )
    @action(detail=True, methods=['post'], url_path='unlink_user')
    def unlink_user(self, request, user_id, pk=None):
        serializer = UnlinkUserToSpaceSerializer(
            data=request.data,
            context={'space_id': pk, 'user_id': int(user_id)}
        )
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        serializer.delete(vd)
        return Response(
            {
                'status': f'Пользователь {vd['linked_user'].username} '
                          f'(id {vd['linked_user'].id}) отключен от базы '
                          f'{vd['space'].name} '
                          f'(id {vd['space'].id}) '
                          f'пользователя {vd['space'].user.username} '
                          f'(id {vd['space'].user.id}).'
            },
            status=status.HTTP_200_OK
        )
