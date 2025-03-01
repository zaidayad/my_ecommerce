import datetime
import logging
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone  # لإضافة التاريخ والوقت الحالي

# تعريف logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="categories/", default="default.jpg")

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(
        Category, related_name="products", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="product_images/", blank=True, null=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def discounted_price(self):
        """حساب السعر بعد الخصم كدالة"""
        return self.price * (1 - self.discount_percentage / Decimal("100"))

    def reduce_stock(self, quantity_sold):
        """تقليل الكمية المتبقية للمخزون"""
        if self.stock >= quantity_sold:
            self.stock -= quantity_sold
            self.save()  # حفظ التحديث في قاعدة البيانات
            logger.info(
                f"تم تقليل المخزون للمنتج {self.name} بمقدار {quantity_sold}. المخزون المتبقي: {self.stock}"
            )
        else:
            logger.error(f"الكمية المطلوبة أكثر من المخزون المتاح للمنتج {self.name}.")
            raise ValueError(
                f"الكمية المطلوبة أكبر من المخزون المتاح للمنتج {self.name}."
            )


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)

    def __str__(self):
        return self.user.username


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    # هنا يمكنك تعيين معرف مستخدم افتراضي
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=1
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def total_price(self):
        return self.product.discounted_price() * self.quantity  #


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()  # يمكن أن يكون بين 1 و 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Order(models.Model):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(default=timezone.now)
    delivery_person = models.ForeignKey(
        "DeliveryPerson",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )

    def __str__(self):
        return f"Order {self.id} by {self.customer.username}"

    def complete_order(self):
        """إتمام الطلب وتقليل المخزون"""
        if self.status != Order.COMPLETED:
            self.status = Order.COMPLETED
            self.save()  # تحديث حالة الطلب
            logger.info(f"تم تحديث حالة الطلب رقم {self.id} إلى مكتمل")

            # التحقق من العناصر في الطلب وتقليل المخزون
            for item in self.items.all():
                product = item.product
                logger.info(
                    f"المنتج: {product.name}, الكمية المطلوبة: {item.quantity}, المخزون الحالي: {product.stock}"
                )

                try:
                    product.reduce_stock(item.quantity)  # تقليل المخزون
                except ValueError as e:
                    logger.error(f"خطأ في تقليل المخزون: {e}")
            logger.info(f"تم إتمام الطلب رقم {self.id} بنجاح وتحديث المخزون.")
        else:
            logger.info(f"الطلب رقم {self.id} تم إتمامه مسبقًا.")


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, related_name="orderitems", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def total_price(self):
        return self.product.discounted_price() * self.quantity


# في حالة استخدام إشارات post_save لتقليل المخزون عند إتمام الطلب


@receiver(post_save, sender=Order)
def update_inventory_after_order_complete(sender, instance, created, **kwargs):
    """تقليل المخزون بعد إتمام الطلب"""
    if instance.status == Order.COMPLETED:
        logger.info(f"بدء تقليل المخزون للطلب رقم {instance.id}")

        # تأكد من أن هناك عناصر في الطلب
        for item in instance.items.all():
            try:
                product = item.product
                logger.info(
                    f"المنتج: {product.name}, الكمية المطلوبة: {item.quantity}, المخزون الحالي: {product.stock}"
                )

                if product.stock >= item.quantity:
                    product.stock -= item.quantity  # تقليل المخزون
                    product.save()
                    logger.info(
                        f"تم تقليل {item.quantity} من {product.name}. المخزون المتبقي: {product.stock}"
                    )
                else:
                    logger.error(
                        f"لا يوجد كمية كافية من {product.name} لتلبية الطلب. الكمية المطلوبة: {item.quantity}, الكمية المتوفرة: {product.stock}"
                    )
            except ValueError as e:
                logger.error(f"خطأ في تقليل المخزون: {e}")


class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    # Use this if you want custom default
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.message


# def __str__(self):
#     return f"Notification for {self.user.username} - {self.message}"

# إشارة لإرسال إشعار للمشرف عند إضافة طلب جديد


@receiver(post_save, sender=Order)
def send_order_notification(sender, instance, created, **kwargs):
    if created:  # إذا تم إنشاء طلب جديد
        # إرسال إشعار للمشرفين
        supervisors = User.objects.filter(is_staff=True)  # إذا كان المستخدم مشرف
        for supervisor in supervisors:
            Notification.objects.create(
                user=supervisor,
                message=f"تم تقديم طلب جديد من الزبون {instance.customer.username}.",
            )
    elif instance.status == "completed":
        # إرسال إشعار للمشرفين عند اكتمال الطلب
        supervisors = User.objects.filter(is_staff=True)
        for supervisor in supervisors:
            Notification.objects.create(
                user=supervisor,
                message=f"تم إتمام الطلب رقم {instance.id} من الزبون {instance.customer.username}.",
            )


class DeliveryPerson(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    age = models.IntegerField()

    STATUS_CHOICES = [
        ("available", "متاح"),
        ("busy", "مشغول"),
    ]
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="available"
    )

    order = models.ForeignKey(
        "Order",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delivery",
    )
    order_status = models.CharField(max_length=255, null=False, default="في الطريق")

    def __str__(self):
        return self.name if self.name else "اسم الموصل غير محدد"


class Ticket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=100, default="Open")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.id} by {self.user.username}"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(
        "Product", on_delete=models.CASCADE, related_name="wishlist_items"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # كل منتج يجب أن يكون فريدًا في قائمة المفضلة لكل مستخدم
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
