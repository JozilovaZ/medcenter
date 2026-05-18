from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
import random
from core.models import (
    Specialty, Doctor, Patient, ServiceCategory, Service,
    ServicePackage, Appointment, Queue, Payment, MedicalRecord
)


class Command(BaseCommand):
    help = "Demo ma'lumotlarni yaratish (kamida 10 tadan)"

    def handle(self, *args, **options):
        # 1. Specialties (10 ta)
        specialty_names = [
            'Terapevt', 'Kardiolog', 'Nevropatolog', 'Okulist', 'LOR',
            'Ginekolog', 'Urolog', 'Dermatolog', 'Stomatolog', 'Pediatr',
        ]
        specs = []
        for name in specialty_names:
            s, _ = Specialty.objects.get_or_create(name=name)
            specs.append(s)
        self.stdout.write(f'Mutaxassisliklar: {len(specs)} ta')

        # 2. Doctors (10 ta)
        doctors_data = [
            ('Karimov Sherzod Rustamovich',     specs[0], '101', '08:00', '17:00', 15, 4.8),
            ('Rahimova Dilnoza Anvarovna',       specs[1], '102', '09:00', '18:00', 20, 4.9),
            ('Xasanov Bobur Karimovich',         specs[2], '103', '08:00', '16:00', 25, 4.7),
            ('Toshmatova Gulnora Ibrohimovna',   specs[3], '104', '08:30', '17:30', 15, 4.6),
            ('Aliyev Sardor Baxtiyor o\'g\'li',  specs[4], '105', '09:00', '17:00', 15, 4.5),
            ('Yusupova Madina Toxirovna',        specs[5], '201', '08:00', '16:00', 20, 4.9),
            ('Nazarov Jamshid Erkinovich',       specs[6], '202', '09:00', '18:00', 20, 4.7),
            ('Mirzoeva Lola Shuhratovna',        specs[7], '203', '08:00', '17:00', 15, 4.8),
            ('Abdullayev Nodir Farruxovich',     specs[8], '204', '08:00', '18:00', 30, 4.6),
            ('Sultonova Zarina Akmalovna',       specs[9], '205', '08:00', '17:00', 15, 4.9),
        ]
        doctors = []
        for name, spec, room, start, end, dur, rating in doctors_data:
            d, _ = Doctor.objects.get_or_create(
                full_name=name,
                defaults={
                    'specialty': spec, 'room_number': room,
                    'work_start': start, 'work_end': end,
                    'avg_appointment_minutes': dur,
                    'phone': f'+99890{random.randint(1000000, 9999999)}',
                    'rating': rating,
                }
            )
            doctors.append(d)
        self.stdout.write(f'Shifokorlar: {len(doctors)} ta')

        # 3. Service Categories (10 ta)
        category_names = [
            'Konsultatsiya', 'Diagnostika', 'Laboratoriya',
            'Fizioterapiya', 'Stomatologiya', 'Jarrohlik',
            'Onkologiya', 'Nevrologiya', 'Endokrinologiya', 'Pediatriya',
        ]
        cats = {}
        for name in category_names:
            c, _ = ServiceCategory.objects.get_or_create(name=name)
            cats[name] = c
        self.stdout.write(f'Kategoriyalar: {len(cats)} ta')

        # 4. Services (17 ta — 10+ dan ortiq)
        services_data = [
            ('Terapevt konsultatsiyasi',      cats['Konsultatsiya'],   50000,  15),
            ('Kardiolog konsultatsiyasi',      cats['Konsultatsiya'],   80000,  20),
            ('Nevropatolog konsultatsiyasi',   cats['Konsultatsiya'],   70000,  25),
            ('Okulist tekshiruvi',             cats['Konsultatsiya'],   60000,  15),
            ('LOR tekshiruvi',                cats['Konsultatsiya'],   55000,  15),
            ('Ginekolog konsultatsiyasi',      cats['Konsultatsiya'],   75000,  20),
            ('Urolog konsultatsiyasi',         cats['Konsultatsiya'],   65000,  20),
            ('Dermatolog konsultatsiyasi',     cats['Konsultatsiya'],   60000,  15),
            ('Pediatr konsultatsiyasi',        cats['Pediatriya'],      55000,  15),
            ('Endokrinolog konsultatsiyasi',   cats['Endokrinologiya'], 70000,  20),
            ('UZI tekshiruvi',                cats['Diagnostika'],    100000,  20),
            ('EKG',                           cats['Diagnostika'],     40000,  15),
            ('Rentgen',                       cats['Diagnostika'],     80000,  15),
            ('MRT',                           cats['Diagnostika'],    350000,  30),
            ('Umumiy qon tahlili',            cats['Laboratoriya'],    30000,  10),
            ('Bioximik tahlil',               cats['Laboratoriya'],    50000,  10),
            ('Tish plombalash',               cats['Stomatologiya'],  150000,  30),
        ]
        services = []
        for name, cat, price, dur in services_data:
            s, _ = Service.objects.get_or_create(
                name=name, defaults={'category': cat, 'price': price, 'duration_minutes': dur}
            )
            services.append(s)
        self.stdout.write(f'Xizmatlar: {len(services)} ta')

        # 5. Service Packages (5 ta)
        packages_data = [
            ('Umumiy Check-up',    "To'liq sog'liqni tekshirish",        15, services[:5] + [services[10], services[11], services[14]]),
            ('Yurak Check-up',     'Yurak-qon tomir tekshiruvi',         10, [services[1], services[10], services[11], services[14], services[15]]),
            ('Stomatologiya paketi','Tish davolash to\'liq xizmati',     20, [services[16]]),
            ('Ayollar sog\'lig\'i', 'Ginekologiya va profilaktika',      12, [services[5], services[10], services[14], services[15]]),
            ('Bolalar Check-up',   'Bolalar uchun kompleks tekshiruv',   10, [services[8], services[10], services[14]]),
        ]
        for name, desc, disc, svcs in packages_data:
            pkg, _ = ServicePackage.objects.get_or_create(
                name=name, defaults={'description': desc, 'discount_percent': disc}
            )
            pkg.services.set(svcs)
        self.stdout.write('Paketlar: 5 ta')

        # 6. Patients (15 ta)
        patients_data = [
            ('Ahmedov Botir Karimovich',              '+998901234567', 'male',   1985),
            ('Karimova Nigora Rustamovna',            '+998901234568', 'female', 1990),
            ('Toshmatov Sardor Baxtiyor o\'g\'li',    '+998901234569', 'male',   1978),
            ('Rahimova Zilola Anvarovna',             '+998901234570', 'female', 1995),
            ('Xasanov Javohir Sherzod o\'g\'li',      '+998901234571', 'male',   2000),
            ('Mirzoeva Shahlo Toxirovna',             '+998901234572', 'female', 1988),
            ('Nazarov Ulugbek Erkinovich',            '+998901234573', 'male',   1975),
            ('Yusupova Barno Karimovna',              '+998901234574', 'female', 1992),
            ('Sultonov Dostonbek Nodir o\'g\'li',     '+998901234575', 'male',   2002),
            ('Abdullayeva Mohira Farruxovna',         '+998901234576', 'female', 1983),
            ('Ergashev Shuhrat Olimovich',            '+998901234577', 'male',   1970),
            ('Qodirova Feruza Bahodirovna',           '+998901234578', 'female', 1998),
            ('Umarov Sanjar Toxirovich',              '+998901234579', 'male',   1987),
            ('Ismoilova Kamola Rashidovna',           '+998901234580', 'female', 1993),
            ('Raxmatullayev Aziz Kamoliddinovich',    '+998901234581', 'male',   1980),
        ]
        patients = []
        for name, phone, gender, birth_year in patients_data:
            birth = date(birth_year, random.randint(1, 12), random.randint(1, 28))
            p, _ = Patient.objects.get_or_create(
                phone=phone,
                defaults={
                    'full_name': name, 'gender': gender,
                    'birth_date': birth,
                    'address': 'Toshkent sh.',
                }
            )
            patients.append(p)
        self.stdout.write(f'Bemorlar: {len(patients)} ta')

        # 7. Appointments (10 ta bugun + 10 ta o'tgan kunlar)
        today = timezone.now().date()
        statuses = ['scheduled', 'waiting', 'completed', 'completed', 'completed', 'cancelled', 'no_show']
        appointment_count = 0

        # Bugungi qabullar
        for i in range(10):
            patient = patients[i % len(patients)]
            doctor = doctors[i % len(doctors)]
            service = services[i % len(services)]
            hour = 8 + i
            status = statuses[i % len(statuses)]
            apt, created = Appointment.objects.get_or_create(
                patient=patient, doctor=doctor,
                date=today, time=f'{hour:02d}:00',
                defaults={'service': service, 'status': status,
                          'notes': f'Qabul #{i+1} izohi'}
            )
            if created:
                appointment_count += 1
                _create_payment(apt, service, status)
                if status == 'waiting':
                    Queue.objects.get_or_create(
                        ticket_number=Queue.generate_ticket(),
                        patient=patient, doctor=doctor,
                        defaults={'appointment': apt}
                    )

        # O'tgan kunlarning qabullari (10 ta)
        for i in range(10):
            patient = patients[(i + 5) % len(patients)]
            doctor = doctors[(i + 3) % len(doctors)]
            service = services[(i + 2) % len(services)]
            past_date = today - timedelta(days=random.randint(1, 30))
            hour = 9 + (i % 8)
            apt, created = Appointment.objects.get_or_create(
                patient=patient, doctor=doctor,
                date=past_date, time=f'{hour:02d}:30',
                defaults={'service': service, 'status': 'completed',
                          'diagnosis': f'Tashxis #{i+1}: sog\'lom holat'}
            )
            if created:
                appointment_count += 1
                _create_payment(apt, service, 'completed')
                MedicalRecord.objects.get_or_create(
                    patient=patient, appointment=apt,
                    defaults={
                        'doctor': doctor,
                        'diagnosis': f'Tashxis #{i+1}: bemorning ahvoli qoniqarli',
                        'prescription': f'Dori #{i+1}: kuniga 2 marta',
                        'notes': 'Nazoratga kelish tavsiya etiladi',
                    }
                )

        self.stdout.write(f'Qabullar yaratildi: {appointment_count} ta yangi')

        # 8. Queue — bugungi waiting qabullar uchun (agar yaratilmagan bo'lsa)
        q_count = Queue.objects.count()
        self.stdout.write(f'Navbatlar: {q_count} ta')

        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar muvaffaqiyatli yaratildi!"))


def _create_payment(apt, service, status):
    paid = service.price if status == 'completed' else 0
    pay_status = 'paid' if status == 'completed' else 'pending'
    method = random.choice(['cash', 'card', 'transfer'])
    Payment.objects.get_or_create(
        appointment=apt,
        defaults={
            'patient': apt.patient,
            'service': service,
            'amount': service.price,
            'paid_amount': paid,
            'status': pay_status,
            'method': method,
        }
    )
