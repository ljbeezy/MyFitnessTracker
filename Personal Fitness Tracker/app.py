from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt
import mysql.connector
from datetime import datetime
import io
import base64
import matplotlib.pyplot as plt
import random

app = Flask(__name__)
app.secret_key = 'ballsmclongass'  # Change this to a secure key


def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Ljb49602.",
        database="personal fitness tracker"
    )

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = connect_to_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT UserID, Name, Email, PasswordHash, user_role FROM users WHERE Email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user["PasswordHash"].encode('utf-8')):
            session['userid'] = user["UserID"]
            session['user_name'] = user["Name"]

            if user["user_role"] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid email or password.")

    return render_template('login.html')


# Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        age = request.form['age']
        height = request.form['height']
        weight = request.form['weight']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        db = connect_to_db()
        cursor = db.cursor()

        # Check if the email already exists in the database
        cursor.execute("SELECT Email FROM users WHERE Email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            return render_template('register.html', error="Email already in database, try logging in instead.")
        
        # Insert user into the 'users' table if email is not taken
        cursor.execute("INSERT INTO users (Name, Email, PasswordHash) VALUES (%s, %s, %s)", 
                       (name, email, hashed_password.decode('utf-8')))
        
        # Get the UserID of the newly inserted user (use cursor.lastrowid)
        UserID = cursor.lastrowid
        
        # Insert the user's profile into the 'userprofile' table
        cursor.execute("INSERT INTO userprofile (UserID, Age, Height, Weight) VALUES (%s, %s, %s, %s)", 
                       (UserID, age, height, weight))
        
        # Commit changes to the database
        db.commit()

        cursor.close()
        db.close()

        return redirect(url_for('login'))

    return render_template('register.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'userid' not in session:
        return redirect(url_for('login'))

    # Fetch user details from the database to display in the dashboard
    UserID = session['userid']
    db = connect_to_db()
    cursor = db.cursor()

    cursor.execute("SELECT name, email FROM users WHERE UserID = %s", (UserID,))
    user = cursor.fetchone()

    cursor.execute("SELECT Age, Height, Weight FROM userprofile WHERE UserID = %s", (UserID,))
    user_profile = cursor.fetchone()

    cursor.close()
    db.close()

    if user and user_profile:
        return render_template('userDashboard.html', 
                               user_name=user[0], 
                               user_email=user[1],
                               user_age=user_profile[0],
                               user_height=user_profile[1], 
                               user_weight=user_profile[2])

    # Handle case where user or profile data is missing
    return redirect(url_for('login'))

@app.route('/editProfile', methods=['GET', 'POST'])
def edit_profile():
    if 'userid' not in session:
        return redirect(url_for('login'))

    UserID = session['userid']

    # Fetch current user details from the database
    db = connect_to_db()
    cursor = db.cursor()
    cursor.execute("SELECT name, email FROM users WHERE UserID = %s", (UserID,))
    user = cursor.fetchone()

    cursor.execute("SELECT Age, Height, Height FROM userprofile WHERE UserID = %s", (UserID,))
    user_profile = cursor.fetchone()
    cursor.close()

    if request.method == 'POST':
        new_name = request.form['name'] if request.form['name'] else user[0]
        new_email = request.form['email'] if request.form['email'] else user[1]
        new_weight = request.form['weight'] if request.form['weight'] else user_profile[2]
        new_age = request.form['age'] if request.form['age'] else user_profile[0]
        new_height = request.form['height'] if request.form['height'] else user_profile[1]

        db = connect_to_db()
        cursor = db.cursor()

        # Check if the new email already exists for another user
        cursor.execute("SELECT UserID FROM users WHERE email = %s AND UserID != %s", (new_email, UserID))
        existing_email = cursor.fetchone()

        if existing_email:
            # Email is already in use, return to dashboard with an error message
            cursor.close()
            db.close()
            flash("This email is already in use. Please choose another one.", "error")
            return redirect(url_for('dashboard'))  # Redirect back to dashboard

        # Update user details if email is unique
        update_query1 = "UPDATE users SET name = %s, email = %s WHERE UserID = %s"
        cursor.execute(update_query1, (new_name, new_email, UserID))

        # Update weight, age, and height in userprofile
        update_query2 = "UPDATE userprofile SET weight = %s, age = %s, height = %s WHERE UserID = %s"
        cursor.execute(update_query2, (new_weight, new_age, new_height, UserID))

        db.commit()
        cursor.close()
        db.close()

        flash("Profile updated successfully.", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_profile.html', user=user, user_profile=user_profile)



@app.route('/log_workout', methods=['GET', 'POST'])
def log_workout():
    if request.method == 'POST':
        workout_id = request.form.get('WorkoutID')

        db = connect_to_db()
        cursor = db.cursor(dictionary=True)

        # If WorkoutID is provided, fetch its details
        if workout_id:
            cursor.execute("SELECT ExerciseType, Duration, CaloriesBurned FROM workout WHERE WorkoutID = %s", (workout_id,))
            existing_workout = cursor.fetchone()

            if existing_workout:
                exercise_type = existing_workout['ExerciseType']
                duration = existing_workout['Duration']
                calories = existing_workout['CaloriesBurned']
            else:
                return render_template('log_workout.html', error="Invalid Workout ID.")
        else:
            # Get user input if no WorkoutID is provided
            exercise_type = request.form.get('exercise')
            duration = request.form.get('duration')
            calories = request.form.get('calories')

        # Insert new workout record
        workout_date = request.form.get('WorkoutDate')
        user_id = session.get('userid')

        cursor.execute("INSERT INTO workout (UserID, ExerciseType, Duration, CaloriesBurned, WorkoutDate) VALUES (%s, %s, %s, %s, %s)",
                       (user_id, exercise_type, duration, calories, workout_date))

        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for('dashboard'))

    return render_template('log_workout.html')

@app.route('/logMeal', methods=['GET', 'POST'])
def log_meal():
    if request.method == 'POST':
        MealID = request.form.get('MealID')

        db = connect_to_db()
        cursor = db.cursor(dictionary=True)

        # If MealID is provided, fetch its details
        if MealID:
            cursor.execute("SELECT FoodItems, Calories, Nutrients FROM meal WHERE MealID = %s", (MealID,))
            existing_meal = cursor.fetchone()

            if existing_meal:
                FoodItems = existing_meal['FoodItems']
                Calories = existing_meal['Calories']
                Nutrients = existing_meal['Nutrients']
            else:
                return render_template('log_meal.html', error="Invalid Meal ID.")
        else:
            # Get user input if no WorkoutID is provided
            FoodItems = request.form.get('FoodItems')
            Calories = request.form.get('Calories')
            Nutrients = request.form.get('Nutrients')

        # Insert new workout record
        MealDate = request.form.get('MealDate')
        user_id = session.get('userid')

        cursor.execute("INSERT INTO meal (UserID, FoodItems, Calories, Nutrients, MealDate) VALUES (%s, %s, %s, %s, %s)",
                       (user_id, FoodItems, Calories, Nutrients, MealDate))

        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for('dashboard'))

    return render_template('log_meal.html')


@app.route('/view_workouts', methods=['GET'])
def view_workouts():
    if 'userid' not in session:
        return redirect(url_for('login'))
    
    UserID = session['userid']
    user_name = session.get('user_name')
    db = connect_to_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT WorkoutDate, ExerciseType, Duration, CaloriesBurned, WorkoutID FROM workout WHERE UserID = %s", (UserID,))
    workouts = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template('viewWorkouts.html', workouts=workouts, user_name=user_name)

@app.route('/view_meals', methods=['GET'])
def view_meals():
    if 'userid' not in session:
        return redirect(url_for('login'))
    
    UserID = session['userid']
    user_name = session.get('user_name')
    db = connect_to_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT MealDate, FoodItems, Calories, MealID FROM meal WHERE UserID = %s", (UserID,))
    meals = cursor.fetchall()
    
    cursor.close()
    db.close()
    return render_template('viewMeals.html', meals=meals, user_name=user_name)

@app.route('/setGoals', methods=['GET', 'POST'])
def set_goals():
    if 'userid' not in session:
        return redirect(url_for('login'))
    
    UserID = session['userid']
    
    if request.method == 'POST':
        db = connect_to_db()
        cursor = db.cursor()

        # Get the goal data from the form
        target_weight = request.form['TargetWeight']
        deadline = request.form['Deadline']

        # Check if the deadline is in the past
        current_date = datetime.today().strftime('%Y-%m-%d')
        if deadline < current_date:
            return render_template('set_goals.html', error="Deadline cannot be in the past")

        # Insert new goal with creation date (no update query)
        cursor.execute("""
            INSERT INTO goal (UserID, targetWeight, deadline, goalCreationDate)
            VALUES (%s, %s, %s, %s)
        """, (UserID, target_weight, deadline, current_date))

        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for('view_goals'))  # Redirect to view goals page
    
    return render_template('set_goals.html')


