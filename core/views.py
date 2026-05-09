from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Patient, Doctor, Appointment, Queue, Payment,
    Service, ServicePackage, Specialty, MedicalRecord,
    ChatRoom, ChatMessage
)
from .forms import (
    LoginForm, RegisterForm, PatientForm, DoctorForm, AppointmentForm,
    QuickAppointmentForm, PaymentForm
)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']
            gender = form.cleaned_data['gender']

            from .models import User, Patient, Doctor
            base_username = first_name.lower()
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
            )

            if role == 'patient':
                Patient.objects.create(
                    user=user,
                    full_name=f"{first_name} {last_name}",
                    phone=phone,
                    gender=gender,
                )
            elif role == 'doctor':
                specialty = form.cleaned_data['specialty']
                Doctor.objects.create(
                    user=user,
                    full_name=f"{first_name} {last_name}",
                    phone=phone,
                    specialty=specialty,
                )

            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    if request.user.role == 'doctor':
        return redirect('doctor_dashboard')
    elif request.user.role == 'patient':
        return redirect('patient_dashboard')

    today = timezone.now().date()
    today_appointments = Appointment.objects.filter(date=today)
    today_payments = Payment.objects.filter(created_at__date=today)

    context = {
        'today_patients': today_appointments.values('patient').distinct().count(),
        'today_appointments': today_appointments.count(),
        'waiting_count': Queue.objects.filter(status='waiting', created_at__date=today).count(),
        'today_revenue': today_payments.filter(status='paid').aggregate(total=Sum('paid_amount'))['total'] or 0,
        'unpaid_count': today_payments.filter(status='pending').count(),
        'recent_appointments': today_appointments.select_related('patient', 'doctor', 'service')[:10],
        'active_queue': Queue.objects.filter(
            status__in=['waiting', 'called'],
            created_at__date=today
        ).select_related('patient', 'doctor')[:10],
        'doctors': Doctor.objects.filter(is_active=True).select_related('specialty'),
        'top_services': Service.objects.annotate(
            usage=Count('appointment')
        ).order_by('-usage')[:5],
        'weekly_stats': get_weekly_stats(),
        'peak_hours': get_peak_hours(),
    }
    return render(request, 'core/dashboard.html', context)


def get_weekly_stats():
    today = timezone.now().date()
    stats = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Appointment.objects.filter(date=day).count()
        revenue = Payment.objects.filter(
            created_at__date=day, status='paid'
        ).aggregate(total=Sum('paid_amount'))['total'] or 0
        stats.append({
            'day': day.strftime('%a'),
            'date': day.strftime('%d.%m'),
            'count': count,
            'revenue': int(revenue),
        })
    return stats


def get_peak_hours():
    hours = {}
    appointments = Appointment.objects.filter(
        date__gte=timezone.now().date() - timedelta(days=30)
    )
    for apt in appointments:
        h = apt.time.hour
        hours[h] = hours.get(h, 0) + 1
    sorted_hours = sorted(hours.items(), key=lambda x: -x[1])[:5]
    return [{'hour': f"{h}:00", 'count': c} for h, c in sorted_hours]


# ==================== PATIENTS ====================

@login_required
def patient_list(request):
    query = request.GET.get('q', '')
    patients = Patient.objects.all().order_by('-created_at')
    if query:
        patients = patients.filter(
            Q(full_name__icontains=query) | Q(phone__icontains=query)
        )
    return render(request, 'core/patient_list.html', {'patients': patients, 'query': query})


@login_required
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f"Bemor {patient.full_name} qo'shildi!")
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = PatientForm()
    return render(request, 'core/patient_form.html', {'form': form, 'title': "Yangi bemor"})


@login_required
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "Bemor ma'lumotlari yangilandi!")
            return redirect('patient_detail', pk=pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'core/patient_form.html', {'form': form, 'title': "Bemorni tahrirlash"})


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    appointments = patient.appointments.select_related('doctor', 'service').order_by('-date', '-time')
    payments = patient.payments.order_by('-created_at')
    records = patient.medical_records.select_related('doctor').order_by('-created_at')
    return render(request, 'core/patient_detail.html', {
        'patient': patient,
        'appointments': appointments,
        'payments': payments,
        'records': records,
    })


