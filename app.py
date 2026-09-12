from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "placementhub_secret_key"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="",
        database="placement_db"
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("home.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        role = request.form["role"]

        db = get_db_connection()
        cursor = db.cursor()

        try:

            query = """
            INSERT INTO users (name, email, password, role)
            VALUES (%s, %s, %s, %s)
            """

            cursor.execute(
                query,
                (name, email, password, role)
            )

            db.commit()

        except mysql.connector.IntegrityError:

            cursor.close()
            db.close()

            return "Email already registered. Please use another email."

        cursor.close()
        db.close()

        return redirect("/login")

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        query = """
        SELECT *
        FROM users
        WHERE email = %s AND password = %s
        """

        cursor.execute(
            query,
            (email, password)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user:

            session["user_id"] = user["id"]
            session["role"] = user["role"]

            if user["role"] == "recruiter":
                return redirect("/recruiter/dashboard")

            return redirect("/dashboard")

        return "Invalid email or password!"

    return render_template("login.html")


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "student":
        return redirect("/recruiter/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM applications
        WHERE student_id = %s
        """,
        (user_id,)
    )

    total_applications = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM applications
        WHERE student_id = %s
        AND status = 'Shortlisted'
        """,
        (user_id,)
    )

    shortlisted = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM interviews
        JOIN applications
            ON interviews.application_id = applications.id
        WHERE applications.student_id = %s
        AND interviews.status = 'Scheduled'
        """,
        (user_id,)
    )

    interviews = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM jobs
        """
    )

    total_jobs = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT
            jobs.*,
            companies.company_name
        FROM jobs
        JOIN companies
            ON jobs.company_id = companies.id
        ORDER BY jobs.created_at DESC
        LIMIT 5
        """
    )

    jobs = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            applications.status,
            jobs.title,
            companies.company_name
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.id
        JOIN companies
            ON jobs.company_id = companies.id
        WHERE applications.student_id = %s
        ORDER BY applications.applied_at DESC
        LIMIT 5
        """,
        (user_id,)
    )

    applications = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "dashboard.html",
        user=user,
        total_applications=total_applications,
        shortlisted=shortlisted,
        interviews=interviews,
        total_jobs=total_jobs,
        jobs=jobs,
        applications=applications
    )


# =========================================================
# STUDENT PROFILE
# =========================================================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "student":
        return redirect("/recruiter/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    if request.method == "POST":

        phone = request.form["phone"]
        course = request.form["course"]
        university = request.form["university"]
        graduation_year = request.form["graduation_year"]
        cgpa = request.form["cgpa"]
        skills = request.form["skills"]
        about_me = request.form["about_me"]
        resume = request.form["resume"]

        cursor.execute(
            """
            SELECT id
            FROM student_profiles
            WHERE user_id = %s
            """,
            (user_id,)
        )

        existing_profile = cursor.fetchone()

        if existing_profile:

            cursor.execute(
                """
                UPDATE student_profiles
                SET phone = %s,
                    course = %s,
                    university = %s,
                    graduation_year = %s,
                    cgpa = %s,
                    skills = %s,
                    about_me = %s,
                    resume = %s
                WHERE user_id = %s
                """,
                (
                    phone,
                    course,
                    university,
                    graduation_year or None,
                    cgpa or None,
                    skills,
                    about_me,
                    resume,
                    user_id
                )
            )

        else:

            cursor.execute(
                """
                INSERT INTO student_profiles
                (
                    user_id,
                    phone,
                    course,
                    university,
                    graduation_year,
                    cgpa,
                    skills,
                    about_me,
                    resume
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    phone,
                    course,
                    university,
                    graduation_year or None,
                    cgpa or None,
                    skills,
                    about_me,
                    resume
                )
            )

        db.commit()

        cursor.close()
        db.close()

        return redirect("/profile?success=1")

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.execute(
        """
        SELECT *
        FROM student_profiles
        WHERE user_id = %s
        """,
        (user_id,)
    )

    profile_data = cursor.fetchone()

    cursor.close()
    db.close()

    success = request.args.get("success") == "1"

    return render_template(
        "profile.html",
        user=user,
        profile=profile_data or {},
        success=success
    )


# =========================================================
# JOBS - STUDENT
# =========================================================

@app.route("/jobs")
def jobs():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "student":
        return redirect("/recruiter/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            jobs.*,
            companies.company_name
        FROM jobs
        JOIN companies
            ON jobs.company_id = companies.id
        ORDER BY jobs.created_at DESC
        """
    )

    jobs_data = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "jobs.html",
        user=user,
        jobs=jobs_data
    )


