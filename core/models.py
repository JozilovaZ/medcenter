from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import random
import string


class User(AbstractUser):
    ROLE_CHOICES = (
        ('superuser', 'Superuser'),
        ('doctor', 'Shifokor'),
        ('patient', 'Bemor'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"


class Specialty(models.Model):
    name = models.CharField(max_length=100, verbose_name="Mutaxassislik nomi")

    class Meta:
        verbose_name = "Mutaxassislik"
        verbose_name_plural = "Mutaxassisliklar"

    def __str__(self):
        return self.name


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile', null=True, blank=True)
    full_name = models.CharField(max_length=200, verbose_name="F.I.O")
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, verbose_name="Mutaxassislik")
    phone = models.CharField(max_length=20, verbose_name="Telefon", blank=True)
    room_number = models.CharField(max_length=10, verbose_name="Xona raqami", blank=True)
    work_start = models.TimeField(default="08:00", verbose_name="Ish boshlanishi")
    work_end = models.TimeField(default="18:00", verbose_name="Ish tugashi")
    avg_appointment_minutes = models.PositiveIntegerField(default=15, verbose_name="O'rtacha qabul vaqti (daqiqa)")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")
    rating = models.FloatField(default=5.0, verbose_name="Reyting")
    total_ratings = models.PositiveIntegerField(default=0)
    photo = models.ImageField(upload_to='doctors/', blank=True, null=True)

    class Meta:
        verbose_name = "Shifokor"
        verbose_name_plural = "Shifokorlar"

    def __str__(self):
        return f"Dr. {self.full_name} - {self.specialty}"

    def today_appointments_count(self):
        return self.appointments.filter(date=timezone.now().date()).count()

    def is_available_now(self):
        now = timezone.localtime().time()
        if not (self.work_start <= now <= self.work_end):
            return False
        current_count = self.appointments.filter(
            date=timezone.now().date(),
            status__in=['waiting', 'in_progress']
        ).count()
        max_per_day = (
            (self.work_end.hour * 60 + self.work_end.minute) -
            (self.work_start.hour * 60 + self.work_start.minute)
        ) // self.avg_appointment_minutes
        return current_count < max_per_day


class Patient(models.Model):
    GENDER_CHOICES = (
        ('male', 'Erkak'),
        ('female', 'Ayol'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile', null=True, blank=True)
    full_name = models.CharField(max_length=200, verbose_name="F.I.O")
    phone = models.CharField(max_length=20, verbose_name="Telefon raqami", db_index=True)
    birth_date = models.DateField(verbose_name="Tug'ilgan sana", null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male', verbose_name="Jinsi")
    address = models.TextField(verbose_name="Manzil", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    no_show_count = models.PositiveIntegerField(default=0, verbose_name="Kelmagan safarlari")
    total_visits = models.PositiveIntegerField(default=0, verbose_name="Jami tashriflar")
    notes = models.TextField(blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Bemor"
        verbose_name_plural = "Bemorlar"

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

    def age(self):
        if self.birth_date:
            today = timezone.now().date()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kategoriya nomi")

    class Meta:
        verbose_name = "Xizmat kategoriyasi"
        verbose_name_plural = "Xizmat kategoriyalari"

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=200, verbose_name="Xizmat nomi")
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kategoriya")
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, related_name='services', verbose_name="Yo'nalish")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Narxi (so'm)")
    duration_minutes = models.PositiveIntegerField(default=15, verbose_name="Davomiyligi (daqiqa)")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Xizmat"
        verbose_name_plural = "Xizmatlar"

    def __str__(self):
        return f"{self.name} - {self.price:,.0f} so'm"


class ServicePackage(models.Model):
    name = models.CharField(max_length=200, verbose_name="Paket nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    services = models.ManyToManyField(Service, verbose_name="Xizmatlar")
    discount_percent = models.PositiveIntegerField(default=0, verbose_name="Chegirma (%)")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Xizmat paketi"
        verbose_name_plural = "Xizmat paketlari"

    def __str__(self):
        return self.name

    def total_price(self):
        total = sum(s.price for s in self.services.all())
        return total * (100 - self.discount_percent) / 100

    def original_price(self):
        return sum(s.price for s in self.services.all())


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Rejalashtirilgan'),
        ('waiting', 'Kutmoqda'),
        ('in_progress', 'Qabulda'),
        ('completed', 'Yakunlangan'),
        ('cancelled', 'Bekor qilingan'),
        ('no_show', 'Kelmadi'),
    )
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments', verbose_name="Bemor")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments', verbose_name="Shifokor")
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, verbose_name="Xizmat")
    date = models.DateField(verbose_name="Sana")
    time = models.TimeField(verbose_name="Vaqt")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name="Holat")
    notes = models.TextField(blank=True, verbose_name="Izoh")
    diagnosis = models.TextField(blank=True, verbose_name="Tashxis")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Qabul"
        verbose_name_plural = "Qabullar"
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.patient} -> Dr.{self.doctor.full_name} ({self.date} {self.time})"


class Queue(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'Kutmoqda'),
        ('called', 'Chaqirilgan'),
        ('in_progress', 'Qabulda'),
        ('completed', 'Yakunlangan'),
        ('skipped', "O'tkazib yuborilgan"),
    )
    ticket_number = models.CharField(max_length=10, verbose_name="Navbat raqami")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, verbose_name="Bemor")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name="Shifokor")
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting', verbose_name="Holat")
    priority = models.PositiveIntegerField(default=0, verbose_name="Ustuvorlik")
    estimated_time = models.TimeField(null=True, blank=True, verbose_name="Taxminiy vaqt")
    created_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Navbat"
        verbose_name_plural = "Navbatlar"
        ordering = ['-priority', 'created_at']

    def __str__(self):
        return f"{self.ticket_number} - {self.patient.full_name}"

    @staticmethod
    def generate_ticket():
        prefix = random.choice(string.ascii_uppercase)
        number = random.randint(10, 99)
        return f"{prefix}{number}"

    def position_in_queue(self):
        return Queue.objects.filter(
            doctor=self.doctor,
            status='waiting',
            created_at__lt=self.created_at,
            created_at__date=timezone.now().date()
        ).count() + 1

    def people_ahead(self):
        return self.position_in_queue() - 1