@login_required
def patient_search_api(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    patients = Patient.objects.filter(
        Q(full_name__icontains=query) | Q(phone__icontains=query)
    )[:10]
    results = [{'id': p.id, 'name': p.full_name, 'phone': p.phone} for p in patients]
    return JsonResponse({'results': results})


# ==================== DOCTORS ====================

@login_required
def doctor_list(request):
    doctors = Doctor.objects.filter(is_active=True).select_related('specialty')
    return render(request, 'core/doctor_list.html', {'doctors': doctors})


@login_required
def doctor_create(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Shifokor qo'shildi!")
            return redirect('doctor_list')
    else:
        form = DoctorForm()
    return render(request, 'core/doctor_form.html', {'form': form, 'title': "Yangi shifokor"})


@login_required
def doctor_edit(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, "Shifokor ma'lumotlari yangilandi!")
            return redirect('doctor_list')
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'core/doctor_form.html', {'form': form, 'title': "Shifokorni tahrirlash"})


@login_required
def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    today = timezone.now().date()
    today_appointments = doctor.appointments.filter(date=today).select_related('patient', 'service')
    all_appointments = doctor.appointments.select_related('patient', 'service').order_by('-date', '-time')[:20]
    return render(request, 'core/doctor_detail.html', {
        'doctor': doctor,
        'today_appointments': today_appointments,
        'all_appointments': all_appointments,
    })


@login_required
def doctor_schedule_api(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    date_str = request.GET.get('date', timezone.now().date().isoformat())
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    busy_times = doctor.appointments.filter(
        date=date, status__in=['scheduled', 'waiting', 'in_progress']
    ).values_list('time', flat=True)
    busy = [t.strftime('%H:%M') for t in busy_times]
    slots = []
    current = datetime.combine(date, doctor.work_start)
    end = datetime.combine(date, doctor.work_end)
    while current < end:
        t = current.strftime('%H:%M')
        slots.append({'time': t, 'busy': t in busy})
        current += timedelta(minutes=doctor.avg_appointment_minutes)
    return JsonResponse({'slots': slots, 'doctor': doctor.full_name})


# ==================== APPOINTMENTS ====================

@login_required
def appointment_list(request):
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    status_filter = request.GET.get('status', '')
    appointments = Appointment.objects.select_related('patient', 'doctor', 'service')
    try:
        appointments = appointments.filter(date=date_filter)
    except (ValueError, TypeError):
        appointments = appointments.filter(date=timezone.now().date())
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    return render(request, 'core/appointment_list.html', {
        'appointments': appointments,
        'date_filter': date_filter,
        'status_filter': status_filter,
    })


@login_required
def appointment_create(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            apt = form.save(commit=False)
            apt.created_by = request.user
            apt.save()
            messages.success(request, "Qabul yaratildi!")
            return redirect('appointment_list')
    else:
        form = AppointmentForm()
        form.fields['date'].initial = timezone.now().date()
    return render(request, 'core/appointment_form.html', {'form': form, 'title': "Yangi qabul"})


@login_required
def quick_appointment(request):
    if request.method == 'POST':
        form = QuickAppointmentForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            full_name = form.cleaned_data['full_name']
            doctor = form.cleaned_data['doctor']
            service = form.cleaned_data['service']

            patient, created = Patient.objects.get_or_create(
                phone=phone,
                defaults={'full_name': full_name}
            )

            now = timezone.localtime()
            apt = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                service=service,
                date=now.date(),
                time=now.time(),
                status='waiting',
                created_by=request.user,
            )

            queue = Queue.objects.create(
                ticket_number=Queue.generate_ticket(),
                patient=patient,
                doctor=doctor,
                appointment=apt,
                status='waiting',
            )

            if service:
                Payment.objects.create(
                    patient=patient,
                    appointment=apt,
                    service=service,
                    amount=service.price,
                )

            messages.success(request, f"Tez qabul! Navbat: {queue.ticket_number}")
            return redirect('queue_display')
    else:
        form = QuickAppointmentForm()
    specialties = Specialty.objects.filter(doctor__is_active=True).distinct().order_by('name')
    return render(request, 'core/quick_appointment.html', {'form': form, 'specialties': specialties})


@login_required
def appointment_status_update(request, pk, status):
    apt = get_object_or_404(Appointment, pk=pk)
    if status in dict(Appointment.STATUS_CHOICES):
        apt.status = status
        apt.save()
        if status == 'no_show':
            apt.patient.no_show_count += 1
            apt.patient.save()
        elif status == 'completed':
            apt.patient.total_visits += 1
            apt.patient.save()
            # Avtomatik chat xona yaratish
            if apt.doctor and apt.patient:
                ChatRoom.objects.get_or_create(patient=apt.patient, doctor=apt.doctor)
        messages.success(request, f"Qabul holati: {apt.get_status_display()}")
    return redirect(request.META.get('HTTP_REFERER', 'appointment_list'))


# ==================== QUEUE ====================

@login_required
def queue_list(request):
    today = timezone.now().date()
    queues = Queue.objects.filter(
        created_at__date=today
    ).select_related('patient', 'doctor')
    waiting = queues.filter(status='waiting')
    called = queues.filter(status='called')
    in_progress = queues.filter(status='in_progress')
    completed = queues.filter(status='completed')
    return render(request, 'core/queue_list.html', {
        'waiting': waiting,
        'called': called,
        'in_progress': in_progress,
        'completed': completed,
    })


def queue_display(request):
    today = timezone.now().date()
    active = Queue.objects.filter(
        created_at__date=today,
        status__in=['waiting', 'called', 'in_progress']
    ).select_related('patient', 'doctor')
    return render(request, 'core/queue_display.html', {'queues': active})


@login_required
def queue_call_next(request, doctor_id):
    today = timezone.now().date()
    now = timezone.localtime()
    candidates = Queue.objects.filter(
        doctor_id=doctor_id,
        status='waiting',
        created_at__date=today
    )
    next_item = None
    earliest_future = None
    for q in candidates:
        if q.appointment and q.appointment.time:
            apt_dt = timezone.make_aware(datetime.combine(q.appointment.date, q.appointment.time)) \
                if timezone.is_naive(datetime.combine(q.appointment.date, q.appointment.time)) \
                else datetime.combine(q.appointment.date, q.appointment.time)
            if now < apt_dt:
                if earliest_future is None or apt_dt < earliest_future[0]:
                    earliest_future = (apt_dt, q)
                continue
        next_item = q
        break
    if next_item:
        Queue.objects.filter(
            doctor_id=doctor_id, status='called', created_at__date=today
        ).update(status='skipped')
        next_item.status = 'called'
        next_item.called_at = timezone.now()
        next_item.save()
        if next_item.appointment:
            next_item.appointment.status = 'waiting'
            next_item.appointment.save()
        messages.success(request, f"Chaqirildi: {next_item.ticket_number} - {next_item.patient.full_name}")
    elif earliest_future:
        apt_dt, q = earliest_future
        messages.warning(
            request,
            f"Vaqti hali kelmagan! {q.patient.full_name} uchun belgilangan vaqt: {apt_dt.strftime('%H:%M')}. Bemorni o'sha vaqtdan oldin chaqirib bo'lmaydi."
        )
    else:
        messages.info(request, "Navbatda hech kim yo'q!")
    return redirect('queue_list')


@login_required
def queue_status_update(request, pk, status):
    queue = get_object_or_404(Queue, pk=pk)
    if status in ('called', 'in_progress') and queue.appointment and queue.appointment.time:
        apt_dt = datetime.combine(queue.appointment.date, queue.appointment.time)
        if timezone.is_naive(apt_dt):
            apt_dt = timezone.make_aware(apt_dt)
        if timezone.localtime() < apt_dt:
            messages.warning(
                request,
                f"Vaqti hali kelmagan! Bemor uchun belgilangan vaqt: {apt_dt.strftime('%H:%M')}. Vaqtidan oldin chaqirib bo'lmaydi."
            )
            return redirect('queue_list')
    queue.status = status
    if status == 'in_progress' and queue.appointment:
        queue.appointment.status = 'in_progress'
        queue.appointment.save()
    elif status == 'completed':
        queue.completed_at = timezone.now()
        if queue.appointment:
            queue.appointment.status = 'completed'
            queue.appointment.save()
            queue.appointment.patient.total_visits += 1
            queue.appointment.patient.save()
            # Avtomatik chat xona yaratish
            ChatRoom.objects.get_or_create(patient=queue.patient, doctor=queue.doctor)
    queue.save()
    return redirect('queue_list')


@login_required
def queue_add(request, appointment_id):
    apt = get_object_or_404(Appointment, pk=appointment_id)
    if not Queue.objects.filter(appointment=apt).exists():
        Queue.objects.create(
            ticket_number=Queue.generate_ticket(),
            patient=apt.patient,
            doctor=apt.doctor,
            appointment=apt,
        )
        apt.status = 'waiting'
        apt.save()
        messages.success(request, "Navbatga qo'shildi!")
    else:
        messages.warning(request, "Bu qabul allaqachon navbatda!")
    return redirect('queue_list')


@login_required
def queue_monitor_api(request):
    today = timezone.now().date()
    queues = Queue.objects.filter(
        created_at__date=today,
        status__in=['waiting', 'called', 'in_progress']
    ).select_related('patient', 'doctor')
    data = [{
        'ticket': q.ticket_number,
        'patient': q.patient.full_name,
        'doctor': q.doctor.full_name,
        'room': q.doctor.room_number,
        'status': q.status,
        'status_display': q.get_status_display(),
        'position': q.position_in_queue() if q.status == 'waiting' else 0,
    } for q in queues]
    return JsonResponse({'queues': data})


# ==================== PAYMENTS ====================

@login_required
def payment_list(request):
    date_filter = request.GET.get('date', '')
    date_to = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')
    method_filter = request.GET.get('method', '')
    search_query = request.GET.get('q', '')
    payments = Payment.objects.select_related('patient', 'service', 'appointment').order_by('-created_at')
    if date_filter:
        try:
            payments = payments.filter(created_at__date__gte=date_filter)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            payments = payments.filter(created_at__date__lte=date_to)
        except (ValueError, TypeError):
            pass
    if not date_filter and not date_to:
        payments = payments.filter(created_at__date=timezone.now().date())
    if status_filter:
        payments = payments.filter(status=status_filter)
    if method_filter:
        payments = payments.filter(method=method_filter)
    if search_query:
        payments = payments.filter(
            Q(patient__full_name__icontains=search_query) |
            Q(receipt_number__icontains=search_query) |
            Q(service__name__icontains=search_query)
        )
    total = payments.aggregate(
        total_amount=Sum('amount'),
        total_paid=Sum('paid_amount')
    )
    total_amount = total['total_amount'] or 0
    total_paid = total['total_paid'] or 0
    total_debt = total_amount - total_paid
    return render(request, 'core/payment_list.html', {
        'payments': payments,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_debt': total_debt,
        'date_filter': date_filter,
        'date_to': date_to,
        'status_filter': status_filter,
        'method_filter': method_filter,
        'search_query': search_query,
    })


@login_required
def payment_create(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            messages.success(request, f"To'lov yaratildi! Chek: {payment.receipt_number}")
            return redirect('payment_detail', pk=payment.pk)
    else:
        form = PaymentForm()
        patient_id = request.GET.get('patient')
        service_id = request.GET.get('service')
        if patient_id:
            form.fields['patient'].initial = patient_id
        if service_id:
            try:
                service = Service.objects.get(pk=service_id)
                form.fields['service'].initial = service_id
                form.fields['amount'].initial = service.price
            except Service.DoesNotExist:
                pass
    return render(request, 'core/payment_form.html', {'form': form, 'title': "Yangi to'lov"})


@login_required
def payment_detail(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('patient', 'service', 'appointment'), pk=pk)
    return render(request, 'core/payment_detail.html', {'payment': payment})


@login_required
def payment_edit(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if payment.status == 'paid':
        messages.warning(request, "To'langan to'lovni tahrirlash mumkin emas!")
        return redirect('payment_detail', pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, "To'lov yangilandi!")
            return redirect('payment_detail', pk=pk)
    else:
        form = PaymentForm(instance=payment)
    return render(request, 'core/payment_form.html', {'form': form, 'title': "To'lovni tahrirlash", 'payment': payment})


@login_required
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if payment.status == 'paid':
        messages.warning(request, "To'langan to'lovni o'chirish mumkin emas!")
        return redirect('payment_detail', pk=pk)
    if request.method == 'POST':
        receipt = payment.receipt_number
        payment.delete()
        messages.success(request, f"To'lov #{receipt} o'chirildi!")
        return redirect('payment_list')
    return render(request, 'core/payment_confirm_delete.html', {'payment': payment})


@login_required
def payment_mark_paid(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    method = request.POST.get('method', payment.method)
    payment.status = 'paid'
    payment.paid_amount = payment.amount
    payment.method = method
    payment.paid_at = timezone.now()
    payment.save()
    messages.success(request, f"To'lov #{payment.receipt_number} to'landi!")
    return redirect(request.META.get('HTTP_REFERER', 'payment_list'))


@login_required
def payment_partial_pay(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if payment.status == 'paid':
        messages.info(request, "Bu to'lov allaqachon to'langan!")
        return redirect('payment_detail', pk=pk)
    if request.method == 'POST':
        try:
            pay_amount = round(float(request.POST.get('pay_amount', 0)), 2)
        except (ValueError, TypeError):
            pay_amount = 0
        method = request.POST.get('method', payment.method)
        if pay_amount <= 0:
            messages.error(request, "Noto'g'ri summa!")
            return redirect('payment_detail', pk=pk)
        from decimal import Decimal
        pay_amount = Decimal(str(pay_amount))
        remaining = payment.amount - payment.paid_amount
        if pay_amount > remaining:
            pay_amount = remaining
        payment.paid_amount += pay_amount
        payment.method = method
        payment.paid_at = timezone.now()
        if payment.paid_amount >= payment.amount:
            payment.status = 'paid'
            messages.success(request, f"To'lov #{payment.receipt_number} to'liq to'landi!")
        else:
            payment.status = 'partial'
            messages.success(request, f"{pay_amount:,.0f} so'm qabul qilindi. Qoldiq: {payment.remaining:,.0f} so'm")
        payment.save()
        return redirect('payment_detail', pk=pk)
    return redirect('payment_detail', pk=pk)


@login_required
def payment_refund(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if payment.paid_amount == 0:
        messages.warning(request, "Bu to'lovda qaytariladigan summa yo'q!")
        return redirect('payment_detail', pk=pk)
    if request.method == 'POST':
        payment.status = 'refunded'
        payment.save()
        messages.success(request, f"To'lov #{payment.receipt_number} qaytarildi!")
        return redirect('payment_detail', pk=pk)
    return redirect('payment_detail', pk=pk)


@login_required
def payment_receipt(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('patient', 'service', 'appointment'), pk=pk)
    return render(request, 'core/payment_receipt.html', {'payment': payment})


@login_required
def payment_search_api(request):
    q = request.GET.get('q', '')
    if len(q) < 2:
        return JsonResponse({'results': []})
    payments = Payment.objects.select_related('patient', 'service').filter(
        Q(patient__full_name__icontains=q) |
        Q(receipt_number__icontains=q)
    ).order_by('-created_at')[:10]
    results = [{
        'id': p.pk,
        'receipt': p.receipt_number,
        'patient': p.patient.full_name,
        'service': p.service.name if p.service else '-',
        'amount': str(p.amount),
        'paid': str(p.paid_amount),
        'status': p.get_status_display(),
        'status_key': p.status,
    } for p in payments]
    return JsonResponse({'results': results})


# ==================== STATISTICS ====================

@login_required
def statistics(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    monthly_revenue = Payment.objects.filter(
        created_at__date__gte=month_start, status='paid'
    ).aggregate(total=Sum('paid_amount'))['total'] or 0

    top_doctors = Doctor.objects.annotate(
        apt_count=Count('appointments', filter=Q(appointments__date__gte=month_start)),
        revenue=Sum(
            'appointments__payment__paid_amount',
            filter=Q(appointments__payment__status='paid', appointments__date__gte=month_start)
        )
    ).order_by('-apt_count')[:5]

    top_services = Service.objects.annotate(
        usage=Count('appointment', filter=Q(appointment__date__gte=month_start)),
        revenue=Sum(
            'payment__paid_amount',
            filter=Q(payment__status='paid', payment__created_at__date__gte=month_start)
        )
    ).order_by('-usage')[:5]

    daily_stats = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        apts = Appointment.objects.filter(date=day).count()
        rev = Payment.objects.filter(
            created_at__date=day, status='paid'
        ).aggregate(total=Sum('paid_amount'))['total'] or 0
        daily_stats.append({'date': day.strftime('%d.%m'), 'appointments': apts, 'revenue': int(rev)})

    no_show_patients = Patient.objects.filter(no_show_count__gt=0).order_by('-no_show_count')[:10]

    context = {
        'monthly_revenue': monthly_revenue,
        'total_patients': Patient.objects.count(),
        'total_appointments_month': Appointment.objects.filter(date__gte=month_start).count(),
        'top_doctors': top_doctors,
        'top_services': top_services,
        'daily_stats': daily_stats,
        'no_show_patients': no_show_patients,
        'peak_hours': get_peak_hours(),
    }
    return render(request, 'core/statistics.html', context)


# ==================== SERVICES ====================

@login_required
def service_list(request):
    services = Service.objects.filter(is_active=True).select_related('category')
    packages = ServicePackage.objects.filter(is_active=True).prefetch_related('services')
    return render(request, 'core/service_list.html', {'services': services, 'packages': packages})


def services_by_specialty_api(request, specialty_id):
    services = Service.objects.filter(is_active=True, specialty_id=specialty_id).order_by('name')
    data = [{'id': s.pk, 'name': s.name, 'price': str(s.price), 'duration': s.duration_minutes} for s in services]
    return JsonResponse({'services': data})


def doctors_by_specialty_api(request, specialty_id):
    doctors = Doctor.objects.filter(is_active=True, specialty_id=specialty_id).select_related('specialty')
    data = [{
        'id': d.pk,
        'name': d.full_name,
        'room': d.room_number or '-',
        'work_start': d.work_start.strftime('%H:%M'),
        'work_end': d.work_end.strftime('%H:%M'),
        'available': d.is_available_now(),
    } for d in doctors]
    return JsonResponse({'doctors': data})


# ==================== BEMOR (PATIENT ROLE) VIEWS ====================

@login_required
def my_appointments(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.warning(request, "Sizning bemor profilingiz topilmadi!")
        return redirect('dashboard')
    patient = request.user.patient_profile
    appointments = patient.appointments.select_related('doctor', 'service').order_by('-date', '-time')
    return render(request, 'core/my_appointments.html', {'appointments': appointments, 'patient': patient})


@login_required
def my_queue(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.warning(request, "Sizning bemor profilingiz topilmadi!")
        return redirect('dashboard')
    patient = request.user.patient_profile
    today = timezone.now().date()
    queues = Queue.objects.filter(
        patient=patient,
        created_at__date=today
    ).select_related('doctor')
    return render(request, 'core/my_queue.html', {'queues': queues, 'patient': patient})


@login_required
def my_payments(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.warning(request, "Sizning bemor profilingiz topilmadi!")
        return redirect('dashboard')
    patient = request.user.patient_profile
    status_filter = request.GET.get('status', '')
    payments = patient.payments.select_related('service').order_by('-created_at')
    if status_filter:
        payments = payments.filter(status=status_filter)
    total = payments.aggregate(
        total_amount=Sum('amount'),
        total_paid=Sum('paid_amount')
    )
    total_amount = total['total_amount'] or 0
    total_paid = total['total_paid'] or 0
    return render(request, 'core/my_payments.html', {
        'payments': payments,
        'patient': patient,
        'status_filter': status_filter,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_debt': total_amount - total_paid,
    })


@login_required
def my_medical_records(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.warning(request, "Sizning bemor profilingiz topilmadi!")
        return redirect('dashboard')
    patient = request.user.patient_profile
    records = patient.medical_records.select_related('doctor').order_by('-created_at')
    return render(request, 'core/my_medical_records.html', {'records': records, 'patient': patient})


# ==================== DOCTOR DASHBOARD ====================

@login_required
def doctor_dashboard(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.warning(request, "Shifokor profilingiz topilmadi!")
        return redirect('login')
    doctor = request.user.doctor_profile
    today = timezone.now().date()

    today_appointments = doctor.appointments.filter(date=today).select_related('patient', 'service').order_by('time')
    waiting_queue = Queue.objects.filter(
        doctor=doctor, status='waiting', created_at__date=today
    ).select_related('patient').order_by('-priority', 'created_at')
    called_queue = Queue.objects.filter(
        doctor=doctor, status__in=['called', 'in_progress'], created_at__date=today
    ).select_related('patient')
    completed_today = doctor.appointments.filter(date=today, status='completed').count()
    scheduled_count = doctor.appointments.filter(date=today, status='scheduled').count()

    upcoming_appointments = doctor.appointments.filter(
        date__gte=today, status='scheduled'
    ).select_related('patient', 'service').order_by('date', 'time')[:10]

    context = {
        'doctor': doctor,
        'today_appointments': today_appointments,
        'waiting_queue': waiting_queue,
        'called_queue': called_queue,
        'completed_today': completed_today,
        'scheduled_count': scheduled_count,
        'total_today': today_appointments.count(),
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'core/doctor_dashboard.html', context)


@login_required
def doctor_payments(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.warning(request, "Shifokor profilingiz topilmadi!")
        return redirect('login')
    doctor = request.user.doctor_profile
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    search_query = request.GET.get('q', '')
    payments = Payment.objects.filter(
        appointment__doctor=doctor
    ).select_related('patient', 'service', 'appointment').order_by('-created_at')
    if date_filter:
        try:
            payments = payments.filter(created_at__date=date_filter)
        except (ValueError, TypeError):
            pass
    if status_filter:
        payments = payments.filter(status=status_filter)
    if search_query:
        payments = payments.filter(
            Q(patient__full_name__icontains=search_query) |
            Q(patient__phone__icontains=search_query) |
            Q(receipt_number__icontains=search_query)
        )
    total = payments.aggregate(
        total_amount=Sum('amount'),
        total_paid=Sum('paid_amount')
    )
    total_amount = total['total_amount'] or 0
    total_paid = total['total_paid'] or 0
    return render(request, 'core/doctor_payments.html', {
        'payments': payments,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_debt': total_amount - total_paid,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'search_query': search_query,
    })


@login_required
def doctor_my_appointments(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.warning(request, "Shifokor profilingiz topilmadi!")
        return redirect('login')
    doctor = request.user.doctor_profile
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    status_filter = request.GET.get('status', '')

    appointments = doctor.appointments.select_related('patient', 'service')
    try:
        appointments = appointments.filter(date=date_filter)
    except (ValueError, TypeError):
        appointments = appointments.filter(date=timezone.now().date())
    if status_filter:
        appointments = appointments.filter(status=status_filter)

    appointments = appointments.order_by('time')
    return render(request, 'core/doctor_my_appointments.html', {
        'appointments': appointments,
        'doctor': doctor,
        'date_filter': date_filter,
        'status_filter': status_filter,
    })


@login_required
def doctor_update_schedule(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.warning(request, "Shifokor profilingiz topilmadi!")
        return redirect('login')
    doctor = request.user.doctor_profile
    if request.method == 'POST':
        work_start = request.POST.get('work_start')
        work_end = request.POST.get('work_end')
        avg_minutes = request.POST.get('avg_appointment_minutes')
        room_number = request.POST.get('room_number')
        if work_start:
            doctor.work_start = work_start
        if work_end:
            doctor.work_end = work_end
        if avg_minutes:
            doctor.avg_appointment_minutes = int(avg_minutes)
        if room_number:
            doctor.room_number = room_number
        doctor.save()
        messages.success(request, "Ish vaqtlari yangilandi!")
    return redirect('doctor_dashboard')


@login_required
def doctor_approve_appointment(request, pk):
    if not hasattr(request.user, 'doctor_profile'):
        return redirect('login')
    apt = get_object_or_404(Appointment, pk=pk, doctor=request.user.doctor_profile)
    if apt.status == 'scheduled':
        apt.status = 'waiting'
        apt.save()
        if not Queue.objects.filter(appointment=apt).exists():
            Queue.objects.create(
                ticket_number=Queue.generate_ticket(),
                patient=apt.patient,
                doctor=apt.doctor,
                appointment=apt,
            )
        messages.success(request, f"{apt.patient.full_name} tasdiqlandi!")
    return redirect('doctor_dashboard')


@login_required
def doctor_reject_appointment(request, pk):
    if not hasattr(request.user, 'doctor_profile'):
        return redirect('login')
    apt = get_object_or_404(Appointment, pk=pk, doctor=request.user.doctor_profile)
    if apt.status == 'scheduled':
        apt.status = 'cancelled'
        apt.save()
        messages.success(request, f"{apt.patient.full_name} qabuli bekor qilindi!")
    return redirect('doctor_dashboard')


@login_required
def doctor_write_record(request, appointment_id):
    if not hasattr(request.user, 'doctor_profile'):
        return redirect('login')
    doctor = request.user.doctor_profile
    apt = get_object_or_404(Appointment, pk=appointment_id, doctor=doctor)
    if request.method == 'POST':
        diagnosis = request.POST.get('diagnosis', '')
        prescription = request.POST.get('prescription', '')
        notes = request.POST.get('notes', '')
        if diagnosis:
            MedicalRecord.objects.create(
                patient=apt.patient,
                appointment=apt,
                doctor=doctor,
                diagnosis=diagnosis,
                prescription=prescription,
                notes=notes,
            )
            apt.diagnosis = diagnosis
            apt.save()
            messages.success(request, "Tibbiy yozuv saqlandi!")
        else:
            messages.warning(request, "Tashxis kiritish shart!")
    return redirect('doctor_dashboard')


# ==================== PATIENT DASHBOARD ====================

@login_required
def patient_dashboard(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.warning(request, "Bemor profilingiz topilmadi!")
        return redirect('login')
    patient = request.user.patient_profile
    today = timezone.now().date()
    now = timezone.localtime()

    doctors = Doctor.objects.filter(is_active=True).select_related('specialty')

    my_upcoming = patient.appointments.filter(
        date__gte=today, status__in=['scheduled', 'waiting']
    ).select_related('doctor', 'service').order_by('date', 'time')

    my_queue = Queue.objects.filter(
        patient=patient, created_at__date=today, status__in=['waiting', 'called', 'in_progress']
    ).select_related('doctor')

    my_recent = patient.appointments.filter(
        status='completed'
    ).select_related('doctor', 'service').order_by('-date', '-time')[:5]

    upcoming_with_countdown = []
    for apt in my_upcoming:
        apt_datetime = timezone.make_aware(
            datetime.combine(apt.date, apt.time),
            timezone.get_current_timezone()
        )
        diff = apt_datetime - now
        total_seconds = int(diff.total_seconds())
        if total_seconds > 0:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            if days > 0:
                countdown_text = f"{days} kun {hours} soat {minutes} daqiqa"
            elif hours > 0:
                countdown_text = f"{hours} soat {minutes} daqiqa"
            else:
                countdown_text = f"{minutes} daqiqa"
        else:
            countdown_text = "Vaqti keldi!"
        upcoming_with_countdown.append({
            'appointment': apt,
            'countdown_text': countdown_text,
            'total_seconds': max(total_seconds, 0),
            'apt_datetime_iso': apt_datetime.isoformat(),
        })

    context = {
        'patient': patient,
        'doctors': doctors,
        'upcoming': upcoming_with_countdown,
        'my_queue': my_queue,
        'my_recent': my_recent,
    }
    return render(request, 'core/patient_dashboard.html', context)


# ==================== PROFILE ====================

@login_required
def profile_view(request):
    user = request.user
    today = timezone.now().date()
    month_start = today.replace(day=1)

    context = {
        'profile_user': user,
        'member_since': user.date_joined,
        'last_login': user.last_login,
    }

    if user.role == 'doctor' and hasattr(user, 'doctor_profile'):
        doctor = user.doctor_profile
        total_appointments = doctor.appointments.count()
        completed_appointments = doctor.appointments.filter(status='completed').count()
        month_appointments = doctor.appointments.filter(date__gte=month_start).count()
        total_patients = doctor.appointments.values('patient').distinct().count()
        total_revenue = Payment.objects.filter(
            appointment__doctor=doctor, status='paid'
        ).aggregate(total=Sum('paid_amount'))['total'] or 0
        month_revenue = Payment.objects.filter(
            appointment__doctor=doctor, status='paid',
            created_at__date__gte=month_start
        ).aggregate(total=Sum('paid_amount'))['total'] or 0
        recent_appointments = doctor.appointments.select_related(
            'patient', 'service'
        ).order_by('-date', '-time')[:10]

        context.update({
            'doctor': doctor,
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'month_appointments': month_appointments,
            'total_patients': total_patients,
            'total_revenue': total_revenue,
            'month_revenue': month_revenue,
            'recent_appointments': recent_appointments,
        })

    elif user.role == 'patient' and hasattr(user, 'patient_profile'):
        patient = user.patient_profile
        total_appointments = patient.appointments.count()
        completed_appointments = patient.appointments.filter(status='completed').count()
        total_paid = patient.payments.filter(status='paid').aggregate(
            total=Sum('paid_amount'))['total'] or 0
        pending_payments = patient.payments.filter(status='pending').aggregate(
            total=Sum('amount'))['total'] or 0
        recent_appointments = patient.appointments.select_related(
            'doctor', 'service'
        ).order_by('-date', '-time')[:10]
        recent_records = patient.medical_records.select_related('doctor').order_by('-created_at')[:5]

        context.update({
            'patient': patient,
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'total_paid': total_paid,
            'pending_payments': pending_payments,
            'recent_appointments': recent_appointments,
            'recent_records': recent_records,
        })

    elif user.role == 'superuser':
        context.update({
            'total_patients': Patient.objects.count(),
            'total_doctors': Doctor.objects.filter(is_active=True).count(),
            'total_appointments': Appointment.objects.count(),
            'month_appointments': Appointment.objects.filter(date__gte=month_start).count(),
            'total_revenue': Payment.objects.filter(status='paid').aggregate(
                total=Sum('paid_amount'))['total'] or 0,
            'month_revenue': Payment.objects.filter(
                status='paid', created_at__date__gte=month_start
            ).aggregate(total=Sum('paid_amount'))['total'] or 0,
        })

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()

        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if phone:
            user.phone = phone

        user.save()

        if hasattr(user, 'doctor_profile'):
            doctor = user.doctor_profile
            doctor.full_name = f"{user.first_name} {user.last_name}"
            doctor.phone = phone
            doctor.save()
        elif hasattr(user, 'patient_profile'):
            patient = user.patient_profile
            patient.full_name = f"{user.first_name} {user.last_name}"
            patient.phone = phone
            gender = request.POST.get('gender', '').strip()
            birth_date = request.POST.get('birth_date', '').strip()
            address = request.POST.get('address', '').strip()
            if gender in ('male', 'female'):
                patient.gender = gender
            if birth_date:
                try:
                    patient.birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
                except ValueError:
                    pass
            patient.address = address
            patient.save()

        messages.success(request, "Profil muvaffaqiyatli yangilandi!")
        return redirect('profile')

    return render(request, 'core/profile.html', context)


@login_required
def patient_book_appointment(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.warning(request, "Bemor profilingiz topilmadi!")
        return redirect('login')
    patient = request.user.patient_profile

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        service_id = request.POST.get('service')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')

        doctor = get_object_or_404(Doctor, pk=doctor_id, is_active=True)
        service = None
        if service_id:
            service = get_object_or_404(Service, pk=service_id, is_active=True)

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_val = datetime.strptime(time_str, '%H:%M').time()
        except (ValueError, TypeError):
            messages.error(request, "Noto'g'ri sana yoki vaqt!")
            return redirect('patient_book')

        if date < timezone.now().date():
            messages.error(request, "O'tgan sanaga yozilish mumkin emas!")
            return redirect('patient_book')

        existing = Appointment.objects.filter(
            doctor=doctor, date=date, time=time_val,
            status__in=['scheduled', 'waiting', 'in_progress']
        ).exists()
        if existing:
            messages.error(request, "Bu vaqt band! Boshqa vaqt tanlang.")
            return redirect('patient_book')

        apt = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            service=service,
            date=date,
            time=time_val,
            status='scheduled',
            created_by=request.user,
        )

        if service:
            Payment.objects.create(
                patient=patient,
                appointment=apt,
                service=service,
                amount=service.price,
            )

        messages.success(request, f"Dr. {doctor.full_name}ga {date} kuni soat {time_str}ga yozildingiz!")
        return redirect('patient_dashboard')

    doctors = Doctor.objects.filter(is_active=True).select_related('specialty')
    services = Service.objects.filter(is_active=True)
    specialties = Specialty.objects.filter(doctor__is_active=True).distinct().order_by('name')
    return render(request, 'core/patient_book.html', {
        'doctors': doctors,
        'services': services,
        'specialties': specialties,
        'min_date': timezone.now().date().isoformat(),
    })


# ==================== CHAT ====================

@login_required
def chat_list(request):
    user = request.user
    if user.role == 'doctor' and hasattr(user, 'doctor_profile'):
        rooms = ChatRoom.objects.filter(doctor=user.doctor_profile).select_related('patient', 'doctor')
    elif user.role == 'patient' and hasattr(user, 'patient_profile'):
        rooms = ChatRoom.objects.filter(patient=user.patient_profile).select_related('patient', 'doctor')
    elif user.role == 'superuser':
        rooms = ChatRoom.objects.all().select_related('patient', 'doctor')
    else:
        rooms = ChatRoom.objects.none()

    room_data = []
    for room in rooms:
        last_msg = room.last_message()
        unread = room.unread_count(user)
        room_data.append({
            'room': room,
            'last_message': last_msg,
            'unread': unread,
        })

    return render(request, 'core/chat_list.html', {'room_data': room_data})


@login_required
def chat_room(request, room_id):
    user = request.user
    room = get_object_or_404(ChatRoom, pk=room_id)

    # check access
    if user.role == 'doctor' and hasattr(user, 'doctor_profile'):
        if room.doctor != user.doctor_profile:
            return redirect('chat_list')
    elif user.role == 'patient' and hasattr(user, 'patient_profile'):
        if room.patient != user.patient_profile:
            return redirect('chat_list')

    # mark messages as read
    room.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        is_prescription = request.POST.get('is_prescription') == 'on'
        if text:
            ChatMessage.objects.create(
                room=room,
                sender=user,
                text=text,
                is_prescription=is_prescription,
            )
            room.save()  # update updated_at
            return redirect('chat_room', room_id=room.pk)

    chat_messages = room.messages.select_related('sender').order_by('created_at')
    return render(request, 'core/chat_room.html', {
        'room': room,
        'chat_messages': chat_messages,
    })


@login_required
def chat_start(request, doctor_id):
    """Bemor shifokor bilan yangi chat boshlaydi"""
    if not hasattr(request.user, 'patient_profile'):
        messages.warning(request, "Faqat bemorlar chat boshlashi mumkin!")
        return redirect('dashboard')
    patient = request.user.patient_profile
    doctor = get_object_or_404(Doctor, pk=doctor_id, is_active=True)
    room, created = ChatRoom.objects.get_or_create(patient=patient, doctor=doctor)
    return redirect('chat_room', room_id=room.pk)


@login_required
def chat_start_with_patient(request, patient_id):
    """Shifokor bemor bilan yangi chat boshlaydi"""
    if not hasattr(request.user, 'doctor_profile'):
        messages.warning(request, "Faqat shifokorlar chat boshlashi mumkin!")
        return redirect('dashboard')
    doctor = request.user.doctor_profile
    patient = get_object_or_404(Patient, pk=patient_id)
    room, created = ChatRoom.objects.get_or_create(patient=patient, doctor=doctor)
    return redirect('chat_room', room_id=room.pk)


@login_required
def chat_messages_api(request, room_id):
    """AJAX: yangi xabarlarni olish"""
    user = request.user
    room = get_object_or_404(ChatRoom, pk=room_id)
    after = request.GET.get('after', '')

    msgs = room.messages.select_related('sender').order_by('created_at')
    if after:
        try:
            msgs = msgs.filter(pk__gt=int(after))
        except ValueError:
            pass

    # mark as read
    room.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)

    data = [{
        'id': m.pk,
        'text': m.text,
        'sender': m.sender.get_full_name() or m.sender.username,
        'is_me': m.sender == user,
        'is_prescription': m.is_prescription,
        'time': m.created_at.strftime('%H:%M'),
    } for m in msgs]
    return JsonResponse({'messages': data})