# =========================================================
# JOB DETAILS
# =========================================================

@app.route("/job/<int:job_id>")
def job_details(job_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "student":
        return redirect("/recruiter/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            jobs.*,
            companies.company_name,
            companies.website,
            companies.description AS company_description
        FROM jobs
        JOIN companies
            ON jobs.company_id = companies.id
        WHERE jobs.id = %s
        """,
        (job_id,)
    )

    job = cursor.fetchone()

    if not job:

        cursor.close()
        db.close()

        return "Job not found."

    cursor.execute(
        """
        SELECT
            id,
            status
        FROM applications
        WHERE student_id = %s
        AND job_id = %s
        """,
        (user_id, job_id)
    )

    application = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "job_details.html",
        user=user,
        job=job,
        application=application
    )


# =========================================================
# APPLY FOR JOB
# =========================================================

@app.route("/apply/<int:job_id>")
def apply_job(job_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "student":
        return redirect("/recruiter/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT
            id,
            status
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )

    job = cursor.fetchone()

    if not job:

        cursor.close()
        db.close()

        return "Job not found."

    if job["status"] == "Closed":

        cursor.close()
        db.close()

        return """
        <script>
            alert("This job is closed and is no longer accepting applications.");
            window.location.href = "/jobs";
        </script>
        """

    cursor.execute(
        """
        SELECT id
        FROM applications
        WHERE student_id = %s
        AND job_id = %s
        """,
        (user_id, job_id)
    )

    existing_application = cursor.fetchone()

    if existing_application:

        cursor.close()
        db.close()

        return "You have already applied for this job."

    cursor.execute(
        """
        INSERT INTO applications
        (
            student_id,
            job_id,
            status
        )
        VALUES
        (
            %s,
            %s,
            'Applied'
        )
        """,
        (user_id, job_id)
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect("/dashboard")


# =========================================================
# STUDENT APPLICATIONS
# =========================================================

@app.route("/applications")
def applications():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "student":
        return redirect("/recruiter/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            applications.id,
            applications.job_id,
            applications.status,
            applications.applied_at,
            jobs.title,
            jobs.location,
            jobs.salary,
            companies.company_name
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.id
        JOIN companies
            ON jobs.company_id = companies.id
        WHERE applications.student_id = %s
        ORDER BY applications.applied_at DESC
        """,
        (user_id,)
    )

    applications_data = cursor.fetchall()

    # Get latest interview for each application
    for application in applications_data:

        cursor.execute(
            """
            SELECT
                interview_date,
                interview_time,
                duration_minutes AS interview_duration,
                mode,
                location AS interview_location,
                meeting_link AS interview_link,
                notes AS interview_notes,
                status AS interview_status
            FROM interviews
            WHERE application_id = %s
            ORDER BY interview_date DESC,
                     interview_time DESC
            LIMIT 1
            """,
            (application["id"],)
        )

        interview = cursor.fetchone()

        if interview:

            application["interview_date"] = interview["interview_date"]
            application["interview_time"] = interview["interview_time"]
            application["interview_duration"] = interview["interview_duration"]
            application["mode"] = interview["mode"]
            application["interview_location"] = interview["interview_location"]
            application["interview_link"] = interview["interview_link"]
            application["interview_notes"] = interview["interview_notes"]
            application["interview_status"] = interview["interview_status"]

            # Format time as 12-hour format
            if interview["interview_time"]:

                total_seconds = interview["interview_time"].total_seconds()

                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)

                am_pm = "AM" if hours < 12 else "PM"

                display_hour = hours % 12

                if display_hour == 0:
                    display_hour = 12

                application["interview_time"] = (
                    f"{display_hour:02d}:{minutes:02d} {am_pm}"
                )

        else:

            application["interview_date"] = None
            application["interview_time"] = None
            application["interview_duration"] = None
            application["mode"] = None
            application["interview_location"] = None
            application["interview_link"] = None
            application["interview_notes"] = None
            application["interview_status"] = None

    cursor.close()
    db.close()

    return render_template(
        "applications.html",
        user=user,
        applications=applications_data
    )


