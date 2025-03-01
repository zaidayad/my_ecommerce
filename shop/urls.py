from django.conf.urls.static import static
from django.urls import path

from .views import *
from .views import (cart_view, login_view, product_list, register,
                    remove_from_cart, supervisor_dashboard)

urlpatterns = [
    path("register/", register, name="register"),
    path("", login_view, name="login"),
    path("categories/", category_list, name="category_list"),
    path("categories/<int:category_id>/", product_list, name="product_list"),
    path("add_to_cart/<int:product_id>/", add_to_cart, name="add_to_cart"),
    path("cart/", cart_view, name="cart_view"),
    path("checkout/", checkout, name="checkout"),
    path("products/<int:product_id>/", product_detail, name="product_detail"),
    path("cart/remove/<int:item_id>/", remove_from_cart, name="remove_from_cart"),
    path("order_success/<int:order_id>/", order_success, name="order_success"),
    path("supervisor/", supervisor_dashboard, name="supervisor_dashboard"),
    path(
        "supervisor/update_order/<int:order_id>/",
        update_order_status,
        name="update_order_status",
    ),
    path("supervisor/products/", product_management, name="product_management"),
    path("supervisor/product/add/", add_product, name="add_product"),
    path(
        "supervisor/product/edit/<int:product_id>/", edit_product, name="edit_product"
    ),
    path(
        "supervisor/product/delete/<int:product_id>/",
        delete_product,
        name="delete_product",
    ),
    path("notifications/", notifications_list, name="notifications_list"),
    path(
        "notification/<int:notification_id>/mark_as_read/",
        mark_notification_as_read,
        name="mark_notification_as_read",
    ),
    # رابط صفحة إدارة المخزون
    path("manage/", manage_inventory, name="manage_inventory"),
    path("reduce_stock/<int:product_id>/", reduce_stock, name="reduce_stock"),
    path("order/<int:order_id>/complete/", complete_order, name="complete_order"),
    path(
        "supervisor/add_delivery_person/",
        add_delivery_person,
        name="add_delivery_person",
    ),
    path("delivery_person/login/", delivery_person_login, name="delivery_person_login"),
    path(
        "delivery_person/dashboard/",
        delivery_person_dashboard,
        name="delivery_person_dashboard",
    ),
    path(
        "supervisor/delivery_persons/",
        supervisor_delivery_persons,
        name="supervisor_delivery_persons",
    ),
    # رابط إضافة موصل جديد (خاص بالمشرف)
    path(
        "supervisor/create_delivery_person/",
        add_delivery_person,
        name="create_delivery_person",
    ),
    # رابط تسجيل دخول الموصّل
    path("delivery_person/login/", delivery_person_login, name="delivery_person_login"),
    # رابط لوحة تحكم الموصّل
    path("dashboard/", delivery_person_dashboard, name="delivery_person_dashboard"),
    # رابط تغيير حالة الموصّل (متاح/مشغول)
    path("change_status/", change_status, name="change_status"),
    # رابط عرض جميع الموصلي الطلبات (خاص بالمشرف)
    path(
        "supervisor/delivery_persons/",
        supervisor_delivery_persons,
        name="supervisor_delivery_persons",
    ),
    # رابط تحديث حالة الموصّل من قبل المشرف
    path(
        "supervisor/update_status/<int:delivery_person_id>/",
        update_delivery_person_status,
        name="update_delivery_person_status",
    ),
    path(
        "update_delivery_person_order/",
        update_delivery_person_order,
        name="update_delivery_person_order",
    ),
    path(
        "supervisor/update_order/<int:order_id>/",
        delivery_person_order,
        name="delivery_person_order",
    ),
    path("order-history/", order_history, name="order_history"),
    path("create-ticket/", create_ticket, name="create_ticket"),
    path("wishlist/", wishlist_view, name="wishlist_view"),
    path("wishlist/add/<int:product_id>/", add_to_wishlist, name="add_to_wishlist"),
    path(
        "wishlist/remove/<int:product_id>/",
        remove_from_wishlist,
        name="remove_from_wishlist",
    ),
]
