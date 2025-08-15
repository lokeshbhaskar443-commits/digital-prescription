from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_moment import Moment
from authlib.integrations.flask_client import OAuth
import base64
import json
import os
from datetime import datetime, date, timedelta
import io
import pdfkit
from PIL import Image
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from urllib.parse import urlparse

load_dotenv()

app = Flask(__name__)
moment = Moment(app)

# Database Configuration
def get_database_uri():
    """Get database URI from environment with Railway support"""
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Railway provides postgres:// but SQLAlchemy needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    else:
        # Fallback to SQLite for local development
        return 'sqlite:///prescription_system.db'

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(16))
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Production optimizations for PostgreSQL
if os.getenv('FLASK_ENV') == 'production':
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

# OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
app.config['FACEBOOK_CLIENT_ID'] = os.getenv('FACEBOOK_CLIENT_ID')
app.config['FACEBOOK_CLIENT_SECRET'] = os.getenv('FACEBOOK_CLIENT_SECRET')

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
oauth = OAuth(app)

# Configure OAuth providers
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

facebook = oauth.register(
    name='facebook',
    client_id=app.config['FACEBOOK_CLIENT_ID'],
    client_secret=app.config['FACEBOOK_CLIENT_SECRET'],
    access_token_url='https://graph.facebook.com/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    api_base_url='https://graph.facebook.com/',
    client_kwargs={'scope': 'email'}
)

# Configuration for wkhtmltopdf
try:
    config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
except:
    config = None  # Will use system default

# Cloud Storage Manager
class CloudStorageManager:
    def __init__(self):
        pass
    
    def upload_pdf(self, pdf_data, filename, prescription_id):
        """Upload PDF to Cloudinary"""
        try:
            # Create unique path
            file_path = f"prescriptions/{prescription_id}/{filename}"
            
            # Convert binary data to base64 for Cloudinary
            pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
            
            result = cloudinary.uploader.upload(
                f"data:application/pdf;base64,{pdf_b64}",
                public_id=file_path,
                resource_type="raw",  # For non-image files
                access_mode="authenticated",  # Require authentication to access
                folder=f"prescriptions/{prescription_id}"
            )
            
            return {'success': True, 'url': result['secure_url'], 'path': result['public_id']}
            
        except Exception as e:
            print(f"Upload error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_secure_url(self, file_path, expiration=3600):
        """Generate secure URL for existing file"""
        try:
            return cloudinary.utils.private_download_url(file_path, 'raw', expires_at=expiration)
        except Exception as e:
            print(f"URL generation error: {str(e)}")
            return None

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(200))
    password_hash = db.Column(db.String(128))
    provider = db.Column(db.String(50))  # google, facebook, local
    provider_id = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Doctor details
    doctor_profile = db.relationship('DoctorProfile', backref='user', uselist=False)
    prescriptions = db.relationship('Prescription', backref='doctor', lazy=True)

class DoctorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Personal Information
    full_name = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    specialization = db.Column(db.String(200))
    license_number = db.Column(db.String(50))
    experience_years = db.Column(db.Integer)
    phone = db.Column(db.String(20))
    
    # Hospital Information
    hospital_name = db.Column(db.String(200))
    hospital_address = db.Column(db.Text)
    hospital_phone = db.Column(db.String(20))
    hospital_email = db.Column(db.String(120))
    hospital_logo_path = db.Column(db.String(200))  # Cloudinary path
    
    # Professional Details
    education = db.Column(db.Text)
    certifications = db.Column(db.Text)
    signature = db.Column(db.Text)  # Base64 encoded signature
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(20))
    blood_group = db.Column(db.String(5))
    allergies = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    is_starred = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prescriptions = db.relationship('Prescription', backref='patient', lazy=True)

class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.String(50), unique=True, nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    
    chief_complaint = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    medications = db.Column(db.Text)  # JSON string
    notes = db.Column(db.Text)
    follow_up_date = db.Column(db.Date)
    is_rare_case = db.Column(db.Boolean, default=False)
    
    canvas_pages = db.Column(db.Text)  # JSON string of canvas data
    signature_data = db.Column(db.Text)  # Base64 encoded signature
    
    # Cloud storage paths
    pdf_cloud_path = db.Column(db.String(500))  # Cloudinary path
    pdf_filename = db.Column(db.String(200))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions
def generate_patient_id():
    return f"PT{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

def generate_prescription_id():
    return f"RX{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/auth/<provider>')
def oauth_login(provider):
    if provider == 'google':
        redirect_uri = url_for('oauth_callback', provider='google', _external=True)
        return google.authorize_redirect(redirect_uri)
    elif provider == 'facebook':
        redirect_uri = url_for('oauth_callback', provider='facebook', _external=True)
        return facebook.authorize_redirect(redirect_uri)
    else:
        flash('Invalid provider', 'error')
        return redirect(url_for('login'))