# =========================================================
# RECRUITER DASHBOARD
# =========================================================

@app.route("/recruiter/dashboard")
def recruiter_dashboard():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    jobs_count = 0
    applications_count = 0
    shortlisted_count = 0
    interviews_count = 0
    upcoming_interviews = []

    if company:

        company_id = company["id"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM jobs
            WHERE company_id = %s
            """,
            (company_id,)
        )

        jobs_count = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM applications
            JOIN jobs
                ON applications.job_id = jobs.id
            WHERE jobs.company_id = %s
            """,
            (company_id,)
        )

        applications_count = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM applications
            JOIN jobs
                ON applications.job_id = jobs.id
            WHERE jobs.company_id = %s
            AND applications.status = 'Shortlisted'
            """,
            (company_id,)
        )

        shortlisted_count = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM interviews
            JOIN applications
                ON interviews.application_id = applications.id
            JOIN jobs
                ON applications.job_id = jobs.id
            WHERE jobs.company_id = %s
            AND interviews.status = 'Scheduled'
            """,
            (company_id,)
        )

        interviews_count = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT
                interviews.id AS interview_id,
                interviews.application_id,
                interviews.interview_date,
                interviews.interview_time,
                interviews.duration_minutes,
                interviews.mode,
                interviews.location,
                interviews.meeting_link,
                interviews.notes,
                interviews.status,
                users.name AS student_name,
                jobs.title AS job_title
            FROM interviews
            JOIN applications
                ON interviews.application_id = applications.id
            JOIN users
                ON applications.student_id = users.id
            JOIN jobs
                ON applications.job_id = jobs.id
            WHERE jobs.company_id = %s
            AND interviews.status = 'Scheduled'
            ORDER BY
                interviews.interview_date ASC,
                interviews.interview_time ASC
            LIMIT 5
            """,
            (company_id,)
        )

        upcoming_interviews = cursor.fetchall()

        for interview in upcoming_interviews:

            if interview["interview_time"]:

                total_seconds = interview["interview_time"].total_seconds()

                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)

                am_pm = "AM" if hours < 12 else "PM"

                display_hour = hours % 12

                if display_hour == 0:
                    display_hour = 12

                interview["formatted_time"] = (
                    f"{display_hour:02d}:{minutes:02d} {am_pm}"
                )

    cursor.close()
    db.close()

    return render_template(
        "recruiter_dashboard.html",
        user=user,
        company=company,
        jobs_count=jobs_count,
        applications_count=applications_count,
        shortlisted_count=shortlisted_count,
        interviews_count=interviews_count,
        upcoming_interviews=upcoming_interviews
    )


# =========================================================
# RECRUITER COMPANY PROFILE
# =========================================================

@app.route("/recruiter/company", methods=["GET", "POST"])
def recruiter_company():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if request.method == "POST":

        company_name = request.form["company_name"]
        website = request.form["website"]
        location = request.form["location"]
        description = request.form["description"]

        if company:

            cursor.execute(
                """
                UPDATE companies
                SET company_name = %s,
                    website = %s,
                    location = %s,
                    description = %s
                WHERE id = %s
                """,
                (
                    company_name,
                    website,
                    location,
                    description,
                    company["id"]
                )
            )

        else:

            cursor.execute(
                """
                INSERT INTO companies
                (
                    user_id,
                    company_name,
                    website,
                    location,
                    description
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    company_name,
                    website,
                    location,
                    description
                )
            )

        db.commit()

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.close()
    db.close()

    return render_template(
        "recruiter_company.html",
        company=company
    )


# =========================================================
# RECRUITER MANAGE JOBS
# =========================================================

@app.route("/recruiter/jobs")
def recruiter_jobs():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    jobs = []

    if company:

        cursor.execute(
            """
            SELECT *
            FROM jobs
            WHERE company_id = %s
            ORDER BY created_at DESC
            """,
            (company["id"],)
        )

        jobs = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "recruiter_jobs.html",
        company=company,
        jobs=jobs
    )


# =========================================================
# RECRUITER APPLICANTS
# =========================================================

