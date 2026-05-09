from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from core.models import (
    Specialty, Doctor, Patient, ServiceCategory, Service,
    ServicePackage, Appointment, Queue, Payment
)


class Command(BaseCommand):
    help = 'Demo ma\'lumotlarni yaratish'

    def handle(self, *args, **options):
        # Specialties
        specs = []
        for name in ['Terapevt', 'Kardiolog', 'Nevropatolog', 'Okulist', 'LOR', 'Ginekolog', 'Urolog', 'Dermatolog', 'Stomatolog', 'Pediatr']:
            s, _ = Specialty.objects.get_or_create(name=name)
            specs.append(s)
        self.stdout.write('Mutaxassisliklar yaratildi')

        # Doctors
        doctors_data = [
            ('Karimov Sherzod Rustamovich', specs[0], '101', '08:00', '17:00', 15),
            ('Rahimova Dilnoza Anvarovna', specs[1], '102', '09:00', '18:00', 20),
            ('Xasanov Bobur Karimovich', specs[2], '103', '08:00', '16:00', 25),
            ('Toshmatova Gulnora Ibrohimovna', specs[3], '104', '08:30', '17:30', 15),
            ('Aliyev Sardor Baxtiyor o\'g\'li', specs[4], '105', '09:00', '17:00', 15),
            ('Yusupova Madina Toxirovna', specs[5], '201', '08:00', '16:00', 20),
            ('Nazarov Jamshid Erkinovich', specs[6], '202', '09:00', '18:00', 20),
            ('Mirzoeva Lola Shuhratovna', specs[7], '203', '08:00', '17:00', 15),
            ('Abdullayev Nodir Farruxovich', specs[8], '204', '08:00', '18:00', 30),
            ('Sultonova Zarina Akmalovna', specs[9], '205', '08:00', '17:00', 15),
        ]
        doctors = []
        for name, spec, room, start, end, dur in doctors_data:
            d, _ = Doctor.objects.get_or_create(
                full_name=name,
                defaults={
                    'specialty': spec, 'room_number': room,
                    'work_start': start, 'work_end': end,
                    'avg_appointment_minutes': dur,
                    'phone': f'+99890{random.randint(1000000, 9999999)}',
                    'rating': round(random.uniform(4.0, 5.0), 1),
                }
            )
            doctors.append(d)
        self.stdout.write('Shifokorlar yaratildi')

        # Service Categories
        cats = {}
        for name in ['Konsultatsiya', 'Diagnostika', 'Laboratoriya', 'Fizioterapiya', 'Stomatologiya']:
            c, _ = ServiceCategory.objects.get_or_create(name=name)
            cats[name] = c

        # Services
        services_data = [
            ('Terapevt konsultatsiyasi', cats['Konsultatsiya'], 50000, 15),
            ('Kardiolog konsultatsiyasi', cats['Konsultatsiya'], 80000, 20),
            ('Nevropatolog konsultatsiyasi', cats['Konsultatsiya'], 70000, 25),
            ('Okulist tekshiruvi', cats['Konsultatsiya'], 60000, 15),
            ('LOR tekshiruvi', cats['Konsultatsiya'], 55000, 15),
            ('UZI tekshiruvi', cats['Diagnostika'], 100000, 20),
            ('EKG', cats['Diagnostika'], 40000, 15),
            ('Rentgen', cats['Diagnostika'], 80000, 15),
            ('MRT', cats['Diagnostika'], 350000, 30),
            ('Umumiy qon tahlili', cats['Laboratoriya'], 30000, 10),
            ('Bioximik tahlil', cats['Laboratoriya'], 50000, 10),
            ('Qon guruhi', cats['Laboratoriya'], 25000, 10),
            ('Fizioterapiya seansi', cats['Fizioterapiya'], 40000, 30),
            ('Massaj', cats['Fizioterapiya'], 60000, 45),
            ('Tish plombalash', cats['Stomatologiya'], 150000, 30),
            ('Tish olish', cats['Stomatologiya'], 100000, 20),
            ('Professional tozalash', cats['Stomatologiya'], 200000, 45),
        ]
        services = []
        for name, cat, price, dur in services_data:
            s, _ = Service.objects.get_or_create(
                name=name, defaults={'category': cat, 'price': price, 'duration_minutes': dur}
            )
            services.append(s)
        self.stdout.write('Xizmatlar yaratildi')

        # Service Packages
        pkg1, _ = ServicePackage.objects.get_or_create(
            name='Umumiy Check-up', defaults={'description': 'To\'liq sog\'liqni tekshirish', 'discount_percent': 15}
        )
        pkg1.services.set(services[:5] + [services[5], services[6], services[9]])

        pkg2, _ = ServicePackage.objects.get_or_create(
            name='Yurak Check-up', defaults={'description': 'Yurak-qon tomir tekshiruvi', 'discount_percent': 10}
        )
        pkg2.services.set([services[1], services[5], services[6], services[9], services[10]])

        pkg3, _ = ServicePackage.objects.get_or_create(
            name='Stomatologiya paketi', defaults={'description': 'Tish davolash to\'liq xizmati', 'discount_percent': 20}
        )
        pkg3.services.set(services[14:17])
        self.stdout.write('Paketlar yaratildi')

        # Patients
        patients_names = [
            ('Ahmedov Botir Karimovich', '+998901234567', 'male'),
            ('Karimova Nigora Rustamovna', '+998901234568', 'female'),
            ('Toshmatov Sardor Baxtiyor o\'g\'li', '+998901234569', 'male'),
            ('Rahimova Zilola Anvarovna', '+998901234570', 'female'),
            ('Xasanov Javohir Sherzod o\'g\'li', '+998901234571', 'male'),
            ('Mirzoeva Shahlo Toxirovna', '+998901234572', 'female'),
            ('Nazarov Ulugbek Erkinovich', '+998901234573', 'male'),
            ('Yusupova Barno Karimovna', '+998901234574', 'female'),
            ('Sultonov Dostonbek Nodir o\'g\'li', '+998901234575', 'male'),
            ('Abdullayeva Mohira Farruxovna', '+998901234576', 'female'),
            ('Ergashev Shuhrat Olimovich', '+998901234577', 'male'),
            ('Qodirova Feruza Bahodirovna', '+998901234578', 'female'),
            ('Umarov Sanjar Toxirovich', '+998901234579', 'male'),
            ('Ismoilova Kamola Rashidovna', '+998901234580', 'female'),
            ('Raxmatullayev Aziz Kamoliddinovich', '+998901234581', 'male'),
        ]
        patients = []
        for name, phone, gender in patients_names:
            p, _ = Patient.objects.get_or_create(
                phone=phone,
                defaults={
                    'full_name': name, 'gender': gender,
                    'birth_date': timezone.now().date() - timedelta(days=random.randint(7000, 25000)),
                    'address': 'Toshkent sh.',
                }
            )
            patients.append(p)
        self.stdout.write('Bemorlar yaratildi')

        # Appointments for today
        today = timezone.now().date()
        for i in range(10):
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            service = random.choice(services)
            hour = random.randint(8, 16)
            minute = random.choice([0, 15, 30, 45])
            status = random.choice(['scheduled', 'waiting', 'completed'])

            apt, created = Appointment.objects.get_or_create(
                patient=patient, doctor=doctor, date=today,
                time=f'{hour:02d}:{minute:02d}',
                defaults={'service': service, 'status': status}
            )
            if created:
                Payment.objects.create(
                    patient=patient, appointment=apt, service=service,
                    amount=service.price,
                    paid_amount=service.price if status == 'completed' else 0,
                    status='paid' if status == 'completed' else 'pending',
                )
                if status == 'waiting':
                    Queue.objects.create(
                        ticket_number=Queue.generate_ticket(),
                        patient=patient, doctor=doctor, appointment=apt,
                    )

        self.stdout.write(self.style.SUCCESS('Demo ma\'lumotlar muvaffaqiyatli yaratildi!'))
