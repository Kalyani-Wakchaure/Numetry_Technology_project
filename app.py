from flask import Flask, render_template, redirect, jsonify, url_for, flash, render_template_string, request, session
from flask_mail import Mail, Message
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import random
import requests
from forms import RegistrationForm, LoginForm, ForgotPasswordForm, EnterOTPForm, ResetPasswordForm, EnquiryForm
from config import Config
from twilio.rest import Client
import time, datetime

app = Flask(__name__)
app.config.from_object(Config)

trigger_options = {
    'hello': ['Frontend', 'Backend', 'Fullstack'],
    'Frontend': ['HTML', 'CSS', 'JavaScript', 'React'],
    'Backend': ['Python', 'Node.js', 'Java', 'Ruby'],
    'Fullstack': ['MERN', 'MEAN', 'LAMP', 'Django']
}

# Initialize conversation state
conversation_state = {
    'current_trigger': None
}

mail = Mail(app)

def get_db_connection():
    return mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME']
    )

def send_otp_email(to_email, otp):
    msg = Message('Password Reset OTP', sender=app.config['MAIL_USERNAME'], recipients=[to_email])
    msg.body = f'''Your OTP for password reset is: {otp}

If you did not request this, please ignore this email.
'''
    with app.app_context():
        mail.send(msg)

def send_sms(contact, message_body):
    account_sid = ''#add your account sid
    auth_token = ''# add your token
    from_number = ''#add your twilio number

    client = Client(account_sid, auth_token)

    try:
        # Check if the contact number starts with '+'
        if not contact.startswith('+'):
            contact = f'+{contact}'

        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=contact
        )
        print(f"Message SID: {message.sid}")
        return True, "SMS sent successfully."
    except Exception as e:
        return False, f"Error sending SMS: {str(e)}"

# Function to send SMS (mock implementation)
'''def send_sms(contact_number, message):
    print(f"Sending SMS to {contact_number}: {message}")'''  # Replace with actual SMS sending logic


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, contact, password) VALUES (%s, %s, %s, %s)",
                       (form.name.data, form.email.data, form.contact.data, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (form.email.data,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], form.password.data):
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (form.email.data,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['reset_email'] = user['email']
            send_otp_email(user['email'], otp)
            flash('An email has been sent with the OTP.', 'info')
            print(f"Generated OTP: {otp}")
            return redirect(url_for('enter_otp'))
        else:
            flash('No account found with that email.', 'danger')
    return render_template('forgot_password.html', form=form)

@app.route('/enter_otp', methods=['GET', 'POST'])
def enter_otp():
    form = EnterOTPForm()
    if form.validate_on_submit():
        entered_otp = form.otp.data
        stored_otp = session.get('otp')
        print(f"Entered OTP: {entered_otp}")  # Debug print
        print(f"Stored OTP: {stored_otp}")  # Debug print
        if entered_otp == stored_otp:  # Compare as strings
            flash('OTP verified successfully!', 'success')
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid OTP. Please try again.', 'danger')
    return render_template('enter_otp.html', form=form)

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = %s WHERE email = %s",
                       (hashed_password, session.get('reset_email')))
        conn.commit()
        cursor.close()
        conn.close()
        session.pop('otp', None)
        session.pop('reset_email', None)
        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return "Welcome to Numetry Technology!"

# Route for enquiry form
@app.route('/enquiry', methods=['GET', 'POST'])
def enquiry():
    form = EnquiryForm()
    
    if form.validate_on_submit():
        # Process form data and store in the database
        first_name = form.first_name.data
        last_name = form.last_name.data
        contact = form.contact.data
        email = form.email.data

        # Ensure the contact number is in E.164 format
        if not contact.startswith('+'):
            contact = f'+{contact}'

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO enquiries (first_name, last_name, contact, email) VALUES (%s, %s, %s, %s)",
                       (first_name, last_name, contact, email))
        conn.commit()
        cursor.close()
        conn.close()

        # Send SMS notification
        message_body = f"Hi {first_name}, your enquiry form has been submitted successfully!"
        success, msg = send_sms(form.contact.data, message_body)
        
        if success:
            flash('Enquiry form submitted successfully! A confirmation SMS has been sent.', 'success')
        else:
            flash(f'Error sending SMS: {msg}', 'danger')

        return redirect(url_for('dashboard'))

    return render_template('enquiry.html', form=form)
#images = ["Image1.gif", "Image2.gif", "Image3.gif"] 
@app.route('/')
def home():
     # Get the current second
    current_second = datetime.datetime.now().second
    # Determine which image to display based on the second
    image_index = current_second // 3  % 3  # We have 3 images, so use mod 3
    image_files = [
        'Image1.gif',
        'Image2.gif',
        'Image3.gif'
    ]
    current_image = image_files[image_index]
    return render_template('base1.html', page="home", current_image=current_image)

    '''image = images[int(time.time()) % len(images)]
     #return render_template_string(home_template, image=image)
    return render_template('base1.html', page="home",image=image)'''
    
@app.route('/overview')
def overview():
    return render_template('base1.html', page="overview")

