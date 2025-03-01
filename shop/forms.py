from django import forms
from django.contrib.auth.models import User

from .models import CustomerProfile, DeliveryPerson, Product, Review, Ticket


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput,
        help_text="يجب أن تكون كلمة المرور 8 أحرف على الأقل.",
    )
    confirm_password = forms.CharField(
        label="تأكيد كلمة المرور",
        widget=forms.PasswordInput,
        help_text="يرجى إدخال نفس كلمة المرور مرة أخرى.",
    )

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("كلمتا المرور غير متطابقتين.")

    def save(self, commit=True):
        user = super().save(commit=False)
        # استخدم set_password هنا
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ["address"]
        widgets = {
            "address": forms.TextInput(attrs={"placeholder": "أدخل عنوانك هنا"}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]  # تأكد من أن التعليق مدرج هنا
        widgets = {
            "rating": forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
        }


class CheckoutForm(forms.Form):
    address = forms.CharField(max_length=255, label="عنوان المنزل")
    phone_number = forms.CharField(max_length=15, label="رقم الهاتف")


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "price",
            "stock",
            "category",
            "discount_percentage",
            "image",
        ]


class UpdateStockForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(), required=True, label="اختر المنتج"
    )
    quantity = forms.IntegerField(min_value=1, required=True, label="الكمية")


# class DeliveryPersonForm(forms.ModelForm):
# username = forms.CharField(max_length=150)  # إضافة حقل username
#  order_id = forms.IntegerField(required=False)  # حقل لإدخال رقم الطلب

# class Meta:
#    model = DeliveryPerson
#    fields = [ 'name', 'phone_number', 'age', 'status', 'order_id']


#  name = forms.CharField(max_length=100)
# phone_number = forms.CharField(max_length=15)
#  age = forms.IntegerField()
#  status = forms.ChoiceField(choices=DeliveryPerson.STATUS_CHOICES)
class DeliveryPersonForm(forms.ModelForm):
    order_id = forms.IntegerField(required=False)  # حقل لإدخال رقم الطلب

    class Meta:
        model = DeliveryPerson
        fields = [
            "name",
            "phone_number",
            "age",
            "status",
            "order_id",
        ]  # الحقول الخاصة بالموصل

    def save(self, commit=True):
        # حفظ بيانات الموصل
        delivery_person = super().save(commit=False)

        # إذا تم تحديد رقم الطلب، ربطه بالموصل
        if self.cleaned_data["order_id"]:
            try:
                order = Order.objects.get(id=self.cleaned_data["order_id"])
                # ربط الطلب بالموصل
                delivery_person.order = order
            except Order.DoesNotExist:
                pass  # أو يمكنك معالجة الحالة إذا كان رقم الطلب غير صحيح

        if commit:
            delivery_person.save()
        return delivery_person  # تأكد من أن return داخل الدالة


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["subject", "description"]
