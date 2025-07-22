#!/usr/bin/env python3
"""
MarkYou Backend Server
Run this script to start the Flask development server
"""

from app import create_app, db
from models import User, Attendance, ClassSession, Subject

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Create some sample data for testing
        if not User.query.first():
            print("Creating sample data...")
            
            # Create a sample teacher
            teacher = User(
                prn='T001',
                name='Dr. John Smith',
                email='john.smith@university.edu',
                class_name='FY',
                department='CSE',
                role='teacher'
            )
            teacher.password = 'teacher123'
            
            # Create sample students
            students = []
            for i in range(1, 11):
                student = User(
                    prn=f'S{i:03d}',
                    name=f'Student {i}',
                    email=f'student{i}@university.edu',
                    class_name='FY',
                    department='CSE',
                    role='student'
                )
                student.password = 'student123'
                students.append(student)
            
            db.session.add(teacher)
            db.session.add_all(students)
            db.session.commit()
            
            print("Sample data created successfully!")
    
    print("Starting MarkYou Backend Server...")
    print("Server will be available at: http://localhost:5000")
    print("API Health Check: http://localhost:5000/api/health")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000) 