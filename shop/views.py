import datetime
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ProductForm  # نحتاج إلى نموذج لإضافة وتعديل المنتجات
from .forms import (CheckoutForm, CustomerProfileForm, DeliveryPersonForm,
                    ReviewForm, UpdateStockForm, UserRegistrationForm)
from .models import *
from .models import Order  # تأكد من أن لديك نموذج الطلب
from .models import (CartItem, Category, DeliveryPerson, Notification,
                     OrderItem, Product, Wishlist)

logger = logging.getLogger(__name__)


def category_list(request):
    categories = Category.objects.all()  # جلب جميع الأقسام
    discounted_products = Product.objects.filter(discount_percentage__gt=0)

    # جلب جميع الأقسام
    categories = Category.objects.all()

    return render(
        request,
        "shop/category_list.html",
        {
            "categories": categories,
            "discounted_products": discounted_products,
        },
    )


# def product_list(request, category_id):
# products = Product.objects.filter(category_id=category_id)  # جلب المنتجات بناءً على القسم
# return render(request, 'shop/product_list.html', {'products': products})


def product_list(request, category_id):
    # تحقق من وجود الفئة
    category = get_object_or_404(Category, id=category_id)

    query = request.GET.get("q", "")
    price_filter = request.GET.get("price_filter", "")

    products = Product.objects.filter(category_id=category_id)

    # فلترة المنتجات بناءً على الاستعلام
    if query:
        products = products.filter(name__icontains=query)

    # فلترة حسب السعر
    if price_filter == "low":
        products = products.filter(price__lt=100)
    elif price_filter == "medium":
        products = products.filter(price__gte=100, price__lte=500)
    elif price_filter == "high":
        products = products.filter(price__gt=500)

    return render(
        request,
        "shop/product_list.html",
        {
            "products": products,
            "query": query,
            "price_filter": price_filter,
            "category_id": category_id,  # تأكد من إرسال category_id هنا
        },
    )


def register(request):
    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)
        profile_form = CustomerProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            return redirect("login")
    else:
        user_form = UserRegistrationForm()
        profile_form = CustomerProfileForm()

    return render(
        request,
        "shop/register.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


def login_view(request):
    error = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # توجيه المستخدم إلى قائمة الأقسام
            return redirect("category_list")
        else:
            error = "فشل تسجيل الدخول، يرجى التحقق من اسم المستخدم وكلمة المرور."

    return render(request, "shop/login.html", {"error": error})


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # توجيه المستخدم بعد تغيير كلمة المرور
            return redirect("category_list")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "shop/change_password.html", {"form": form})


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # احصل على السعر بعد الخصم
    price = product.discounted_price if product.discount_percentage else product.price

    cart_item, created = CartItem.objects.get_or_create(
        product=product, user=request.user, defaults={"quantity": 1, "price": price}
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect("cart_view")


def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.price * item.quantity for item in cart_items)

    if request.method == "POST":
        # تحديث الكميات
        for item in cart_items:
            quantity = request.POST.get(f"quantity_{item.id}")
            if quantity.isdigit():
                item.quantity = int(quantity)
                item.save()
        return redirect("cart_view")

    # معالجة حذف المنتج
    if request.GET.get("action") == "delete":
        item_id = request.GET.get("item_id")
        CartItem.objects.filter(id=item_id, user=request.user).delete()
        return redirect("cart_view")

    return render(request, "shop/cart.html", {"cart_items": cart_items, "total": total})


@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.price * item.quantity for item in cart_items)

    if request.method == "POST":
        total_amount = total

        # الحصول على المعلومات من النموذج
        address = request.POST.get("address")
        phone_number = request.POST.get("phone_number")

        # إنشاء الطلب
        order = Order.objects.create(
            customer=request.user,
            total_amount=total_amount,
            status="pending",
            address=address,
            phone_number=phone_number,
        )

        # إضافة العناصر (المنتجات) من سلة التسوق إلى الطلب
        for item in cart_items:
            product = item.product
            # استدعاء الدالة discounted_price بشكل صحيح هنا
            # إضافة الأقواس () لاستدعاء الدالة
            price = (
                product.discounted_price()
                if product.discount_percentage
                else product.price
            )

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                price=price,  # استخدم السعر المحسوب هنا
            )

        # بعد إنشاء الطلب، سيتم إرسال الإشعار للمشرفين عبر الإشارة (Signal)

        # مسح سلة التسوق بعد تقديم الطلب
        cart_items.delete()

        return redirect("order_success", order_id=order.id)

    return render(
        request,
        "shop/checkout.html",
        {
            "cart_items": cart_items,
            "total": total,
        },
    )


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, "shop/order_success.html", {"order": order})


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = Review.objects.filter(product=product)

    # إنشاء قائمة range لكل تقييم ليتم استخدامها في القالب
    for review in reviews:
        review.star_range = range(review.rating)

    return render(
        request,
        "shop/product_detail.html",
        {
            "product": product,
            "reviews": reviews,
        },
    )


