#!/usr/bin/env python
"""
Database initialization script for MediScript Pro
Run this script to set up the database and create initial data
"""

from app import app, db, User, DoctorProfile, Patient, Prescription
from datetime import datetime, date
import json

def init_database():
    """Initialize the database with tables"""
    with app.app_context():
        # Drop all tables and recreate (for development only)
        db.drop_all()
        db.create_all()
        print("✅ Database tables created successfully!")

def create_sample_data():
    """Create sample data for testing"""
    with app.app_context():
        try:
            # Create sample doctor user
            sample_user = User(
                email='doctor@example.com',
                name='Dr. John Smith',
                provider='local',
                is_active=True
            )
            db.session.add(sample_user)
            db.session.flush()  # Get the ID
            
            # Create doctor profile
            doctor_profile = DoctorProfile(
                user_id=sample_user.id,
                full_name='Dr. John Smith',
                designation='MBBS, MD',
                specialization='General Medicine, Cardiology',
                license_number='MED12345',
                experience_years=10,
                phone='+1-555-123-4567',
                hospital_name='City General Hospital',
                hospital_address='123 Medical Street\nHealthcare City, HC 12345',
                hospital_phone='+1-555-987-6543',
                hospital_email='info@citygeneral.com',
                education='MBBS from Medical University\nMD in Internal Medicine',
                certifications='Board Certified Internal Medicine\nAdvanced Cardiac Life Support (ACLS)'
            )
            db.session.add(doctor_profile)
            
            # Create sample patients
            patients_data = [
                {
                    'name': 'Alice Johnson',
                    'age': 35,
                    'gender': 'Female',
                    'phone': '+1-555-111-2222',
                    'email': 'alice.johnson@email.com',
                    'blood_group': 'A+',
                    'address': '456 Oak Street, Cityville, CV 67890',
                    'allergies': 'Penicillin, Shellfish',
                    'medical_history': 'Hypertension, Previous surgery in 2020'
                },
                {
                    'name': 'Robert Brown',
                    'age': 58,
                    'gender': 'Male',
                    'phone': '+1-555-333-4444',
                    'email': 'robert.brown@email.com',
                    'blood_group': 'O-',
                    'address': '789 Pine Avenue, Townsburg, TB 13579',
                    'allergies': 'None known',
                    'medical_history': 'Diabetes Type 2, High cholesterol',
                    'is_starred': True
                },
                {
                    'name': 'Emily Davis',
                    'age': 28,
                    'gender': 'Female',
                    'phone': '+1-555-555-6666',
                    'email': 'emily.davis@email.com',
                    'blood_group': 'B+',
                    'address': '321 Maple Drive, Villageton, VT 24680',
                    'medical_history': 'Asthma, Seasonal allergies'
                },
                {
                    'name': 'Michael Wilson',
                    'age': 42,
                    'gender': 'Male',
                    'phone': '+1-555-777-8888',
                    'blood_group': 'AB+',
                    'address': '654 Elm Street, Hamletville, HV 97531',
                    'allergies': 'Aspirin',
                    'medical_history': 'Previous heart surgery, Regular checkups required'
                },
                {
                    'name': 'Sarah Martinez',
                    'age': 31,
                    'gender': 'Female',
                    'phone': '+1-555-999-0000',
                    'email': 'sarah.martinez@email.com',
                    'blood_group': 'O+',
                    'address': '987 Cedar Lane, Boroughtown, BT 86420',
                    'medical_history': 'Pregnancy complications in 2022'
                }
            ]
            
            created_patients = []
            for patient_data in patients_data:
                patient = Patient(
                    patient_id=f"PT{datetime.now().strftime('%Y%m%d')}{len(created_patients)+1:04d}",
                    **patient_data
                )
                db.session.add(patient)
                created_patients.append(patient)
            
            db.session.flush()  # Get patient IDs
            
            # Create sample prescriptions
            prescriptions_data = [
                {
                    'patient': created_patients[0],
                    'chief_complaint': 'Chest pain and shortness of breath for 2 days',
                    'diagnosis': 'Acute bronchitis with chest congestion',
                    'notes': 'Patient advised rest and plenty of fluids. Follow-up if symptoms persist.',
                    'is_rare_case': False
                },
                {
                    'patient': created_patients[1],
                    'chief_complaint': 'Uncontrolled blood sugar levels, frequent urination',
                    'diagnosis': 'Diabetes mellitus type 2, poor glycemic control',
                    'notes': 'Medication adjustment needed. Dietary counseling provided.',
                    'follow_up_date': date(2025, 8, 20),
                    'is_rare_case': False
                },
                {
                    'patient': created_patients[2],
                    'chief_complaint': 'Severe headaches with visual disturbances',
                    'diagnosis': 'Migraine with aura, possible hormonal trigger',
                    'notes': 'Prescribed triptan therapy. Advised trigger avoidance.',
                    'is_rare_case': True
                },
                {
                    'patient': created_patients[3],
                    'chief_complaint': 'Irregular heartbeat and dizziness',
                    'diagnosis': 'Atrial fibrillation, new onset',
                    'notes': 'Cardiology referral recommended. ECG shows irregular rhythm.',
                    'follow_up_date': date(2025, 8, 15),
                    'is_rare_case': True
                },
                {
                    'patient': created_patients[4],
                    'chief_complaint': 'Persistent cough and fatigue',
                    'diagnosis': 'Upper respiratory tract infection',
                    'notes': 'Symptomatic treatment prescribed. Return if fever develops.',
                    'is_rare_case': False
                }
            ]
            
            for i, prescription_data in enumerate(prescriptions_data):
                prescription = Prescription(
                    prescription_id=f"RX{datetime.now().strftime('%Y%m%d')}{i+1:04d}",
                    doctor_id=sample_user.id,
                    patient_id=prescription_data['patient'].id,
                    chief_complaint=prescription_data['chief_complaint'],
                    diagnosis=prescription_data['diagnosis'],
                    notes=prescription_data['notes'],
                    follow_up_date=prescription_data.get('follow_up_date'),
                    is_rare_case=prescription_data['is_rare_case'],
                    canvas_pages=json.dumps([]),  # Empty canvas for sample data
                    signature_data='',  # Empty signature for sample data
                    medications=json.dumps([])  # Empty medications for sample data
                )
                db.session.add(prescription)
            
            db.session.commit()
            print("✅ Sample data created successfully!")
            print(f"📧 Sample doctor login: doctor@example.com")
            print(f"👥 Created {len(created_patients)} sample patients")
            print(f"📋 Created {len(prescriptions_data)} sample prescriptions")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating sample data: {str(e)}")

def reset_database():
    """Reset the database (WARNING: This will delete all data!)"""
    with app.app_context():
        response = input("⚠️  This will delete ALL data. Are you sure? (type 'yes' to confirm): ")
        if response.lower() == 'yes':
            db.drop_all()
            db.create_all()
            print("✅ Database reset successfully!")
        else:
            print("❌ Database reset cancelled.")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'reset':
            reset_database()
        elif sys.argv[1] == 'sample':
            init_database()
            create_sample_data()
        else:
            print("Usage:")
            print("  python init_db.py          # Initialize empty database")
            print("  python init_db.py sample   # Initialize with sample data")
            print("  python init_db.py reset    # Reset database (WARNING: Deletes all data)")
    else:
        init_database()
        print("💡 Run 'python init_db.py sample' to add sample data for testing.")