@app.route('/courses')
def courses():        
    course_data = [
        {
            'title': 'Python',
            'location': 'Pune',
            'duration': '3 Months',
            'instructor': '3RI Expert',
            'description': 'In this high-octane technological world, the popularity of Python is increasing at a tremendous rate pairing up with lucrative career opportunities. Python is easy and a powerful language and to get your hands on experience in that, Technolearn Trainings can provide you with the coaching for a duration of 45 days. It is the best Python training institute in Karvenagar, Pune-India providing training to students from industrial IT top-notch Python mentors having proven work experience.',
            'image': 'python.gif'
        },
        {
            'title': 'Introduction To HTML',
            'location': 'Pune',
            'duration': '3 Months',
            'instructor': '3RI Expert',
            'description': 'This HTML course offers a comprehensive introduction to Hypertext Markup Language (HTML), the backbone of web development. Designed for beginners, the course covers the basics of HTML structure, elements, and attributes. You will learn how to create and format web pages, insert images, links, and tables, and understand the importance of semantic HTML for accessibility and SEO.By the end of the course, you will have the skills to build simple yet functional web pages and a solid foundation for further web development.',
            'image': 'html.gif'
        },
        {
            'title': 'C++ Programming',
            'location': 'Pune',
            'duration': '3 Months',
            'instructor': '3RI Expert',
            'description': 'This C++ course provides a thorough introduction to one of the most powerful and widely-used programming languages in software development. Perfect for beginners and those with some programming experience, the course covers fundamental concepts such as variables, data types, control structures, functions, and object-oriented programming (OOP) principles. You will learn to write efficient and maintainable code, understand memory management, and explore advanced topics like templates and the Standard Template Library (STL). By the end of the course, you will have the skills to develop robust applications and a strong foundation for further exploration of C++ and other programming languages.',
            'image': 'c.gif'
        },
        {
            'title': '.NET Programming',
            'location': 'Pune',
            'duration': '3 Months',
            'instructor': '3RI Expert',
            'description': 'This .NET course offers an in-depth introduction to the .NET framework, a versatile and powerful platform for building a wide range of applications. Suitable for beginners and those with some programming experience, the course covers essential concepts such as the .NET architecture, C# programming, and the development of Windows and web applications using ASP.NET. You will learn about object-oriented programming, debugging, and deployment processes, as well as working with databases using Entity Framework. By the end of the course, you will be equipped with the skills to create scalable, high-performance applications and a solid foundation for further .NET development.',
            'image': 'net.gif'
        },
        {
            'title': 'Data Science',
            'location': 'Pune',
            'duration': '3 Months',
            'instructor': '3RI Expert',
            'description': 'Over the last decade, the demand for Data Science professionals has surged in the industry and has revamped the intelligence thus offering thriving career in the areas of interests. So, let’s get started with the coaching in data science with python course (4 months) from Technolearn Trainings. It is the best Data Science with Python training institute in Swargate, Pune- India. The course will provide you with the knowledge of the concepts of Python programming along with learning of data analytics. After completing the Python Data Science Training , you will expertise the requisite tools in Data Science with Python.',
            'image': 'data_science.gif'
        },
        {
            'title': 'Machine Learning',
            'location': 'Pune',
            'duration': '3 Months',
            'instructor': '3RI Expert',
            'description': 'With the rapid growing demand of Artificial Intelligence and the AI-enabled services, machine learning is elevating as a high profile globally. Amidst the buzz of Big Data, enterprises are aware of the benefits of ML and so have started hiring for engineers and researchers. For a remunerative career in this, one must stay updated with the latest development requirements. You may want to enrol in machine learning course with python which is for 4 months! So, at your rescue, Technolearn which is the best machine learning training institute in Dhankawadi & Balajinagar in Pune has stepped up to provide extensive knowledgeable course and practical sessions related to it.',
            'image': 'machine_learning.gif'
        }
        
    ]
    read_more_title = request.args.get('read_more')
    return render_template('base1.html',page="courses", courses=course_data, read_more_title=read_more_title)

@app.route('/submit_enquiry', methods=['POST'])
def submit_enquiry():
    course_title = request.form.get('course_title')
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    # Here you can handle the form data, for example, save it to a database or send an email.
    # For demonstration purposes, we will just flash a success message.
    flash('Your enquiry has been submitted successfully!', 'success')
    
    return redirect(url_for('courses'))

@app.route('/faqs')
def faqs():
    return render_template('base1.html', page="faqs")

@app.route('/contact')
def contact():
    return render_template('base1.html', page="contact")

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    response, options = generate_response(user_message)
    return jsonify({'response': response, 'options': options})

def generate_response(user_message):
    global conversation_state

    user_message = user_message.lower()

    # Check if the user message matches any trigger option
    if user_message in ['hi', 'hello']:
        conversation_state['current_trigger'] = 'hello'
        return "Hello! How can I help you?", trigger_options['hello']

    # Handle the user message based on the current conversation state
    current_trigger = conversation_state.get('current_trigger')
    if current_trigger:
        if current_trigger == 'hello':
            if user_message in ['frontend', 'backend', 'fullstack']:
                conversation_state['current_trigger'] = user_message.capitalize()
                return f"You selected {user_message.capitalize()}. Here are your options:", trigger_options[user_message.capitalize()]
            else:
                return "I'm sorry, I didn't understand that. Please choose one of the options.", trigger_options['hello']
        elif current_trigger in ['Frontend', 'Backend', 'Fullstack']:
            if user_message.capitalize() in trigger_options[current_trigger]:
                return f"You selected {user_message}. Course details are available soon.", []
            else:
                return "I'm sorry, I didn't understand that. Please choose one of the options.", trigger_options[current_trigger]

    # Default response if no conditions are met
    return "I'm sorry, I didn't understand that.", []

if __name__ == '__main__':
    app.run(debug=True)