@app.route('/callback/<provider>')
def oauth_callback(provider):
    try:
        if provider == 'google':
            token = google.authorize_access_token()
            user_info = token.get('userinfo')
            if user_info:
                email = user_info['email']
                name = user_info['name']
                profile_picture = user_info.get('picture')
                provider_id = user_info['sub']
        elif provider == 'facebook':
            token = facebook.authorize_access_token()
            user_info = facebook.get('me?fields=id,email,name,picture', token=token).json()
            email = user_info.get('email')
            name = user_info['name']
            profile_picture = user_info.get('picture', {}).get('data', {}).get('url')
            provider_id = user_info['id']
        else:
            flash('Invalid provider', 'error')
            return redirect(url_for('login'))

        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user
            user = User(
                email=email,
                name=name,
                profile_picture=profile_picture,
                provider=provider,
                provider_id=provider_id
            )
            db.session.add(user)
            db.session.commit()
            
            # Create doctor profile
            doctor_profile = DoctorProfile(
                user_id=user.id,
                full_name=name
            )
            db.session.add(doctor_profile)
            db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash(f'Authentication failed: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get statistics
    total_patients = Patient.query.count()
    total_prescriptions = Prescription.query.filter_by(doctor_id=current_user.id).count()
    starred_patients = Patient.query.filter_by(is_starred=True).count()
    rare_cases = Prescription.query.filter_by(doctor_id=current_user.id, is_rare_case=True).count()
    
    # Recent prescriptions
    recent_prescriptions = Prescription.query.filter_by(doctor_id=current_user.id)\
                          .order_by(Prescription.created_at.desc()).limit(5).all()
    
    # Recent patients
    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()
    
    stats = {
        'total_patients': total_patients,
        'total_prescriptions': total_prescriptions,
        'starred_patients': starred_patients,
        'rare_cases': rare_cases
    }
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_prescriptions=recent_prescriptions,
                         recent_patients=recent_patients)

@app.route('/profile')
@login_required
def profile():
    doctor_profile = current_user.doctor_profile
    if not doctor_profile:
        doctor_profile = DoctorProfile(user_id=current_user.id)
        db.session.add(doctor_profile)
        db.session.commit()
    return render_template('profile.html', profile=doctor_profile)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        profile = current_user.doctor_profile
        if not profile:
            profile = DoctorProfile(user_id=current_user.id)
            db.session.add(profile)
        
        # Update personal information
        profile.full_name = request.form.get('full_name', '')
        profile.designation = request.form.get('designation', '')
        profile.specialization = request.form.get('specialization', '')
        profile.license_number = request.form.get('license_number', '')
        profile.experience_years = int(request.form.get('experience_years', 0) or 0)
        profile.phone = request.form.get('phone', '')
        profile.education = request.form.get('education', '')
        profile.certifications = request.form.get('certifications', '')
        
        # Update hospital information
        profile.hospital_name = request.form.get('hospital_name', '')
        profile.hospital_address = request.form.get('hospital_address', '')
        profile.hospital_phone = request.form.get('hospital_phone', '')
        profile.hospital_email = request.form.get('hospital_email', '')
        
        # Handle hospital logo upload to Cloudinary
        if 'hospital_logo' in request.files:
            file = request.files['hospital_logo']
            if file and allowed_file(file.filename):
                try:
                    # Upload to Cloudinary
                    result = cloudinary.uploader.upload(
                        file,
                        folder=f"hospital_logos/{current_user.id}",
                        public_id=f"logo_{current_user.id}",
                        overwrite=True,
                        resource_type="image"
                    )
                    profile.hospital_logo_path = result['public_id']
                except Exception as e:
                    flash(f'Error uploading logo: {str(e)}', 'error')
        
        # Handle signature
        signature_data = request.form.get('signature_data')
        if signature_data:
            profile.signature = signature_data
        
        profile.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
        
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'error')
        return redirect(url_for('profile'))

@app.route('/patients')
@login_required
def patients():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    filter_starred = request.args.get('starred', False, type=bool)
    
    query = Patient.query
    
    if search:
        query = query.filter(
            (Patient.name.contains(search)) |
            (Patient.patient_id.contains(search)) |
            (Patient.phone.contains(search))
        )
    
    if filter_starred:
        query = query.filter_by(is_starred=True)
    
    patients = query.order_by(Patient.created_at.desc())\
                   .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('patients.html', patients=patients, search=search, filter_starred=filter_starred)

@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    prescriptions = Prescription.query.filter_by(patient_id=patient_id)\
                                    .order_by(Prescription.created_at.desc()).all()
    return render_template('patient_detail.html', patient=patient, prescriptions=prescriptions)

@app.route('/toggle_star_patient/<int:patient_id>', methods=['POST'])
@login_required
def toggle_star_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.is_starred = not patient.is_starred
    db.session.commit()
    return jsonify({'success': True, 'starred': patient.is_starred})

@app.route('/rare_cases')
@login_required
def rare_cases():
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    cases = Prescription.query.filter(
        Prescription.doctor_id == current_user.id,
        Prescription.is_rare_case == True,
        Prescription.created_at > cutoff_date
    ).order_by(Prescription.created_at.desc()).all()

    return render_template('rare_cases.html', cases=cases)