@app.route('/viewGoals', methods=['GET'])
def view_goals():
    if 'userid' not in session:
        return redirect(url_for('login'))
    
    UserID = session['userid']
    
    db = connect_to_db()
    cursor = db.cursor()

    # Get the user's goal details (target weight, deadline, goal creation date)
    cursor.execute("SELECT TargetWeight, Deadline, GoalCreationDate FROM goal WHERE UserID = %s", (UserID,))
    goals = cursor.fetchall()  # Using fetchall to retrieve multiple goals for the user

    if goals:
        user_profile = None
        cursor.execute("SELECT weight FROM userprofile WHERE UserID = %s", (UserID,))
        user_profile = cursor.fetchone()

        # Get all goals and calculate progress for each
        goal_progress = []
        for goal in goals:
            target_weight = goal[0]
            deadline = goal[1]
            goal_creation_date = goal[2]

            # Calculate total calories consumed and burned within the goal's timeframe
            cursor.execute("""
                SELECT SUM(calories) 
                FROM meal
                WHERE UserID = %s AND MealDate BETWEEN %s AND %s
            """, (UserID, goal_creation_date, deadline))
            total_calories_consumed = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT SUM(CaloriesBurned) FROM workout
                WHERE UserID = %s AND workoutDate BETWEEN %s AND %s
            """, (UserID, goal_creation_date, deadline))
            total_calories_burned = cursor.fetchone()[0] or 0

            current_weight = user_profile[0] if user_profile else 0
            achieved_goal = current_weight <= target_weight
            net_calories = total_calories_consumed - total_calories_burned
            goal_status = "Achieved" if achieved_goal else "Not Achieved"

            goal_progress.append({
                'target_weight': target_weight,
                'deadline': deadline,
                'goal_creation_date': goal_creation_date,
                'current_weight': current_weight,
                'total_calories_consumed': total_calories_consumed,
                'total_calories_burned': total_calories_burned,
                'net_calories': net_calories,
                'goal_status': goal_status
            })

        cursor.close()
        db.close()

        return render_template('view_goals.html', goals=goal_progress)

    else:
        cursor.close()
        db.close()
        return render_template('view_goals.html', goals=None)

@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    if 'userid' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = connect_to_db()
        cursor = db.cursor()
        
        # Fetch user details for authentication
        cursor.execute("SELECT UserID, PasswordHash FROM users WHERE Email = %s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):  
            UserID = user[0]

            # Delete associated data
            cursor.execute("DELETE FROM userprofile WHERE UserID = %s", (UserID,))
            cursor.execute("DELETE FROM workout WHERE UserID = %s", (UserID,))
            cursor.execute("DELETE FROM meal WHERE UserID = %s", (UserID,))
            cursor.execute("DELETE FROM users WHERE UserID = %s", (UserID,))

            db.commit()
            cursor.close()
            db.close()

            session.clear()
            flash("Account deleted successfully.", "success")
            return redirect(url_for('login'))
        else:
            cursor.close()
            db.close()
            flash("Invalid email or password.", "danger")
            return render_template('delete_account.html', error="Invalid email or password.")

    return render_template('delete_account.html')

# Logout
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

#Admin Stuff
@app.route('/AdminDashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'userid' not in session:
        return redirect(url_for('login'))

    return render_template('adminDashboard.html')  # No users data passed

@app.route('/view_users')
def view_users():
    if 'userid' not in session:
        return redirect(url_for('login'))

    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    # Fetch user details
    cursor.execute("""
        SELECT u.UserID, u.Name, u.Email, u.PasswordHash, up.Age, up.Height, up.Weight,
               (SELECT COUNT(*) FROM meal WHERE meal.UserID = u.UserID) AS MealsLogged,
               (SELECT COUNT(*) FROM workout WHERE workout.UserID = u.UserID) AS WorkoutsLogged,
               (SELECT COUNT(*) FROM goal WHERE goal.UserID = u.UserID) AS GoalsSet
        FROM users u
        LEFT JOIN userprofile up ON u.UserID = up.UserID
        WHERE u.user_role != 'admin'  -- Exclude admin users
    """)
    users = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('viewUsers.html', users=users)

@app.route('/delete_user', methods=['POST'])
def delete_user():
    if 'userid' not in session:
        return redirect(url_for('login'))

    user_id = request.form.get('user_id')

    db = connect_to_db()
    cursor = db.cursor()

    # Delete associated records before deleting the user
    cursor.execute("DELETE FROM userprofile WHERE UserID = %s", (user_id,))
    cursor.execute("DELETE FROM workout WHERE UserID = %s", (user_id,))
    cursor.execute("DELETE FROM meal WHERE UserID = %s", (user_id,))
    cursor.execute("DELETE FROM goal WHERE UserID = %s", (user_id,))
    cursor.execute("DELETE FROM users WHERE UserID = %s", (user_id,))

    db.commit()
    cursor.close()
    db.close()

    flash("User account deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/log_workout_admin', methods=['GET', 'POST'])
def log_workout_admin():
    if request.method == 'POST':

        db = connect_to_db()
        cursor = db.cursor(dictionary=True)

        exercise_type = request.form.get('exercise')
        duration = request.form.get('duration')
        calories = request.form.get('calories')

        # Insert new workout record
        workout_date = None
        user_id = session.get('userid')

        cursor.execute("INSERT INTO workout (UserID, ExerciseType, Duration, CaloriesBurned, WorkoutDate) VALUES (%s, %s, %s, %s, %s)",
                       (user_id, exercise_type, duration, calories, workout_date))

        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for('admin_dashboard'))

    return render_template('logWorkoutAdmin.html')

@app.route('/log_meal_admin', methods=['GET', 'POST'])
def log_meal_admin():
    if request.method == 'POST':

        db = connect_to_db()
        cursor = db.cursor(dictionary=True)

        FoodItems = request.form.get('FoodItems')
        Calories = request.form.get('Calories')
        Nutrients = request.form.get('Nutrients')

        MealDate = None
        user_id = session.get('userid')

        cursor.execute("INSERT INTO meal (UserID, FoodItems, Calories, Nutrients, MealDate) VALUES (%s, %s, %s, %s, %s)",
                       (user_id, FoodItems, Calories, Nutrients, MealDate))

        db.commit()
        cursor.close()
        db.close()

        return redirect(url_for('admin_dashboard'))

    return render_template('logMealAdmin.html')


@app.route('/view_meals_admin')
def view_meals_admin():
    if 'userid' not in session:
        return redirect(url_for('login'))

    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    # Fetch all meals
    cursor.execute("""
        SELECT m.MealID, m.FoodItems, m.Calories, m.UserID, u.Name AS UserName
        FROM meal m
        JOIN users u ON m.UserID = u.UserID
    """)
    meals = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('viewMealsAdmin.html', meals=meals)


@app.route('/view_workouts_admin')
def view_workouts_admin():
    if 'userid' not in session:
        return redirect(url_for('login'))

    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT w.WorkoutID, w.UserID, w.ExerciseType, w.Duration, w.CaloriesBurned, w.WorkoutDate, u.Name AS UserName
        FROM workout w
        JOIN users u ON w.UserID = u.UserID
    """)
    workouts = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('viewWorkoutsAdmin.html', workouts=workouts)