def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    item.delete()
    return redirect("cart_view")


def product_list(request, category_id):
    query = request.GET.get("q", "")
    price_filter = request.GET.get("price_filter", "")
    category_filter = request.GET.get("category_filter", "")

    products = Product.objects.filter(category_id=category_id)

    if query:
        products = products.filter(name__icontains=query)

    if price_filter == "low":
        products = products.filter(price__lt=100)
    elif price_filter == "medium":
        products = products.filter(price__gte=100, price__lte=500)
    elif price_filter == "high":
        products = products.filter(price__gt=500)

    if category_filter:
        products = products.filter(category_id=category_filter)

    return render(request, "shop/product_list.html", {"products": products})


@login_required
def supervisor_dashboard(request):
    # الحصول على التاريخ الحالي
    today = datetime.today().date()

    # الحصول على الفلاتر من GET (التاريخ البداية والنهاية والحالة)
    # إذا لم يتم تحديد تاريخ البداية، استخدم تاريخ اليوم
    start_date = request.GET.get("start_date", today)
    end_date = request.GET.get("end_date")
    status_filter = request.GET.get("status_filter")

    # استعلام للطلبات بناءً على الفلاتر
    orders = Order.objects.all()

    if start_date:
        orders = orders.filter(date__gte=start_date)
    if end_date:
        orders = orders.filter(date__lte=end_date)

    # تصفية الطلبات حسب الحالة المحددة
    if status_filter:
        orders = orders.filter(status=status_filter)

    # إحصائيات
    new_orders_count = orders.count()
    completed_orders_count = orders.filter(status="completed").count()
    total_sales = orders.aggregate(Sum("total_amount"))["total_amount__sum"] or 0

    # إرسال البيانات إلى القالب
    context = {
        "orders": orders,
        "new_orders_count": new_orders_count,
        "completed_orders_count": completed_orders_count,
        "total_sales": total_sales,
        "start_date": start_date,
        "end_date": end_date,
        "status_filter": status_filter,
        "today": today,  # إضافة التاريخ الحالي ليتم تحديده في القالب تلقائيًا
    }

    return render(request, "shop/supervisor_dashboard.html", context)


@login_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        new_status = request.POST.get("status")
        order.status = new_status or Order.PENDING
        order.save()
        return redirect("supervisor_dashboard")

    return render(request, "shop/update_order.html", {"order": order})


# الوظائف الأخرى...


def product_management(request):
    categories = Category.objects.all()
    products = Product.objects.all()

    # تصفية حسب الفئة
    category_id = request.GET.get("category")
    if category_id:
        products = products.filter(category_id=category_id)

    # تصفية حسب الاسم
    search_query = request.GET.get("search")
    if search_query:
        products = products.filter(name__icontains=search_query)

    return render(
        request,
        "shop/product_management.html",
        {
            "products": products,
            "categories": categories,
            "selected_category": category_id,
            "search_query": search_query,
        },
    )


# إضافة منتج جديد


def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("product_management")
    else:
        form = ProductForm()
    return render(request, "shop/add_product.html", {"form": form})


# تعديل منتج موجود


def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect("product_management")
    else:
        form = ProductForm(instance=product)
    return render(request, "shop/edit_product.html", {"form": form, "product": product})


# حذف منتج


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect("product_management")


def mark_notification_as_read(request, notification_id):
    # جلب الإشعار باستخدام المعرف
    notification = get_object_or_404(Notification, id=notification_id)

    # تحديث حالة الإشعار إلى "تمت القراءة"
    notification.is_read = True
    notification.save()

    # إعادة التوجيه إلى قائمة الإشعارات
    return redirect("notifications_list")


