from flask import Flask, request, render_template, redirect, url_for, session
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

app = Flask(__name__)
app.secret_key = ''
email = ""
password = ""
file_path = ""

def init_db():
    conn = sqlite3.connect("email_entries.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            company TEXT,
            recruiter_name TEXT,
            recruiter_email TEXT,
            starred BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

templates = [
    {
        'title': 'Follow-Up Email',
        'subject': 'Following Up on {company} SWE Internship Application',
        'content': """Hi {recruiter_name},

I wanted to follow up on my application for the {company} SWE internship. I'm very interested in the opportunity and would appreciate any updates on the process.

Thank you for considering my application!

Best,
Amogh
https://www.linkedin.com/in/amoghdhumal/"""
    },
    {
        'title': 'Introduction Email',
        'subject': 'Introduction Regarding {company} SWE Internship',
        'content': """Hi {recruiter_name},

My name is Amogh, a Junior studying CS at the University of Washington. I recently applied for the {company} SWE Internship and would love the opportunity to connect.

Thanks for your time!

Best,
Amogh
https://www.linkedin.com/in/amoghdhumal/"""
    },
    {
        'title': 'Networking Email',
        'subject': 'Interest in {company} Opportunities',
        'content': """Hi {recruiter_name},

I hope you're doing well. I am very interested in {company} and would love to learn more about opportunities to connect or collaborate.

Looking forward to connecting!

Best,
Amogh
https://www.linkedin.com/in/amoghdhumal/"""
    }
]

@app.route('/', methods=['GET', 'POST'])
def send_email():
    message = None
    prompt = request.args.get('prompt', "")
    subject = request.args.get('subject', "")

    if not prompt:
        prompt = templates[0]['content']
    if not subject:
        subject = templates[0]['subject']

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'preview':
            company = request.form['company']
            recruiter_names = request.form.getlist('recruiter_name')
            receiver_emails = request.form.getlist('recruiter_email')
            custom_prompt = request.form['prompt']
            subject = request.form['subject']

            session['email_data'] = {
                'company': company,
                'recruiter_names': recruiter_names,
                'receiver_emails': receiver_emails,
                'prompt': custom_prompt,
                'subject': subject
            }
            recipient_emails = [email.strip() for email in receiver_emails]
            to_field = ', '.join(recipient_emails)
            email_subject = subject.format(company=company)
            message_content = custom_prompt.replace('{recruiter_name}', '[recruiter_name]').format(company=company)

            preview_email = {
                'to': to_field,
                'subject': email_subject,
                'content': message_content
            }

            return render_template('preview.html', preview=preview_email)
        elif action == 'send':
            email_data = session.get('email_data')
            if not email_data:
                message = "No email data found in session."
                return render_template('email_form.html', message=message, success=False, prompt=prompt, subject=subject)

            company = email_data['company']
            recruiter_names = email_data['recruiter_names']
            receiver_emails = email_data['receiver_emails']
            custom_prompt = email_data['prompt']
            subject = email_data['subject']

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()

            try:
                server.login(email, password)
                conn = sqlite3.connect("email_entries.db")
                cursor = conn.cursor()
                for recruiter_name, receiver_email in zip(recruiter_names, receiver_emails):
                    recruiter_name = recruiter_name.strip()
                    receiver_email = receiver_email.strip()

                    first_name = recruiter_name.split()[0] if recruiter_name else recruiter_name
                    message_content = custom_prompt.format(recruiter_name=first_name, company=company)
                    email_subject = subject.format(company=company)

                    msg = MIMEMultipart()
                    msg['From'] = email
                    msg['To'] = receiver_email
                    msg['Subject'] = email_subject
                    msg.attach(MIMEText(message_content, 'plain'))

                    with open(file_path, "rb") as attachment:
                        part = MIMEApplication(attachment.read(), _subtype="pdf")
                        part.add_header('Content-Disposition', 'attachment', filename=file_path.split("/")[-1])
                        msg.attach(part)

                    server.sendmail(email, receiver_email, msg.as_string())
                    cursor.execute("INSERT INTO entries (company, recruiter_name, recruiter_email) VALUES (?, ?, ?)",
                                   (company, recruiter_name, receiver_email))
                conn.commit()
                conn.close()

                message = "Emails with attachments have been sent successfully."
                session.pop('email_data', None)
                return render_template('email_form.html', message=message, success=True, prompt=custom_prompt, subject=subject)
            except Exception as e:
                message = f"An error occurred: {e}"
                return render_template('email_form.html', message=message, success=False, prompt=custom_prompt, subject=subject)
            finally:
                server.quit()
    return render_template('email_form.html', message=message, prompt=prompt, subject=subject)

@app.route('/results')
def view_results():
    conn = sqlite3.connect("email_entries.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, company, recruiter_name, recruiter_email, starred FROM entries")
    entries = cursor.fetchall()
    conn.close()
    return render_template('results.html', entries=entries)

@app.route('/toggle_star/<int:entry_id>')
def toggle_star(entry_id):
    conn = sqlite3.connect("email_entries.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE entries SET starred = NOT starred WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_results'))

@app.route('/delete_entry/<int:entry_id>', methods=['GET'])
def delete_entry(entry_id):
    conn = sqlite3.connect("email_entries.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_results'))

@app.route('/add_manual_entry', methods=['POST'])
def add_manual_entry():
    company = request.form['company']
    recruiter_name = request.form['recruiter_name']
    recruiter_email = request.form['recruiter_email']

    conn = sqlite3.connect("email_entries.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO entries (company, recruiter_name, recruiter_email) VALUES (?, ?, ?)",
                   (company, recruiter_name, recruiter_email))
    conn.commit()
    conn.close()
    return redirect(url_for('view_results'))

@app.route('/edit_entry', methods=['POST'])
def edit_entry():
    entry_id = request.form['entry_id']
    company = request.form['company']
    recruiter_name = request.form['recruiter_name']
    recruiter_email = request.form['recruiter_email']

    conn = sqlite3.connect("email_entries.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE entries
        SET company = ?, recruiter_name = ?, recruiter_email = ?
        WHERE id = ?
    """, (company, recruiter_name, recruiter_email, entry_id))
    conn.commit()
    conn.close()

    return redirect(url_for('view_results'))

@app.route('/templates')
def templates_page():
    return render_template('templates.html', templates=templates)

if __name__ == '__main__':
    app.run()