@app.route('/view_goals_admin')
def view_goals_admin():
    if 'userid' not in session:
        return redirect(url_for('login'))

    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    # Fetch all goals
    cursor.execute("""
        SELECT g.GoalID, g.TargetWeight, g.Deadline, g.UserID, u.Name AS UserName, up.Weight AS CurrentWeight
        FROM goal g
        JOIN users u ON g.UserID = u.UserID
        JOIN userprofile up ON g.UserID = up.UserID
    """)
    goals = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('viewGoalsAdmin.html', goals=goals)

@app.route('/delete_meal_admin', methods=['POST'])
def delete_meal_admin():
    if 'userid' not in session:
        return redirect(url_for('login'))

    meal_id = request.form['meal_id']
    
    db = connect_to_db()
    cursor = db.cursor()
    
    cursor.execute("DELETE FROM meal WHERE MealID = %s", (meal_id,))
    db.commit()
    
    cursor.close()
    db.close()

    return redirect(url_for('view_meals_admin'))

@app.route('/delete_goal_admin', methods=['POST'])
def delete_goal_admin():
    if 'userid' not in session:
        return redirect(url_for('login'))

    goal_id = request.form['goal_id']
    
    db = connect_to_db()
    cursor = db.cursor()
    
    cursor.execute("DELETE FROM goal WHERE GoalID = %s", (goal_id,))
    db.commit()
    
    cursor.close()
    db.close()

    return redirect(url_for('view_goals_admin'))