def notifications_list(request):
    # جلب الإشعارات الخاصة بالمستخدم الحالي
    notifications = Notification.objects.filter(user=request.user)

    return render(
        request, "shop/notifications_list.html", {"notifications": notifications}
    )


@login_required
def manage_inventory(request):
    products = Product.objects.all()  # جلب جميع المنتجات

    # إذا كانت الطريقة POST
    if request.method == "POST":
        form = UpdateStockForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data["product"]
            quantity = form.cleaned_data["quantity"]

            # تحديث المخزون
            product.stock += quantity
            product.save()  # حفظ التغييرات في قاعدة البيانات

            # عرض رسالة نجاح
            messages.success(request, f"تم تحديث المخزون بنجاح للمنتج: {product.name}")
            return redirect("manage_inventory")  # إعادة التوجيه إلى نفس الصفحة
        else:
            messages.error(request, "هناك خطأ في النموذج, يرجى المحاولة مرة أخرى.")
    else:
        form = UpdateStockForm()  # إذا كانت الطريقة GET، نعرض النموذج الفارغ

    return render(
        request, "shop/manage_inventory.html", {"form": form, "products": products}
    )


def complete_order(request, order_id):
    """تحديث حالة الطلب إلى مكتمل وتقليل المخزون بشكل آمن"""

    # الحصول على الطلب باستخدام order_id
    order = get_object_or_404(Order, id=order_id)

    # سجل حالة الطلب الحالية
    logger.info(f"الطلب رقم {order.id} - الحالة الحالية: {order.status}")

    # التأكد من أن الطلب ليس مكتملًا بالفعل
    if order.status == Order.COMPLETED:
        messages.warning(request, "الطلب قد تم إتمامه مسبقًا.")
        logger.info(f"الطلب رقم {order.id} تم إتمامه مسبقًا.")
        # توجه إلى صفحة لوحة المشرف أو الصفحة المناسبة لك
        return redirect("supervisor_dashboard")

    try:
        # استخدام transaction.atomic لضمان أن العملية تتم ككل أو لا شيء
        with transaction.atomic():
            # تحديث حالة الطلب إلى مكتمل
            order.status = Order.COMPLETED
            order.save()
            logger.info(f"تم تحديث حالة الطلب رقم {order.id} إلى مكتمل.")

            # تقليل المخزون بناءً على العناصر الموجودة في الطلب
            for item in order.items.all():
                product = item.product
                logger.info(
                    f"المنتج: {product.name} - الكمية المطلوبة: {item.quantity} - المخزون الحالي: {product.stock}"
                )

                # التأكد من أن المخزون يكفي للكمية المطلوبة
                if product.stock >= item.quantity:
                    # تقليل المخزون باستخدام طريقة reduce_stock
                    product.reduce_stock(item.quantity)
                else:
                    # إذا كانت الكمية المطلوبة أكبر من المخزون المتاح
                    logger.error(
                        f"لا يوجد كمية كافية من {product.name}. المخزون المتاح: {product.stock}, الكمية المطلوبة: {item.quantity}"
                    )
                    messages.error(
                        request, f"لا يوجد كمية كافية من {product.name} لتلبية الطلب."
                    )
                    # توجه إلى لوحة المشرف في حالة عدم كفاية المخزون
                    return redirect("supervisor_dashboard")

            # بعد إتمام العملية بنجاح
            messages.success(request, "تم إتمام الطلب بنجاح وتم تقليل المخزون.")
            # توجه إلى لوحة المشرف بعد إتمام العملية
            return redirect("supervisor_dashboard")

    except Exception as e:
        # في حالة حدوث أي خطأ غير متوقع
        logger.error(f"حدث خطأ أثناء إتمام الطلب رقم {order.id}: {e}")
        messages.error(request, "حدث خطأ أثناء إتمام الطلب. يرجى المحاولة مرة أخرى.")
        # توجيه المستخدم إلى لوحة المشرف
        return redirect("supervisor_dashboard")