@app.route('/prescription_history')
@login_required
def prescription_history():
    page = request.args.get('page', 1, type=int)
    prescriptions = Prescription.query.filter_by(doctor_id=current_user.id)\
                                     .order_by(Prescription.created_at.desc())\
                                     .paginate(page=page, per_page=20, error_out=False)
    return render_template('prescription_history.html', prescriptions=prescriptions, date=date)

@app.route('/new_prescription')
@login_required
def new_prescription():
    patients = Patient.query.order_by(Patient.name).all()
    return render_template('prescription.html', patients=patients)

@app.route('/create_patient', methods=['POST'])
@login_required
def create_patient():
    try:
        data = request.json
        
        patient = Patient(
            patient_id=generate_patient_id(),
            name=data['name'],
            age=int(data.get('age', 0) or 0),
            gender=data.get('gender', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            address=data.get('address', ''),
            emergency_contact=data.get('emergency_contact', ''),
            blood_group=data.get('blood_group', ''),
            allergies=data.get('allergies', ''),
            medical_history=data.get('medical_history', '')
        )
        
        db.session.add(patient)
        db.session.commit()
        
        return jsonify({'success': True, 'patient_id': patient.id, 'patient_display_id': patient.patient_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/save_prescription', methods=['POST'])
@login_required
def save_prescription():
    try:
        data = request.json
        
        # Get or create patient
        patient_id = data.get('patient_id')
        if not patient_id:
            # Create new patient
            patient = Patient(
                patient_id=generate_patient_id(),
                name=data['patient_info']['name'],
                age=int(data['patient_info'].get('age', 0) or 0),
                gender=data['patient_info'].get('gender', ''),
                phone=data['patient_info'].get('contact', '')
            )
            db.session.add(patient)
            db.session.flush()  # Get the ID without committing
            patient_id = patient.id
        
        # Create prescription
        prescription = Prescription(
            prescription_id=generate_prescription_id(),
            doctor_id=current_user.id,
            patient_id=patient_id,
            chief_complaint=data.get('chief_complaint', ''),
            diagnosis=data.get('diagnosis', ''),
            medications=json.dumps(data.get('medications', [])),
            notes=data.get('notes', ''),
            canvas_pages=json.dumps(data.get('pages', [])),
            signature_data=data.get('signature', ''),
            is_rare_case=data.get('is_rare_case', False)
        )
        
        if data.get('follow_up_date'):
            prescription.follow_up_date = datetime.strptime(data['follow_up_date'], '%Y-%m-%d').date()
        
        db.session.add(prescription)
        db.session.commit()
        
        return jsonify({'success': True, 'prescription_id': prescription.prescription_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate_pdf', methods=['POST'])
@login_required
def generate_pdf():
    try:
        data = request.json
        html_content = data.get('html_content')
        prescription_id = data.get('prescription_id')
        
        # Configure PDF options
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }
        
        # Generate PDF
        if config:
            pdf_data = pdfkit.from_string(html_content, False, options=options, configuration=config)
        else:
            pdf_data = pdfkit.from_string(html_content, False, options=options)
        
        # Store PDF in Cloudinary if prescription_id is provided
        if prescription_id:
            prescription = Prescription.query.filter_by(prescription_id=prescription_id).first()
            if prescription:
                storage_manager = CloudStorageManager()
                filename = f'prescription_{prescription_id}.pdf'
                upload_result = storage_manager.upload_pdf(pdf_data, filename, prescription_id)
                
                if upload_result and upload_result['success']:
                    prescription.pdf_cloud_path = upload_result['path']
                    prescription.pdf_filename = filename
                    db.session.commit()
        
        # Return PDF for immediate download
        pdf_file = io.BytesIO(pdf_data)
        pdf_file.seek(0)
        
        return send_file(
            pdf_file,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'prescription_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download_prescription_pdf/<prescription_id>')
@login_required
def download_prescription_pdf(prescription_id):
    prescription = Prescription.query.filter_by(
        prescription_id=prescription_id,
        doctor_id=current_user.id
    ).first_or_404()
    
    if not prescription.pdf_cloud_path:
        flash('PDF not found', 'error')
        return redirect(url_for('prescription_history'))
    
    storage_manager = CloudStorageManager()
    secure_url = storage_manager.get_secure_url(prescription.pdf_cloud_path)
    
    if secure_url:
        return redirect(secure_url)
    else:
        flash('Error generating download link', 'error')
        return redirect(url_for('prescription_history'))

@app.route('/get_hospital_logo/<path:public_id>')
@login_required
def get_hospital_logo(public_id):
    """Get hospital logo from Cloudinary"""
    try:
        logo_url = cloudinary.utils.cloudinary_url(public_id)[0]
        return redirect(logo_url)
    except Exception as e:
        return '', 404

@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

def init_db():
    """Initialize database tables"""
    try:
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")

if __name__ == '__main__':
    with app.app_context():
        init_db()
        
        for directory in ['templates', 'static', 'uploads']:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') != 'production')