def get_calories(user_id, month, year):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)

    user_id = session.get('userid')
    # Query meals
    cursor.execute("""
        SELECT SUM(Calories) AS total_intake
        FROM meal
        WHERE UserID = %s AND MONTH(MealDate) = %s AND YEAR(MealDate) = %s
    """, (user_id, month, year))
    meal_data = cursor.fetchone()
    total_intake = meal_data['total_intake'] if meal_data['total_intake'] else 0

    # Query workouts
    cursor.execute("""
        SELECT SUM(CaloriesBurned) AS total_burned
        FROM workout
        WHERE UserID = %s AND MONTH(WorkoutDate) = %s AND YEAR(WorkoutDate) = %s
    """, (user_id, month, year))
    workout_data = cursor.fetchone()
    total_burned = workout_data['total_burned'] if workout_data['total_burned'] else 0

    conn.close()
    return total_intake, total_burned

def generate_chart(user_id, month, year):
    intake, burned = get_calories(user_id, month, year)

    categories = ["Calories Consumed", "Calories Burned"]
    values = [intake, burned]

    plt.figure(figsize=(6, 4))
    plt.bar(categories, values, color=['blue', 'red'])
    plt.title(f"Caloric Intake vs Burned ({month}/{year})")
    plt.ylabel("Calories")
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    encoded_img = base64.b64encode(img.getvalue()).decode('utf-8')
    plt.close()

    return encoded_img

