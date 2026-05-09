from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Specialty, Doctor, Patient, ServiceCategory,
    Service, ServicePackage, Appointment, Queue, Payment, MedicalRecord
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'role', 'phone')
    list_filter = ('role',)
    fieldsets = UserAdmin.fieldsets + (
        ('Qo\'shimcha', {'fields': ('role', 'phone')}),
    )


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'specialty', 'room_number', 'is_active', 'rating')
    list_filter = ('specialty', 'is_active')
    search_fields = ('full_name',)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'gender', 'total_visits', 'created_at')
    search_fields = ('full_name', 'phone')
    list_filter = ('gender',)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'category', 'price', 'duration_minutes', 'is_active')
    list_filter = ('specialty', 'category', 'is_active')


@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_percent', 'is_active')
    filter_horizontal = ('services',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'service', 'date', 'time', 'status')
    list_filter = ('status', 'date', 'doctor')
    search_fields = ('patient__full_name',)
    date_hierarchy = 'date'


@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'patient', 'doctor', 'status', 'created_at')
    list_filter = ('status', 'doctor')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'amount', 'paid_amount', 'status', 'method', 'created_at')
    list_filter = ('status', 'method')
    search_fields = ('patient__full_name', 'receipt_number')


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'diagnosis', 'created_at')
    search_fields = ('patient__full_name', 'diagnosis')