@app.route("/recruiter/applicants")
def recruiter_applicants():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    applicants = []

    if company:

        cursor.execute(
            """
            SELECT
                applications.id AS application_id,
                applications.status,
                applications.applied_at,
                users.id AS student_id,
                users.name AS student_name,
                users.email,
                jobs.id AS job_id,
                jobs.title AS job_title
            FROM applications
            JOIN users
                ON applications.student_id = users.id
            JOIN jobs
                ON applications.job_id = jobs.id
            WHERE jobs.company_id = %s
            ORDER BY applications.applied_at DESC
            """,
            (company["id"],)
        )

        applicants = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "recruiter_applicants.html",
        company=company,
        applicants=applicants
    )


# =========================================================
# APPLICANT PROFILE
# =========================================================

@app.route("/recruiter/applicant/<int:application_id>")
def applicant_profile(application_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.execute(
        """
        SELECT
            applications.id AS application_id,
            applications.status,
            applications.applied_at,
            users.id AS student_id,
            users.name,
            users.email,
            student_profiles.phone,
            student_profiles.course,
            student_profiles.university,
            student_profiles.graduation_year,
            student_profiles.cgpa,
            student_profiles.skills,
            student_profiles.about_me,
            student_profiles.resume,
            jobs.title AS job_title
        FROM applications
        JOIN users
            ON applications.student_id = users.id
        JOIN jobs
            ON applications.job_id = jobs.id
        LEFT JOIN student_profiles
            ON users.id = student_profiles.user_id
        WHERE applications.id = %s
        AND jobs.company_id = %s
        """,
        (
            application_id,
            company["id"]
        )
    )

    applicant = cursor.fetchone()

    if not applicant:

        cursor.close()
        db.close()

        return "Applicant not found."

    cursor.execute(
        """
        SELECT *
        FROM interviews
        WHERE application_id = %s
        ORDER BY interview_date DESC,
                 interview_time DESC
        LIMIT 1
        """,
        (application_id,)
    )

    interview = cursor.fetchone()

    if interview and interview["interview_time"]:

        total_seconds = interview["interview_time"].total_seconds()

        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)

        am_pm = "AM" if hours < 12 else "PM"

        display_hour = hours % 12

        if display_hour == 0:
            display_hour = 12

        interview["formatted_time"] = (
            f"{display_hour:02d}:{minutes:02d} {am_pm}"
        )

    cursor.close()
    db.close()

    return render_template(
        "applicant_profile.html",
        company=company,
        applicant=applicant,
        interview=interview
    )


# =========================================================
# RESCHEDULE INTERVIEW
# =========================================================