class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', "To'lanmagan"),
        ('paid', "To'langan"),
        ('partial', "Qisman to'langan"),
        ('refunded', "Qaytarilgan"),
    )
    METHOD_CHOICES = (
        ('cash', 'Naqd'),
        ('card', 'Karta'),
        ('transfer', "O'tkazma"),
    )
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='payments', verbose_name="Bemor")
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Qabul")
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, verbose_name="Xizmat")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Summa")
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="To'langan summa")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holat")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='cash', verbose_name="To'lov usuli")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Chek raqami")

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"

    def __str__(self):
        return f"{self.patient} - {self.amount} so'm ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"R{timezone.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    @property
    def remaining(self):
        return self.amount - self.paid_amount


class MedicalRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records', verbose_name="Bemor")
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True)
    diagnosis = models.TextField(verbose_name="Tashxis")
    prescription = models.TextField(blank=True, verbose_name="Retsept")
    notes = models.TextField(blank=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tibbiy yozuv"
        verbose_name_plural = "Tibbiy yozuvlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient} - {self.diagnosis[:50]}"


class ChatRoom(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='chat_rooms')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chat xona"
        verbose_name_plural = "Chat xonalar"
        unique_together = ['patient', 'doctor']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.patient.full_name} <-> Dr. {self.doctor.full_name}"

    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(verbose_name="Xabar")
    is_prescription = models.BooleanField(default=False, verbose_name="Retsept")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Xabar"
        verbose_name_plural = "Xabarlar"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender} -> {self.text[:30]}"