def reduce_stock(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # تحديد الكمية التي سيتم تقليلها من المخزون
    quantity_to_deduct = 1  # أو أي عدد آخر حسب الحاجة

    # التأكد من أن المخزون كافٍ
    if product.stock >= quantity_to_deduct:
        product.stock -= quantity_to_deduct  # تقليل المخزون
        product.save()  # حفظ التغيير في المخزون
        print(
            f"تم تقليل المخزون للمنتج {product.name} بمقدار {quantity_to_deduct}. المخزون الحالي: {product.stock}"
        )
        return redirect("product_management")  # العودة إلى صفحة إدارة المنتجات
    else:
        # في حال المخزون غير كافٍ
        return HttpResponse("المخزون غير كافٍ لتقليله.")


@login_required
def add_delivery_person(request):
    if request.method == "POST":
        form = DeliveryPersonForm(request.POST)
        if form.is_valid():
            # حفظ الموزع الجديد، إنشاء الحساب وربطه بالموصل
            delivery_person = form.save()
            # العودة إلى لوحة تحكم المشرف
            return redirect("supervisor_dashboard")
    else:
        form = DeliveryPersonForm()

    return render(request, "shop/add_delivery_person.html", {"form": form})


def delivery_person_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        # محاولة التحقق من اسم المستخدم وكلمة المرور
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # صفحة لوحة تحكم الموصّل
            return redirect("delivery_person_dashboard")
        else:
            return render(
                request,
                "shop/delivery_person_login.html",
                {"error": "اسم المستخدم أو كلمة المرور غير صحيحة"},
            )

    return render(request, "shop/delivery_person_login.html")


@login_required
def delivery_person_dashboard(request):
    # الحصول على الموصل الحالي
    delivery_person = get_object_or_404(DeliveryPerson, user=request.user)

    # التحقق من وجود طلب مرتبط بالموصل
    order = None
    if delivery_person.order:
        order = delivery_person.order  # الحصول على الطلب المرتبط بالموزع

    return render(
        request,
        "shop/delivery_person_dashboard.html",
        {
            "delivery_person": delivery_person,
            "order": order,  # تمرير الطلب إلى القالب
        },
    )


@login_required
def change_status(request):
    if request.method == "POST":
        # الحصول على الموصل الحالي
        delivery_person = DeliveryPerson.objects.get(user=request.user)

        # تغيير الحالة بناءً على القيمة المرسلة
        new_status = request.POST.get("status")

        if new_status:
            delivery_person.status = new_status
            delivery_person.save()

        # إعادة توجيه إلى لوحة التحكم مع الحالة الجديدة
        return redirect("delivery_person_dashboard")

    return redirect("delivery_person_dashboard")


@login_required
def supervisor_delivery_persons(request):
    # جلب جميع الموصلي الطلبات
    delivery_people = DeliveryPerson.objects.all()  # جلب جميع الموصّلين

    return render(
        request, "shop/delivery_persons.html", {"delivery_persons": delivery_people}
    )


required_field = "some_value"


def update_delivery_person_status(request, delivery_person_id):
    try:
        # الحصول على الموصل بناءً على الـ ID
        delivery_person = DeliveryPerson.objects.get(id=delivery_person_id)
    except DeliveryPerson.DoesNotExist:
        return HttpResponse("الموصل غير موجود", status=404)

    if request.method == "POST":
        # الحصول على الحالة الجديدة من الطلب
        # استخدم get() بدلاً من [] لتجنب الأخطاء
        status = request.POST.get("status")

        if status:
            # تحديث الحالة في قاعدة البيانات
            delivery_person.status = status
            delivery_person.save()

        # إعادة التوجيه إلى لوحة تحكم الموصّل بعد التحديث
        # التوجيه إلى صفحة الموصّل
        return redirect("delivery_person_dashboard")

    return HttpResponse("طريقة غير صحيحة", status=400)


def update_delivery_person_order(request):
    today = timezone.now().date()  # الحصول على تاريخ اليوم
    if request.method == "POST":
        # استلام بيانات الموزع و الـ order_id المرسل
        delivery_person_id = request.POST.get("delivery_person_id")
        order_id = request.POST.get(f"order_id_{delivery_person_id}")

        # التحقق إذا كان يوجد موزع بهذا الـ ID
        try:
            delivery_person = DeliveryPerson.objects.get(id=delivery_person_id)

            # تحقق من وجود الـ order_id وإذا كان موجودًا في قاعدة البيانات
            if order_id:
                try:
                    order = Order.objects.get(id=order_id)

                    # ربط الطلب بالموزع
                    delivery_person.order = order
                    delivery_person.save()

                    # إرسال تفاصيل الطلب إلى القالب لعرضها مع التاريخ الحالي
                    return render(
                        request,
                        "shop/supervisor_dashboard.html",
                        {
                            "order": order,
                            "delivery_person": delivery_person,
                            "today": today,  # إضافة اليوم إلى context
                        },
                    )

                except Order.DoesNotExist:
                    return HttpResponse("رقم الطلب غير صحيح", status=400)
            else:
                # إذا كان `order_id` فارغًا، قم بإزالة ربط الطلب بالموزع
                delivery_person.order = None
                delivery_person.save()

            # إعادة توجيه إلى لوحة تحكم المشرف بعد التحديث
            return redirect("supervisor_dashboard")
        except DeliveryPerson.DoesNotExist:
            return HttpResponse("الموزع غير موجود", status=404)
    else:
        # إذا كانت الطريقة غير POST، لا بد من عرض التاريخ في الـ context
        return render(
            request,
            "shop/supervisor_dashboard.html",
            {
                "today": today,  # إضافة اليوم إلى context
            },
        )


@login_required
def change_order_status(request):
    delivery_person = get_object_or_404(DeliveryPerson, user=request.user)

    if request.method == "POST":
        order_status = request.POST.get("order_status")

        # تحديث حالة الطلب إذا كانت جديدة
        if order_status:
            delivery_person.order_status = order_status
            delivery_person.save()

        return redirect("delivery_person_dashboard")

    return redirect("delivery_person_dashboard")


@login_required
def delivery_person_order(request, order_id):
    if request.method == "POST":
        # الحصول على الحالة الجديدة من الطلب
        # جلب الحالة الجديدة من POST
        new_status = request.POST.get("order_status")

        # التحقق من أن الحالة ليست فارغة
        if not new_status:
            return render(
                request,
                "shop/delivery_person_dashboard.html",
                {"error": "يجب تحديد حالة الطلب"},
            )

        # الحصول على الطلب باستخدام order_id
        order = get_object_or_404(Order, id=order_id)

        # تعيين الحالة الجديدة للطلب
        order.status = new_status

        try:
            order.save()  # حفظ التغييرات في قاعدة البيانات
        except IntegrityError as e:
            return render(
                request,
                "shop/delivery_person_dashboard.html",
                {"error": f"خطأ في حفظ الطلب: {e}"},
            )

        # إعادة التوجيه إلى لوحة المشرف بعد التحديث
        return redirect("delivery_person_dashboard")

    return redirect("delivery_person_dashboard")  # في حالة أن الطلب ليس POST


def order_history(request):
    orders = Order.objects.filter(customer=request.user)
    return render(request, "shop/order_history.html", {"orders": orders})


def ticket_history(request):
    # جلب التذاكر الخاصة بالمستخدم الحالي
    tickets = Ticket.objects.filter(user=request.user)
    return render(request, "shop/ticket_history.html", {"tickets": tickets})


def create_ticket(request):
    if request.method == "POST":
        form = TicketForm(request.POST)
        if form.is_valid():
            # إضافة المستخدم تلقائيًا
            form.instance.user = request.user
            form.save()
            # بعد إنشاء التذكرة، يتم إعادة التوجيه إلى صفحة التذاكر
            return redirect("ticket_history")
    else:
        form = TicketForm()

    return render(request, "shop/create_ticket.html", {"form": form})


@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    messages.success(request, "تمت إضافة المنتج إلى المفضلة!")
    return redirect("wishlist_view")


@login_required
def add_to_wishlist(request, product_id):
    """إضافة منتج إلى قائمة المفضلة"""
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user, product=product
    )

    if created:
        messages.success(request, "تمت إضافة المنتج إلى المفضلة!")
    else:
        messages.info(request, "المنتج موجود بالفعل في المفضلة.")

    return redirect("wishlist_view")


@login_required
def wishlist_view(request):
    """عرض المنتجات في قائمة المفضلة"""
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, "shop/wishlist.html", {"wishlist_items": wishlist_items})


@login_required
def remove_from_wishlist(request, product_id):
    """إزالة منتج من المفضلة"""
    wishlist_item = get_object_or_404(
        Wishlist, user=request.user, product_id=product_id
    )
    wishlist_item.delete()
    messages.success(request, "تمت إزالة المنتج من المفضلة!")
    return redirect("wishlist_view")