@app.route('/view_chart', methods=['GET', 'POST'])
def view_chart():
    if request.method == 'POST':
        month = request.form['month']
        year = request.form['year']
        user_id = request.form['user_id']  # Assuming user ID is passed from the frontend
        chart = generate_chart(user_id, month, year)
        return render_template('chart.html', chart=chart, month=month, year=year)

    return render_template('chart_form.html')

@app.route('/delete_workout_admin', methods=['POST'])
def delete_workout_admin():
    if 'userid' not in session:
        return redirect(url_for('login'))

    workout_id = request.form['workout_id']
    
    db = connect_to_db()
    cursor = db.cursor()
    
    cursor.execute("DELETE FROM workout WHERE WorkoutID = %s", (workout_id,))
    db.commit()
    
    cursor.close()
    db.close()

    return redirect(url_for('view_workouts_admin'))

@app.route('/recommended_meal', methods=['GET', 'POST'])
def recommended_meal():
    if request.method == 'POST':
        # Use .get() to safely get form data and avoid errors
        condition = request.form.get('meal_condition')  # Using .get() to avoid KeyError
        calories = request.form.get('meal_calories')  # Using .get() to avoid KeyError

        if condition and calories:  # Check if both values are available
            calories = int(calories)  # Convert to integer

            # Connect to the database and fetch all meals by the admin (UserID = 1)
            connection = connect_to_db()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Meal WHERE UserID = 1")
            all_meals = cursor.fetchall()

            # Filter meals based on the selected condition
            if condition == 'less':
                filtered_meals = [m for m in all_meals if m['Calories'] < calories]
            elif condition == 'equal':
                filtered_meals = [m for m in all_meals if m['Calories'] == calories]
            elif condition == 'more':
                filtered_meals = [m for m in all_meals if m['Calories'] > calories]
            else:
                filtered_meals = []

            # Randomly select a meal if any are available
            if filtered_meals:
                recommended_meal = random.choice(filtered_meals)
            else:
                recommended_meal = None
        else:
            recommended_meal = None

        return render_template('recommended_meal.html', meal=recommended_meal)

    return render_template('recommended_meal.html')


