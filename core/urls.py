from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Patients
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/create/', views.patient_create, name='patient_create'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:pk>/edit/', views.patient_edit, name='patient_edit'),
    path('api/patients/search/', views.patient_search_api, name='patient_search_api'),

    # Doctors
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/create/', views.doctor_create, name='doctor_create'),
    path('doctors/<int:pk>/', views.doctor_detail, name='doctor_detail'),
    path('doctors/<int:pk>/edit/', views.doctor_edit, name='doctor_edit'),
    path('api/doctors/<int:pk>/schedule/', views.doctor_schedule_api, name='doctor_schedule_api'),
    path('api/specialties/<int:specialty_id>/doctors/', views.doctors_by_specialty_api, name='doctors_by_specialty_api'),
    path('api/specialties/<int:specialty_id>/services/', views.services_by_specialty_api, name='services_by_specialty_api'),

    # Appointments
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/create/', views.appointment_create, name='appointment_create'),
    path('appointments/quick/', views.quick_appointment, name='quick_appointment'),
    path('appointments/<int:pk>/status/<str:status>/', views.appointment_status_update, name='appointment_status_update'),

    # Queue
    path('queue/', views.queue_list, name='queue_list'),
    path('queue/display/', views.queue_display, name='queue_display'),
    path('queue/call/<int:doctor_id>/', views.queue_call_next, name='queue_call_next'),
    path('queue/<int:pk>/status/<str:status>/', views.queue_status_update, name='queue_status_update'),
    path('queue/add/<int:appointment_id>/', views.queue_add, name='queue_add'),
    path('api/queue/monitor/', views.queue_monitor_api, name='queue_monitor_api'),

    # Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/create/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payments/<int:pk>/edit/', views.payment_edit, name='payment_edit'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('payments/<int:pk>/paid/', views.payment_mark_paid, name='payment_mark_paid'),
    path('payments/<int:pk>/partial/', views.payment_partial_pay, name='payment_partial_pay'),
    path('payments/<int:pk>/refund/', views.payment_refund, name='payment_refund'),
    path('payments/<int:pk>/receipt/', views.payment_receipt, name='payment_receipt'),
    path('api/payments/search/', views.payment_search_api, name='payment_search_api'),

    # Statistics
    path('statistics/', views.statistics, name='statistics'),

    # Services
    path('services/', views.service_list, name='service_list'),

    # Patient (Bemor) role pages
    path('my/appointments/', views.my_appointments, name='my_appointments'),
    path('my/queue/', views.my_queue, name='my_queue'),
    path('my/payments/', views.my_payments, name='my_payments'),
    path('my/medical-records/', views.my_medical_records, name='my_medical_records'),

    # Doctor dashboard
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/payments/', views.doctor_payments, name='doctor_payments'),
    path('doctor/my-appointments/', views.doctor_my_appointments, name='doctor_my_appointments'),
    path('doctor/update-schedule/', views.doctor_update_schedule, name='doctor_update_schedule'),
    path('doctor/approve/<int:pk>/', views.doctor_approve_appointment, name='doctor_approve_appointment'),
    path('doctor/reject/<int:pk>/', views.doctor_reject_appointment, name='doctor_reject_appointment'),
    path('doctor/write-record/<int:appointment_id>/', views.doctor_write_record, name='doctor_write_record'),

    # Patient dashboard
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/book/', views.patient_book_appointment, name='patient_book'),

    # Chat
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/<int:room_id>/', views.chat_room, name='chat_room'),
    path('chat/start/<int:doctor_id>/', views.chat_start, name='chat_start'),
    path('chat/start-with-patient/<int:patient_id>/', views.chat_start_with_patient, name='chat_start_with_patient'),
    path('api/chat/<int:room_id>/messages/', views.chat_messages_api, name='chat_messages_api'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
]