@app.route(
    "/recruiter/interview/reschedule/<int:interview_id>",
    methods=["GET", "POST"]
)
def reschedule_interview(interview_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.execute(
        """
        SELECT
            interviews.id,
            interviews.application_id,
            interviews.interview_date,
            interviews.interview_time,
            interviews.duration_minutes,
            interviews.mode,
            interviews.location,
            interviews.meeting_link,
            interviews.notes,
            interviews.status
        FROM interviews
        JOIN applications
            ON interviews.application_id = applications.id
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE interviews.id = %s
        AND jobs.company_id = %s
        """,
        (interview_id, company["id"])
    )

    interview = cursor.fetchone()

    if not interview:

        cursor.close()
        db.close()

        return "Interview not found."

    if interview["status"] != "Scheduled":

        cursor.close()
        db.close()

        return "Only scheduled interviews can be rescheduled."

    if request.method == "POST":

        interview_date = request.form.get("interview_date")
        interview_time = request.form.get("interview_time")
        duration_minutes = request.form.get("duration_minutes")
        mode = request.form.get("mode")
        location = request.form.get("location")
        meeting_link = request.form.get("meeting_link")
        notes = request.form.get("notes")

        if not interview_date or not interview_time:

            cursor.close()
            db.close()

            return "Interview date and time are required."

        if not duration_minutes:
            duration_minutes = 30

        cursor.execute(
            """
            UPDATE interviews
            SET
                interview_date = %s,
                interview_time = %s,
                duration_minutes = %s,
                mode = %s,
                location = %s,
                meeting_link = %s,
                notes = %s
            WHERE id = %s
            """,
            (
                interview_date,
                interview_time,
                int(duration_minutes),
                mode,
                location,
                meeting_link,
                notes,
                interview_id
            )
        )

        db.commit()

        application_id = interview["application_id"]

        cursor.close()
        db.close()

        return redirect(
            f"/recruiter/applicant/{application_id}"
        )

    cursor.close()
    db.close()

    return render_template(
        "reschedule_interview.html",
        interview=interview
    )


# =========================================================
# CANCEL INTERVIEW
# =========================================================

@app.route("/recruiter/interview/cancel/<int:interview_id>")
def cancel_interview(interview_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.execute(
        """
        SELECT
            interviews.id,
            interviews.application_id,
            interviews.status
        FROM interviews
        JOIN applications
            ON interviews.application_id = applications.id
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE interviews.id = %s
        AND jobs.company_id = %s
        """,
        (interview_id, company["id"])
    )

    interview = cursor.fetchone()

    if not interview:

        cursor.close()
        db.close()

        return "Interview not found."

    if interview["status"] != "Scheduled":

        cursor.close()
        db.close()

        return "Only scheduled interviews can be cancelled."

    cursor.execute(
        """
        UPDATE interviews
        SET status = 'Cancelled'
        WHERE id = %s
        """,
        (interview_id,)
    )

    db.commit()

    application_id = interview["application_id"]

    cursor.close()
    db.close()

    return redirect(
        f"/recruiter/applicant/{application_id}"
    )


# =========================================================
# COMPLETE INTERVIEW
# =========================================================

@app.route("/recruiter/interview/complete/<int:interview_id>")
def complete_interview(interview_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.execute(
        """
        SELECT
            interviews.id,
            interviews.application_id,
            interviews.status
        FROM interviews
        JOIN applications
            ON interviews.application_id = applications.id
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE interviews.id = %s
        AND jobs.company_id = %s
        """,
        (interview_id, company["id"])
    )

    interview = cursor.fetchone()

    if not interview:

        cursor.close()
        db.close()

        return "Interview not found."

    if interview["status"] != "Scheduled":

        cursor.close()
        db.close()

        return "Only scheduled interviews can be marked as completed."

    cursor.execute(
        """
        UPDATE interviews
        SET status = 'Completed'
        WHERE id = %s
        """,
        (interview_id,)
    )

    db.commit()

    application_id = interview["application_id"]

    cursor.close()
    db.close()

    return redirect(
        f"/recruiter/applicant/{application_id}"
    )


# =========================================================
# SCHEDULE INTERVIEW
# =========================================================

@app.route(
    "/recruiter/interview/schedule/<int:application_id>",
    methods=["GET", "POST"]
)
def schedule_interview(application_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.execute(
        """
        SELECT
            applications.id AS application_id,
            applications.status,
            users.name AS student_name,
            jobs.title AS job_title
        FROM applications
        JOIN users
            ON applications.student_id = users.id
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE applications.id = %s
        AND jobs.company_id = %s
        """,
        (application_id, company["id"])
    )

    application = cursor.fetchone()

    if not application:

        cursor.close()
        db.close()

        return "Application not found."

    if request.method == "POST":

        interview_date = request.form.get("interview_date")
        interview_time = request.form.get("interview_time")
        duration_minutes = request.form.get("duration_minutes")
        mode = request.form.get("mode")
        meeting_link = request.form.get("meeting_link")
        location = request.form.get("location")
        notes = request.form.get("notes")

        if not interview_date or not interview_time:

            cursor.close()
            db.close()

            return "Interview date and time are required."

        if not duration_minutes:
            duration_minutes = 30

        cursor.execute(
            """
            SELECT id
            FROM interviews
            WHERE application_id = %s
            AND status = 'Scheduled'
            LIMIT 1
            """,
            (application_id,)
        )

        existing_interview = cursor.fetchone()

        if existing_interview:

            cursor.close()
            db.close()

            return "An interview is already scheduled for this candidate."

        cursor.execute(
            """
            INSERT INTO interviews
            (
                application_id,
                interview_date,
                interview_time,
                duration_minutes,
                mode,
                meeting_link,
                location,
                notes,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Scheduled')
            """,
            (
                application_id,
                interview_date,
                interview_time,
                int(duration_minutes),
                mode,
                meeting_link,
                location,
                notes
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            f"/recruiter/applicant/{application_id}"
        )

    cursor.close()
    db.close()

    return render_template(
        "schedule_interview.html",
        company=company,
        application=application
    )


# =========================================================
# UPDATE APPLICATION STATUS
# =========================================================

@app.route(
    "/recruiter/application/<int:application_id>/<status>"
)
def update_application_status(application_id, status):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    allowed_statuses = [
        "Shortlisted",
        "Rejected",
        "Selected"
    ]

    if status not in allowed_statuses:
        return "Invalid application status."

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.execute(
        """
        SELECT applications.id
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE applications.id = %s
        AND jobs.company_id = %s
        """,
        (
            application_id,
            company["id"]
        )
    )

    application = cursor.fetchone()

    if not application:

        cursor.close()
        db.close()

        return "Application not found."

    cursor.execute(
        """
        UPDATE applications
        SET status = %s
        WHERE id = %s
        """,
        (
            status,
            application_id
        )
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect(
        f"/recruiter/applicant/{application_id}"
    )


# =========================================================
# CREATE JOB
# =========================================================

@app.route(
    "/recruiter/jobs/create",
    methods=["GET", "POST"]
)
def create_job():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        location = request.form["location"]
        salary = request.form["salary"]
        eligibility = request.form["eligibility"]
        skills_required = request.form["skills_required"]
        deadline = request.form["deadline"]

        cursor.execute(
            """
            INSERT INTO jobs
            (
                company_id,
                title,
                description,
                location,
                salary,
                eligibility,
                skills_required,
                deadline
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                company["id"],
                title,
                description,
                location,
                salary,
                eligibility,
                skills_required,
                deadline
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect("/recruiter/jobs")

    cursor.close()
    db.close()

    return render_template(
        "create_job.html",
        company=company
    )


# =========================================================
# EDIT JOB
# =========================================================

@app.route(
    "/recruiter/jobs/edit/<int:job_id>",
    methods=["GET", "POST"]
)
def edit_job(job_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = %s
        AND company_id = %s
        """,
        (
            job_id,
            company["id"]
        )
    )

    job = cursor.fetchone()

    if not job:

        cursor.close()
        db.close()

        return redirect("/recruiter/jobs")

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        location = request.form["location"]
        salary = request.form["salary"]
        eligibility = request.form["eligibility"]
        skills_required = request.form["skills_required"]
        deadline = request.form["deadline"]

        cursor.execute(
            """
            UPDATE jobs
            SET
                title = %s,
                description = %s,
                location = %s,
                salary = %s,
                eligibility = %s,
                skills_required = %s,
                deadline = %s
            WHERE id = %s
            AND company_id = %s
            """,
            (
                title,
                description,
                location,
                salary,
                eligibility,
                skills_required,
                deadline,
                job_id,
                company["id"]
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect("/recruiter/jobs")

    cursor.close()
    db.close()

    return render_template(
        "edit_job.html",
        company=company,
        job=job
    )


# =========================================================
# DELETE JOB
# =========================================================

@app.route(
    "/recruiter/jobs/delete/<int:job_id>",
    methods=["POST"]
)
def delete_job(job_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = %s
        AND company_id = %s
        """,
        (
            job_id,
            company["id"]
        )
    )

    job = cursor.fetchone()

    if not job:

        cursor.close()
        db.close()

        return redirect("/recruiter/jobs")

    cursor.execute(
        """
        SELECT COUNT(*) AS application_count
        FROM applications
        WHERE job_id = %s
        """,
        (job_id,)
    )

    result = cursor.fetchone()

    if result["application_count"] > 0:

        cursor.close()
        db.close()

        return """
        <script>
            alert("This job cannot be deleted because students have already applied.");
            window.location.href = "/recruiter/jobs";
        </script>
        """

    cursor.execute(
        """
        DELETE FROM jobs
        WHERE id = %s
        AND company_id = %s
        """,
        (
            job_id,
            company["id"]
        )
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect("/recruiter/jobs")


# =========================================================
# CLOSE JOB
# =========================================================

@app.route(
    "/recruiter/jobs/close/<int:job_id>",
    methods=["POST"]
)
def close_job(job_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "recruiter":
        return redirect("/dashboard")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = session["user_id"]

    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    company = cursor.fetchone()

    if not company:

        cursor.close()
        db.close()

        return redirect("/recruiter/company")

    cursor.execute(
        """
        UPDATE jobs
        SET status = 'Closed'
        WHERE id = %s
        AND company_id = %s
        """,
        (
            job_id,
            company["id"]
        )
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect("/recruiter/jobs")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5001
    )
