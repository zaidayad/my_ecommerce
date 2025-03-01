import logging

from django.contrib import admin
from django.utils import timezone

from .models import (Category, CustomerProfile,  # قم بحذف الاستيراد المكرر
                     Order, OrderItem, Product)

logger = logging.getLogger(__name__)


class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock", "category")
    search_fields = ("name",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ("product", "quantity")  #


class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "created_at"]
    actions = ["complete_order"]
    # إضافة OrderItem كـ Inline ModelAdmin داخل Order
    inlines = [OrderItemInline]

    def complete_order(self, request, queryset):
        """أمر مخصص لإتمام الطلبات وتقليل المخزون"""
        for order in queryset:
            logger.info(
                f"بدأ إتمام الطلب رقم {order.id} - الحالة الحالية: {order.status}"
            )

            # التأكد من أن حالة الطلب غير مكتملة
            if order.status != Order.COMPLETED:
                order.status = Order.COMPLETED
                order.save()

                logger.info(f"تم تحديث حالة الطلب رقم {order.id} إلى مكتمل")

                # التحقق من العناصر في الطلب وتقليل المخزون
                for item in order.items.all():
                    product = item.product
                    logger.info(
                        f"المنتج: {product.name}, الكمية المطلوبة: {item.quantity}, المخزون الحالي: {product.stock}"
                    )

                    # التأكد من وجود كمية كافية في المخزون
                    if product.stock >= item.quantity:
                        product.stock -= item.quantity  # تقليل المخزون
                        product.save()  # تأكد من حفظ التحديثات في قاعدة البيانات
                        logger.info(
                            f"تم تقليل المخزون للمنتج {product.name} بمقدار {item.quantity}. المخزون المتبقي: {product.stock}"
                        )
                    else:
                        logger.error(
                            f"لا يوجد كمية كافية من {product.name} لتلبية الطلب. الكمية المطلوبة: {item.quantity}, الكمية المتوفرة: {product.stock}"
                        )

                self.message_user(
                    request, f"تم إتمام الطلب رقم {order.id} بنجاح وتحديث المخزون."
                )
            else:
                logger.info(f"الطلب رقم {order.id} تم إتمامه مسبقًا.")

    complete_order.short_description = "إتمام الطلبات المحددة"


# تسجيل النماذج في لوحة الإدارة
admin.site.register(Order, OrderAdmin)
admin.site.register(Product)  # تأكد من تسجيل منتج في الأدمن
admin.site.register(Category)