# Route for recommended workout
@app.route('/recommended_workout', methods=['GET', 'POST'])
def recommended_workout():
    if request.method == 'POST':
        # Use .get() to safely get form data and avoid errors
        condition = request.form.get('workout_condition')  # Using .get() to avoid KeyError
        duration = request.form.get('workout_duration')  # Using .get() to avoid KeyError

        if condition and duration:  # Check if both values are available
            duration = int(duration)  # Convert to integer

            # Connect to the database and fetch all workouts by the admin (UserID = 1)
            connection = connect_to_db()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Workout WHERE UserID = 1")
            all_workouts = cursor.fetchall()

            # Filter workouts based on the selected condition
            if condition == 'less':
                filtered_workouts = [w for w in all_workouts if w['Duration'] < duration]
            elif condition == 'equal':
                filtered_workouts = [w for w in all_workouts if w['Duration'] == duration]
            elif condition == 'more':
                filtered_workouts = [w for w in all_workouts if w['Duration'] > duration]
            else:
                filtered_workouts = []

            # Randomly select a workout if any are available
            if filtered_workouts:
                recommended_workout = random.choice(filtered_workouts)
            else:
                recommended_workout = None
        else:
            recommended_workout = None

        return render_template('recommended_workout.html', workout=recommended_workout)

    return render_template('recommended_workout.html')


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'userid' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("New passwords do not match.", "error")
            return redirect(url_for('change_password'))

        db = connect_to_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT PasswordHash FROM users WHERE UserID = %s", (session['userid'],))
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(current_password.encode('utf-8'), user['PasswordHash'].encode('utf-8')):
            flash("Current password is incorrect.", "error")
            cursor.close()
            db.close()
            return redirect(url_for('change_password'))

        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("UPDATE users SET PasswordHash = %s WHERE UserID = %s", (hashed_password, session['userid']))

        db.commit()
        cursor.close()
        db.close()

        flash("Password updated successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('change_password.html')

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'userid' not in session:
        return redirect(url_for('login'))

    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    # Get existing user data
    cursor.execute("SELECT * FROM users WHERE UserID = %s", (user_id,))
    user = cursor.fetchone()

    cursor.execute("SELECT * FROM userprofile WHERE UserID = %s", (user_id,))
    profile = cursor.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        age = request.form['age']
        height = request.form['height']
        weight = request.form['weight']

        # Only hash new password if provided
        if password:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("UPDATE users SET Name=%s, Email=%s, PasswordHash=%s WHERE UserID=%s",
                           (name, email, hashed_password, user_id))
        else:
            cursor.execute("UPDATE users SET Name=%s, Email=%s WHERE UserID=%s",
                           (name, email, user_id))

        cursor.execute("UPDATE userprofile SET Age=%s, Height=%s, Weight=%s WHERE UserID=%s",
                       (age, height, weight, user_id))

        db.commit()
        cursor.close()
        db.close()

        flash("User info updated successfully.", "success")
        return redirect(url_for('view_users'))

    cursor.close()
    db.close()

    return render_template('edit_user.html', user=user, profile=profile)

@app.route('/edit_meal/<int:meal_id>', methods=['GET', 'POST'])
def edit_meal(meal_id):
    if 'userid' not in session:
        return redirect(url_for('login'))

    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    # Fetch the current meal details
    cursor.execute("SELECT * FROM meal WHERE MealID = %s", (meal_id,))
    meal = cursor.fetchone()

    if not meal:
        cursor.close()
        db.close()
        flash("Meal not found.", "error")
        return redirect(url_for('view_meals'))

    if request.method == 'POST':
        # Get updated details from the form
        food_items = request.form.get('FoodItems', meal['FoodItems'])
        calories = request.form.get('Calories', meal['Calories'])
        nutrients = request.form.get('Nutrients', meal['Nutrients'])
        meal_date = request.form.get('MealDate', meal['MealDate'])

        # Update the meal in the database
        cursor.execute("""
            UPDATE meal 
            SET FoodItems = %s, Calories = %s, Nutrients = %s, MealDate = %s 
            WHERE MealID = %s
        """, (food_items, calories, nutrients, meal_date, meal_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Meal updated successfully.", "success")
        return redirect(url_for('view_meals'))

    cursor.close()
    db.close()
    return render_template('edit_meal.html', meal=meal)


@app.route('/edit_goal/<int:goal_id>', methods=['GET', 'POST'])
def edit_goal(goal_id):
    if 'userid' not in session:
        return redirect(url_for('login'))

    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    # Fetch the current goal details
    cursor.execute("SELECT * FROM goal WHERE GoalID = %s", (goal_id,))
    goal = cursor.fetchone()

    if not goal:
        cursor.close()
        db.close()
        flash("Goal not found.", "error")
        return redirect(url_for('view_goals'))

    if request.method == 'POST':
        # Get updated details from the form
        target_weight = request.form.get('TargetWeight', goal['TargetWeight'])
        deadline = request.form.get('Deadline', goal['Deadline'])

        # Validate that the deadline is not in the past
        current_date = datetime.today().strftime('%Y-%m-%d')
        if deadline < current_date:
            flash("Deadline cannot be in the past.", "error")
            return render_template('editGoal.html', goal=goal)

        # Update the goal in the database
        cursor.execute("""
            UPDATE goal 
            SET TargetWeight = %s, Deadline = %s 
            WHERE GoalID = %s
        """, (target_weight, deadline, goal_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Goal updated successfully.", "success")
        return redirect(url_for('view_goals'))

    cursor.close()
    db.close()
    return render_template('edit_goal.html', goal=goal)

@app.route('/edit_workout/<int:workout_id>', methods=['GET', 'POST'])
def edit_workout(workout_id):
    if 'userid' not in session:
        return redirect(url_for('login'))

    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    # Fetch the current workout details
    cursor.execute("SELECT * FROM workout WHERE WorkoutID = %s", (workout_id,))
    workout = cursor.fetchone()

    if not workout:
        cursor.close()
        db.close()
        flash("Workout not found.", "error")
        return redirect(url_for('view_workouts'))

    if request.method == 'POST':
        # Get updated details from the form
        exercise_type = request.form.get('ExerciseType', workout['ExerciseType'])
        duration = request.form.get('Duration', workout['Duration'])
        calories_burned = request.form.get('CaloriesBurned', workout['CaloriesBurned'])
        workout_date = request.form.get('WorkoutDate', workout['WorkoutDate'])

        # Validate input (optional: add your own validation logic)
        if not exercise_type or not duration or not calories_burned or not workout_date:
            flash("All fields are required.", "error")
            return render_template('editWorkout.html', workout=workout)

        # Update the workout in the database
        cursor.execute("""
            UPDATE workout 
            SET ExerciseType = %s, Duration = %s, CaloriesBurned = %s, WorkoutDate = %s 
            WHERE WorkoutID = %s
        """, (exercise_type, duration, calories_burned, workout_date, workout_id))

        db.commit()
        cursor.close()
        db.close()

        flash("Workout updated successfully.", "success")
        return redirect(url_for('view_workouts'))

    cursor.close()
    db.close()
    return render_template('edit_workout.html', workout=workout)

if __name__ == '__main__':
    app.run(debug=True)
