from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path
from crm_core.views import (
    all_bookings_list,
    adjust_bonus_api,
    analytics_bookings,
    analytics_clients,
    analytics_occupancy,
    analytics_revenue,
    analytics_sessions,
    cancel_booking_api,
    clients_list,
    confirm_booking_api,
    create_booking_api,
    manage_promotions,
    manage_tariffs,
    manager_stats,
    my_bookings_api,
    place_status_list,
    prolong_session,
    promotion_detail,
    start_session_api,
    stop_session,
    tariff_detail,
    tariffs_list,
)
from loyalty.views import apply_referral_api, client_info_api, referral_stats_api, register_client_api


def landing_page(request):
    return render(request, 'landing.html')


operations_dashboard = login_required(lambda request: render(request, 'operations_dashboard.html'))
super_dashboard = login_required(lambda request: render(request, 'super_dashboard.html'))


def health_check(request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_page),
    path('health/', health_check),
    # Дашборды только для залогиненных менеджеров
    path('dashboard/', operations_dashboard),
    path('dispatcher/', operations_dashboard),
    path('manager/', operations_dashboard),
    path('operations/', operations_dashboard),
    path('super/', super_dashboard),

    # API Endpoints
    path('api/place_status/', place_status_list),
    path('api/start_session/', start_session_api),
    path('api/stop_session/<int:session_id>/', stop_session),
    path('api/prolong_session/', prolong_session),
    path('api/client_info/<int:telegram_id>/', client_info_api),
    path('api/register_client/', register_client_api),
    path('api/manager_stats/', manager_stats),
    path('api/clients/', clients_list),
    path('api/tariffs/', tariffs_list),

    path('api/apply_referral/', apply_referral_api),
    path('api/referral_stats/<int:telegram_id>/', referral_stats_api),
    path('api/create_booking/', create_booking_api),
    path('api/my_bookings/<int:telegram_id>/', my_bookings_api),
    path('api/cancel_booking/<int:booking_id>/', cancel_booking_api),
    path('api/confirm_booking/<int:booking_id>/', confirm_booking_api),
    path('api/all_bookings/', all_bookings_list),
    path('api/clients/<int:telegram_id>/bonus/', adjust_bonus_api),

    path('api/tariffs/manage/', manage_tariffs),
    path('api/tariffs/<int:pk>/', tariff_detail),
    path('api/promotions/', manage_promotions),
    path('api/promotions/<int:pk>/', promotion_detail),

    path('api/analytics/revenue/', analytics_revenue),
    path('api/analytics/occupancy/', analytics_occupancy),
    path('api/analytics/clients/', analytics_clients),
    path('api/analytics/sessions/', analytics_sessions),
    path('api/analytics/bookings/', analytics_bookings),
]
