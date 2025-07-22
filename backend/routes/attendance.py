from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models.attendance import Attendance
from models.class_session import ClassSession
from models.user import User
from datetime import datetime, date
from sqlalchemy import and_

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/record', methods=['POST'])
@jwt_required()
def record_attendance():
    """Record attendance for a class session"""
    try:
        current_user_id = get_jwt_identity()
        teacher = User.query.get(current_user_id)
        
        if not teacher or teacher.role != 'teacher':
            return jsonify({'error': 'Only teachers can record attendance'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['subject', 'class', 'dept', 'date', 'timeStart', 'timeEnd', 'rollStart', 'rollEnd']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create class session
        class_session = ClassSession(
            subject=data['subject'],
            class_name=data['class'],
            department=data['dept'],
            division=data.get('division'),
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            start_time=datetime.strptime(data['timeStart'], '%H:%M').time(),
            end_time=datetime.strptime(data['timeEnd'], '%H:%M').time(),
            teacher_id=current_user_id,
            roll_start=data['rollStart'],
            roll_end=data['rollEnd']
        )
        
        db.session.add(class_session)
        db.session.flush()  # Get the ID without committing
        
        # Get students in the class
        students = User.query.filter(
            and_(
                User.role == 'student',
                User.class_name == data['class'],
                User.department == data['dept']
            )
        ).all()
        
        # Create attendance records for all students
        attendance_records = []
        for student in students:
            attendance = Attendance(
                user_id=student.id,
                class_session_id=class_session.id,
                status='present',  # Default to present, can be updated later
                recorded_by=current_user_id
            )
            attendance_records.append(attendance)
        
        db.session.add_all(attendance_records)
        db.session.commit()
        
        return jsonify({
            'message': 'Attendance recorded successfully',
            'class_session': class_session.to_dict(),
            'students_count': len(students)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@attendance_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_attendance():
    """Update attendance status for specific students"""
    try:
        current_user_id = get_jwt_identity()
        teacher = User.query.get(current_user_id)
        
        if not teacher or teacher.role != 'teacher':
            return jsonify({'error': 'Only teachers can update attendance'}), 403
        
        data = request.get_json()
        
        if not data.get('class_session_id') or not data.get('attendance_updates'):
            return jsonify({'error': 'Class session ID and attendance updates are required'}), 400
        
        class_session = ClassSession.query.get(data['class_session_id'])
        if not class_session:
            return jsonify({'error': 'Class session not found'}), 404
        
        if class_session.teacher_id != current_user_id:
            return jsonify({'error': 'You can only update attendance for your own classes'}), 403
        
        # Update attendance records
        for update in data['attendance_updates']:
            attendance = Attendance.query.filter_by(
                user_id=update['user_id'],
                class_session_id=data['class_session_id']
            ).first()
            
            if attendance:
                attendance.status = update['status']
                attendance.notes = update.get('notes')
        
        db.session.commit()
        
        return jsonify({
            'message': 'Attendance updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@attendance_bp.route('/session/<int:session_id>', methods=['GET'])
@jwt_required()
def get_session_attendance(session_id):
    """Get attendance for a specific class session"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        class_session = ClassSession.query.get(session_id)
        if not class_session:
            return jsonify({'error': 'Class session not found'}), 404
        
        # Check if user has access to this session
        if user.role == 'student':
            # Students can only see their own attendance
            attendance = Attendance.query.filter_by(
                user_id=current_user_id,
                class_session_id=session_id
            ).first()
            
            if not attendance:
                return jsonify({'error': 'Attendance record not found'}), 404
            
            return jsonify({
                'class_session': class_session.to_dict(),
                'attendance': attendance.to_dict()
            }), 200
        
        elif user.role == 'teacher':
            # Teachers can see all attendance for their sessions
            if class_session.teacher_id != current_user_id:
                return jsonify({'error': 'Access denied'}), 403
            
            attendances = Attendance.query.filter_by(class_session_id=session_id).all()
            
            return jsonify({
                'class_session': class_session.to_dict(),
                'attendances': [att.to_dict() for att in attendances]
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@attendance_bp.route('/student/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student_attendance(student_id):
    """Get attendance records for a specific student"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Check if user has access to this student's data
        if user.role == 'student' and current_user_id != student_id:
            return jsonify({'error': 'Access denied'}), 403
        
        student = User.query.get(student_id)
        if not student or student.role != 'student':
            return jsonify({'error': 'Student not found'}), 404
        
        # Get query parameters for filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        subject = request.args.get('subject')
        
        query = Attendance.query.filter_by(user_id=student_id)
        
        if start_date:
            query = query.join(ClassSession).filter(ClassSession.date >= start_date)
        if end_date:
            query = query.join(ClassSession).filter(ClassSession.date <= end_date)
        if subject:
            query = query.join(ClassSession).filter(ClassSession.subject == subject)
        
        attendances = query.order_by(Attendance.recorded_at.desc()).all()
        
        return jsonify({
            'student': student.to_dict(),
            'attendances': [att.to_dict() for att in attendances]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@attendance_bp.route('/analytics', methods=['GET'])
@jwt_required()
def get_attendance_analytics():
    """Get attendance analytics"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        class_name = request.args.get('class')
        department = request.args.get('dept')
        
        if user.role == 'student':
            # Student analytics
            query = Attendance.query.filter_by(user_id=current_user_id)
            
            if start_date:
                query = query.join(ClassSession).filter(ClassSession.date >= start_date)
            if end_date:
                query = query.join(ClassSession).filter(ClassSession.date <= end_date)
            
            attendances = query.all()
            
            total_sessions = len(attendances)
            present_count = len([a for a in attendances if a.status == 'present'])
            absent_count = len([a for a in attendances if a.status == 'absent'])
            late_count = len([a for a in attendances if a.status == 'late'])
            
            attendance_percentage = (present_count / total_sessions * 100) if total_sessions > 0 else 0
            
            return jsonify({
                'total_sessions': total_sessions,
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'attendance_percentage': round(attendance_percentage, 2)
            }), 200
        
        elif user.role == 'teacher':
            # Teacher analytics
            query = ClassSession.query.filter_by(teacher_id=current_user_id)
            
            if start_date:
                query = query.filter(ClassSession.date >= start_date)
            if end_date:
                query = query.filter(ClassSession.date <= end_date)
            if class_name:
                query = query.filter(ClassSession.class_name == class_name)
            if department:
                query = query.filter(ClassSession.department == department)
            
            sessions = query.all()
            
            total_sessions = len(sessions)
            total_students = 0
            total_present = 0
            total_absent = 0
            
            for session in sessions:
                attendances = Attendance.query.filter_by(class_session_id=session.id).all()
                total_students += len(attendances)
                total_present += len([a for a in attendances if a.status == 'present'])
                total_absent += len([a for a in attendances if a.status == 'absent'])
            
            avg_attendance = (total_present / total_students * 100) if total_students > 0 else 0
            
            return jsonify({
                'total_sessions': total_sessions,
                'total_students': total_students,
                'total_present': total_present,
                'total_absent': total_absent,
                'average_attendance': round(avg_attendance, 2)
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 